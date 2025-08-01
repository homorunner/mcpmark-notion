"""
Simplified Agent for Demo
=========================

This module provides a minimal agent that handles LLM and MCP server interactions
without the complexity of retries, token tracking, and advanced error handling.
"""

import asyncio
import os
import time
from typing import Dict, Any, Optional

from agents import (
    Agent,
    Model,
    ModelProvider,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
)
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent
from agents.mcp.server import MCPServerStdio

from demo_model_config import DemoModelConfig


class DemoAgent:
    """Simplified agent for Notion task execution."""
    
    def __init__(self, model_name: str, notion_key: str, api_key: Optional[str] = None, 
                 base_url: Optional[str] = None, timeout: int = 300):
        """Initialize the agent with configuration.
        
        Args:
            model_name: Name of the model to use
            notion_key: Notion API key
            api_key: Optional API key (uses env var if not provided)
            base_url: Optional base URL (uses env var or default if not provided)
            timeout: Timeout in seconds
        """
        self.notion_key = notion_key
        self.timeout = timeout
        
        # Initialize model configuration
        self.model_config = DemoModelConfig(model_name, api_key, base_url)
        
        # Create model provider
        self.model_provider = self._create_model_provider()
        
        # Stop flag for cancellation
        self.stop_flag = False
    
    def stop(self):
        """Stop the current execution."""
        self.stop_flag = True
    
    def reset(self):
        """Reset the agent for a new execution."""
        self.stop_flag = False
    
    def _create_model_provider(self) -> ModelProvider:
        """Create and return a model provider for the specified model."""
        client = AsyncOpenAI(
            base_url=self.model_config.base_url, 
            api_key=self.model_config.api_key
        )
        
        # Capture the model name from the agent
        agent_model_name = self.model_config.actual_model_name
        
        class CustomModelProvider(ModelProvider):
            def get_model(self, model_name_override: str | None) -> Model:
                final_model_name = model_name_override or agent_model_name
                return OpenAIChatCompletionsModel(
                    model=final_model_name, openai_client=client
                )
        
        return CustomModelProvider()
    
    async def _create_mcp_server(self) -> MCPServerStdio:
        """Create the MCP server for Notion."""
        return MCPServerStdio(
            params={
                "command": "npx",
                "args": ["-y", "@notionhq/notion-mcp-server"],
                "env": {
                    "OPENAPI_MCP_HEADERS": (
                        '{"Authorization": "Bearer ' + self.notion_key + '", '
                        '"Notion-Version": "2022-06-28"}'
                    )
                }
            },
            client_session_timeout_seconds=120,
            cache_tools_list=True,
        )
    
    async def execute_task(self, task_instruction: str, callback=None) -> Dict[str, Any]:
        """Execute a task using the agent.
        
        Args:
            task_instruction: The task description/instruction
            callback: Optional callback function for real-time updates
            
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        
        try:
            # Check if execution was stopped before starting
            if self.stop_flag:
                return {
                    "success": False,
                    "messages": [],
                    "execution_time": 0,
                    "execution_logs": [],
                    "error": "Execution stopped by user"
                }
            
            # Create MCP server
            async with await self._create_mcp_server() as server:
                # Create agent
                agent = Agent(name="Notion Agent", mcp_servers=[server])
                
                # Configure model settings
                ModelSettings.tool_choice = "required"
                
                # Prepare conversation
                conversation = [{"content": task_instruction, "role": "user"}]
                
                # Run agent with streaming
                result = Runner.run_streamed(
                    agent,
                    max_turns=50,
                    input=conversation,
                    run_config=RunConfig(model_provider=self.model_provider),
                )
                
                # Add small delay to ensure background task starts
                await asyncio.sleep(0.1)
                
                # Process streaming events and collect execution logs
                event_count = 0
                execution_logs = []
                
                # Buffer for accumulating response content
                response_buffer = ""
                last_response_update = time.time()
                
                async for event in result.stream_events():
                    # Check for stop signal during streaming
                    if self.stop_flag:
                        return {
                            "success": False,
                            "messages": [],
                            "execution_time": time.time() - start_time,
                            "execution_logs": execution_logs,
                            "error": "Execution stopped by user"
                        }
                    
                    event_count += 1
                    
                    if hasattr(event, "type"):
                        if event.type == "raw_response_event":
                            if hasattr(event, "data") and isinstance(
                                event.data, ResponseTextDeltaEvent
                            ):
                                delta_text = event.data.delta
                                if delta_text:
                                    # Add to response buffer
                                    response_buffer += delta_text
                                    print(delta_text, end="", flush=True)
                                    
                                    # Update UI periodically or on sentence boundaries
                                    current_time = time.time()
                                    should_update = (
                                        # Update every 0.5 seconds
                                        current_time - last_response_update > 0.5 or
                                        # Or on sentence boundaries
                                        delta_text.strip().endswith(('.', '!', '?', '\n'))
                                    )
                                    
                                    if should_update and callback and response_buffer.strip():
                                        log_entry = {
                                            "type": "response", 
                                            "content": response_buffer.strip(),
                                            "timestamp": time.time() - start_time
                                        }
                                        callback(log_entry)
                                        last_response_update = current_time
                        
                        elif event.type == "run_item_stream_event":
                            if hasattr(event, "item") and getattr(event.item, "type", "") == "tool_call_item":
                                tool_name = getattr(getattr(event.item, "raw_item", None), "name", "Unknown")
                                log_message = f"-- Calling Notion Tool: {tool_name}"
                                log_entry = {
                                    "type": "tool_call", 
                                    "tool_name": tool_name,
                                    "message": log_message,
                                    "timestamp": time.time() - start_time
                                }
                                execution_logs.append(log_entry)
                                print(f"\n{log_message}...")
                                
                                # Real-time callback
                                if callback:
                                    callback(log_entry)
                
                # Send final response buffer if there's remaining content
                if response_buffer.strip() and callback:
                    final_log_entry = {
                        "type": "response", 
                        "content": response_buffer.strip(),
                        "timestamp": time.time() - start_time
                    }
                    callback(final_log_entry)
                
                # Store complete response in execution logs
                if response_buffer.strip():
                    execution_logs.append({
                        "type": "response", 
                        "content": response_buffer.strip(),
                        "timestamp": time.time() - start_time
                    })
                
                # Get the final messages
                messages = []
                if hasattr(result, 'messages'):
                    messages = result.messages
                elif hasattr(result, 'conversation'):
                    messages = result.conversation
                
                execution_time = time.time() - start_time
                
                return {
                    "success": True,
                    "messages": messages,
                    "execution_time": execution_time,
                    "execution_logs": execution_logs,
                    "error": None
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "messages": [],
                "execution_time": execution_time,
                "execution_logs": [],
                "error": str(e)
            }
    
    def execute_sync(self, task_instruction: str, callback=None) -> Dict[str, Any]:
        """Synchronous wrapper for execute_task."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.execute_task(task_instruction, callback))
        finally:
            loop.close()