#!/usr/bin/env python3
"""
Notion Runner for MCPBench Evaluation Pipeline
=============================================

This module provides utilities for executing Notion API tasks using an MCP-enabled
agent with configurable models and environments.
"""

import asyncio
import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any, TYPE_CHECKING
from dotenv import load_dotenv

from agents import Agent, Runner, ModelSettings, ModelProvider, RunConfig, Model
from openai.types.responses import ResponseTextDeltaEvent
from openai import AsyncOpenAI
from agents.mcp.server import MCPServerStdio
from agents import OpenAIChatCompletionsModel

# Avoid circular imports
if TYPE_CHECKING:
    from .template_manager import TemplateManager
    
from .task_manager import Task
from .results_reporter import TaskResult


class NotionRunner:
    """Handles execution of Notion tasks through an MCP-enabled agent."""
    
    def __init__(self, model_name: str, api_key: str, base_url: str, notion_key: str):
        """Initialize with model and API configuration.
        
        Args:
            model_name: Name of the model to use
            api_key: API key for the model provider
            base_url: Base URL for the model provider
            notion_key: Notion API key
        """
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.notion_key = notion_key
        self.model_provider = self._create_model_provider()
        
        # Ensure logs directory exists
        self.logs_dir = Path("./logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_model_provider(self) -> ModelProvider:
        """Create and return a custom model provider."""
        load_dotenv(override=True)
        
        # Use provided parameters or fall back to environment variables
        base_url = self.base_url or os.getenv("MCPBENCH_BASE_URL") or ""
        api_key = self.api_key or os.getenv("MCPBENCH_API_KEY") or ""
        model_name = self.model_name or os.getenv("MCPBENCH_MODEL_NAME") or ""
        
        if not base_url or not api_key or not model_name:
            raise ValueError(
                "Please provide base_url, api_key, and model_name as parameters or set "
                "MCPBENCH_BASE_URL, MCPBENCH_API_KEY, and MCPBENCH_MODEL_NAME "
                "in your .env file or as environment variables."
            )
        
        client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        
        class CustomModelProvider(ModelProvider):
            def get_model(self, model_name_override: str | None) -> Model:
                return OpenAIChatCompletionsModel(
                    model=model_name_override or model_name, openai_client=client
                )
        
        return CustomModelProvider()
    
    async def _create_mcp_server(self) -> MCPServerStdio:
        """Create and return an MCP server connection for Notion."""
        return MCPServerStdio(
            params={
                "command": "npx",
                "args": ["-y", "@notionhq/notion-mcp-server"],
                "env": {
                    "OPENAPI_MCP_HEADERS": (
                        '{"Authorization": "Bearer ' + self.notion_key + '", '
                        '"Notion-Version": "2022-06-28"}'
                    )
                },
            },
            client_session_timeout_seconds=120,
            cache_tools_list=True,
        )
    
    def _read_task_file(self, path: Path) -> str:
        """Return the full text content of a file.
        
        Args:
            path: Path to the text/markdown file containing the task
            
        Returns:
            File contents as string
            
        Raises:
            FileNotFoundError: If the task file doesn't exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Task file '{path}' does not exist")
        
        return path.read_text(encoding="utf-8")
    
    async def _run_single_task_async(self, agent: Agent, task_content: str) -> str:
        """Send task content to agent and stream the response.
        
        Args:
            agent: Agent instance to use
            task_content: The task description/instructions
            
        Returns:
            The full assistant response gathered from the streamed deltas
        """
        # Prepare the conversation with a single user message
        conversation = [{"content": task_content, "role": "user"}]
        
        # Run the agent and stream events
        result = Runner.run_streamed(
            agent, 
            max_turns=20, 
            input=conversation, 
            run_config=RunConfig(model_provider=self.model_provider)
        )
        
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(
                event.data, ResponseTextDeltaEvent
            ):
                # Print token deltas as we receive them
                delta_text = event.data.delta
                print(delta_text, end="", flush=True)
            elif event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    print(
                        f"\n-- Calling Tool: {event.item.raw_item.name}...",
                        flush=True,
                    )
                elif event.item.type == "tool_call_output_item":
                    print("-- Tool call completed.", flush=True)
        print()  # Final newline after the assistant's completion
        
        return result.to_input_list()
    
    def run_single_task_file(self, task_file_path: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute a single task from a file.
        
        Args:
            task_file_path: Path to the task description file
            timeout: Maximum execution time in seconds
            
        Returns:
            Dictionary with keys:
                - success: Whether the task completed successfully
                - output: The assistant's response
                - error: Error message if failed, None otherwise
        """
        task_path = Path(task_file_path)
        
        try:
            async def _run() -> str:
                """Internal coroutine that performs the actual evaluation."""
                async with await self._create_mcp_server() as server:
                    agent = Agent(name="Notion Agent", mcp_servers=[server])
                    ModelSettings.tool_choice = "required"
                    
                    task_content = self._read_task_file(task_path)
                    
                    # Set the Notion API key in environment for the MCP server
                    if self.notion_key:
                        os.environ["NOTION_API_KEY"] = self.notion_key
                    
                    # Delegate to the async implementation to stream the response
                    return await self._run_single_task_async(agent, task_content)
            
            # Execute with timeout handling
            assistant_response: str = asyncio.run(asyncio.wait_for(_run(), timeout=timeout))
            
            return {
                "success": True,
                "output": assistant_response,
                "error": None,
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": "",
                "error": f"Task timed out after {timeout} seconds",
            }
        except Exception as exc:
            return {
                "success": False,
                "output": "",
                "error": str(exc),
            }
    
    def execute_task(self, task: Task, template_manager: Optional['TemplateManager'] = None) -> TaskResult:
        """Execute a complete task including verification and cleanup.
        
        Args:
            task: Task object containing task details
            template_manager: Optional TemplateManager for cleanup operations
            
        Returns:
            TaskResult object with execution results
        """
        print(f"\n🔄 Executing task: {task.name}")
        start_time = time.time()
        
        # Check if duplication succeeded
        if task.duplicated_template_id is None:
            execution_time = time.time() - start_time
            return TaskResult(
                task_name=task.name,
                success=False,
                execution_time=execution_time,
                error_message="Duplication failed",
                category=task.category,
                task_id=task.task_id
            )
        
        try:
            # Prepare task description with template ID
            template_id = str(task.duplicated_template_id)
            task_description = task.get_description() + f"\n\nNote: The ID of the working page/database is `{template_id}`. Check the title and properties of this block; this should be the first step."
            
            # Create temporary task file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(task_description)
                temp_task_path = f.name
            
            try:
                # Run the task
                result = self.run_single_task_file(temp_task_path, timeout=300)
                
                # Run verification
                verify_result = subprocess.run(
                    [sys.executable, str(task.verify_path), task.duplicated_template_id],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                # Process results
                success = verify_result.returncode == 0
                error_message = verify_result.stderr if not success and verify_result.stderr else None
                execution_time = time.time() - start_time
                
                # Clean up the duplicated template if template_manager provided
                if template_manager and task.duplicated_template_id:
                    template_manager.delete_template(task.duplicated_template_id)
                
                return TaskResult(
                    task_name=task.name,
                    success=success,
                    execution_time=execution_time,
                    error_message=error_message,
                    model_output=result.get('output', ''),
                    category=task.category,
                    task_id=task.task_id
                )
                
            finally:
                # Clean up temp file
                os.unlink(temp_task_path)
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Task execution failed: {str(e)}"
            
            return TaskResult(
                task_name=task.name,
                success=False,
                execution_time=execution_time,
                error_message=error_msg,
                category=task.category,
                task_id=task.task_id
            )


def main():
    """Example usage of NotionRunner."""
    # Load environment variables
    load_dotenv()
    
    # Create runner instance
    runner = NotionRunner(
        model_name=os.getenv("MCPBENCH_MODEL_NAME", "gpt-4"),
        api_key=os.getenv("MCPBENCH_API_KEY", ""),
        base_url=os.getenv("MCPBENCH_BASE_URL", ""),
        notion_key=os.getenv("NOTION_API_KEY", "")
    )
    
    # Example: Run a task file
    result = runner.run_single_task_file("instructions.md")
    print(f"Task completed: {result['success']}")
    if not result['success']:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()