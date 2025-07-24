#!/usr/bin/env python3
"""
Unified Agent Implementation for MCPBench
=========================================

This module provides a unified agent implementation that handles LLM and MCP server
management. The agent is responsible for:
- Model provider creation and management
- MCP server creation for different services
- LLM inference execution with streaming response
- Token usage tracking and statistics

The agent does NOT handle task-specific logic - that's the responsibility of task managers.
"""

import asyncio
import os
import time
from typing import Any, Dict

from agents import (
    Agent,
    Model,
    ModelProvider,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
    set_tracing_export_api_key,
)
from agents.mcp.server import MCPServerStdio, MCPServerStreamableHttp, MCPServerStreamableHttpParams
from openai import AsyncOpenAI

from src.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

class MCPAgent:
    """
    Unified agent for LLM and MCP server management.
    
    This agent handles the integration of:
    - Model: LLM configuration (model name, API key, base URL)
    - Agent Framework: Currently supports OpenAI Agents SDK
    - Service: MCP service type (notion, github, postgres)
    """

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str,
        service: str,
        agent_framework: str = "openai_agents",
        timeout: int = 600,
        max_retries: int = 3,
        retry_backoff: float = 5.0,
    ):
        """
        Initialize the MCP agent.

        Args:
            model_name: Name of the LLM model to use
            api_key: API key for the model provider
            base_url: Base URL for the model provider
            service: MCP service type (notion, github, postgres)
            agent_framework: Agent framework to use (default: openai_agents)
            timeout: Execution timeout in seconds
            max_retries: Maximum number of retries for transient errors
            retry_backoff: Backoff time for retries in seconds
        """
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.service = service
        self.agent_framework = agent_framework
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        # Initialize model provider
        self.model_provider = self._create_model_provider()

        # Usage statistics
        self._usage_stats = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_turns": 0,
            "total_execution_time": 0.0,
            "successful_executions": 0,
            "failed_executions": 0,
        }

        logger.debug(f"Initialized MCPAgent for service '{service}' with model '{model_name}'")
        set_tracing_export_api_key(os.getenv("OPENAI_TRACE_API_KEY"))

    def _create_model_provider(self) -> ModelProvider:
        """Create and return a model provider for the specified model."""
        client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        agent_model_name = self.model_name  # Capture the model name from the agent

        class CustomModelProvider(ModelProvider):
            def get_model(self, model_name_override: str | None) -> Model:
                final_model_name = model_name_override or agent_model_name
                return OpenAIChatCompletionsModel(
                    model=final_model_name, openai_client=client
                )

        return CustomModelProvider()

    async def _create_mcp_server(self, **service_config):
        """
        Create service-specific MCP server connection.
        
        Args:
            **service_config: Service-specific configuration parameters
            
        Returns:
            MCP server instance
        """
        if self.service == "notion":
            # Notion MCP server configuration
            notion_key = service_config.get("notion_key")
            if not notion_key:
                raise ValueError("Notion API key (notion_key) is required for Notion MCP server")

            return MCPServerStdio(
                params={
                    "command": "npx",
                    "args": ["-y", "@notionhq/notion-mcp-server"],
                    "env": {
                        "OPENAPI_MCP_HEADERS": (
                            '{"Authorization": "Bearer ' + notion_key + '", '
                            '"Notion-Version": "2022-06-28"}'
                        )
                    },
                },
                client_session_timeout_seconds=120,
                cache_tools_list=True,
            )

        elif self.service == "github":
            # GitHub MCP server configuration
            github_token = service_config.get("github_token")
            if not github_token:
                raise ValueError("GitHub token (github_token) is required for GitHub MCP server")

            params = MCPServerStreamableHttpParams(
                url="https://api.githubcopilot.com/mcp/",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "User-Agent": "MCPBench/1.0"
                },
                timeout_seconds=30
            )

            return MCPServerStreamableHttp(
                params=params,
                cache_tools_list=True,
                name="GitHub MCP Server",
                client_session_timeout_seconds=120
            )

        elif self.service == "filesystem":
            # Filesystem MCP server configuration
            # Get test directory from service_config or environment
            test_dir = service_config.get("test_directory", os.getenv("FILESYSTEM_TEST_DIR", "/tmp"))
            
            return MCPServerStdio(
                params={
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        test_dir  # Pass the allowed directory
                    ],
                    "env": {
                        **os.environ,
                        "NODE_ENV": "production"
                    }
                },
                name="Filesystem MCP Server",
                cache_tools_list=True,
            )
        
        elif self.service == "postgres":
            # PostgreSQL MCP server configuration (placeholder)
            raise NotImplementedError("PostgreSQL MCP server not yet implemented")

        else:
            raise ValueError(f"Unsupported service: {self.service}")

    async def _execute_with_streaming(self, instruction: str, **service_config) -> Dict[str, Any]:
        """
        Execute instruction with agent using streaming response.
        
        Args:
            instruction: The instruction/prompt to execute
            **service_config: Service-specific configuration
            
        Returns:
            Dictionary containing execution results
        """
        start_time = time.time()

        try:
            # Create MCP server
            async with await self._create_mcp_server(**service_config) as server:
                # Create agent
                agent = Agent(name=f"{self.service.title()} Agent", mcp_servers=[server])
                
                # Configure model settings
                ModelSettings.tool_choice = "required"

                # Set service-specific environment variables
                if self.service == "notion" and service_config.get("notion_key"):
                    os.environ["NOTION_API_KEY"] = service_config["notion_key"]
                elif self.service == "github" and service_config.get("github_token"):
                    os.environ["GITHUB_TOKEN"] = service_config["github_token"]

                # Prepare conversation
                conversation = [{"content": instruction, "role": "user"}]

                # Try non-streaming first to avoid logprobs issue
                try:
                    # Use non-streaming run
                    result = await Runner.run(
                        agent,
                        max_turns=20,
                        input=conversation,
                        run_config=RunConfig(model_provider=self.model_provider),
                    )
                    
                    # Process non-streaming result
                    print("\n[Agent completed task]")
                    
                except Exception as non_streaming_error:
                    logger.warning(f"Non-streaming failed, falling back to streaming: {non_streaming_error}")
                    
                    # Fall back to streaming
                    result = Runner.run_streamed(
                        agent,
                        max_turns=20,
                        input=conversation,
                        run_config=RunConfig(model_provider=self.model_provider),
                    )

                    # Add small delay to ensure background task starts
                    await asyncio.sleep(0.1)

                    # Process streaming events
                    event_count = 0
                    async for event in result.stream_events():
                        event_count += 1
                        logger.debug(f"Event {event_count}: {event}")

                        # Check if event has type attribute
                        if hasattr(event, "type"):
                            logger.debug(f"Event type: {event.type}")

                            if event.type == "raw_response_event":
                                # Handle text delta events without strict type checking
                                # This avoids pydantic validation errors for missing 'logprobs' field
                                if (hasattr(event, "data") and 
                                    hasattr(event.data, "type") and 
                                    event.data.type == "response.output_text.delta" and
                                    hasattr(event.data, "delta")):
                                    # Print token deltas as we receive them
                                    delta_text = event.data.delta
                                    print(delta_text, end="", flush=True)

                            elif event.type == "run_item_stream_event":
                                if hasattr(event, "item"):
                                    if hasattr(event.item, "type"):
                                        if event.item.type == "tool_call_item":
                                            tool_name = "Unknown"
                                            if (
                                                hasattr(event.item, "raw_item")
                                                and hasattr(event.item.raw_item, "name")
                                            ):
                                                tool_name = event.item.raw_item.name
                                            logger.info(f"\n-- Calling {self.service.title()} Tool: {tool_name}...")

                # Extract token usage from raw responses
                token_usage = {}
                if hasattr(result, "raw_responses") and result.raw_responses:
                    total_input_tokens = 0
                    total_output_tokens = 0
                    total_tokens = 0
                    for response in result.raw_responses:
                        if hasattr(response, "usage") and response.usage:
                            total_input_tokens += response.usage.input_tokens
                            total_output_tokens += response.usage.output_tokens
                            total_tokens += response.usage.total_tokens

                    token_usage = {
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                        "total_tokens": total_tokens,
                    }

                    logger.info(
                        f"\nToken usage - Input: {total_input_tokens}, "
                        f"Output: {total_output_tokens}, Total: {total_tokens}"
                    )

                # Extract turn count
                turn_count = getattr(result, "current_turn", None)
                if turn_count is not None:
                    logger.info(f"Turn count: {turn_count}")

                # Extract conversation output
                conversation_output = result.to_input_list()

                execution_time = time.time() - start_time

                # Update usage statistics
                self._usage_stats["total_input_tokens"] += token_usage.get("input_tokens", 0)
                self._usage_stats["total_output_tokens"] += token_usage.get("output_tokens", 0)
                self._usage_stats["total_tokens"] += token_usage.get("total_tokens", 0)
                self._usage_stats["total_turns"] += turn_count or 0
                self._usage_stats["total_execution_time"] += execution_time
                self._usage_stats["successful_executions"] += 1

                return {
                    "success": True,
                    "output": conversation_output,
                    "token_usage": token_usage,
                    "turn_count": turn_count,
                    "execution_time": execution_time,
                    "error": None,
                }

        except Exception as e:
            execution_time = time.time() - start_time
            self._usage_stats["failed_executions"] += 1
            self._usage_stats["total_execution_time"] += execution_time

            logger.error(f"Agent execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "output": "",
                "token_usage": {},
                "turn_count": 0,
                "execution_time": execution_time,
                "error": str(e),
            }

    async def execute(self, instruction: str, **service_config) -> Dict[str, Any]:
        """
        Execute instruction with automatic retries on transient errors.
        
        Args:
            instruction: The instruction/prompt to execute
            **service_config: Service-specific configuration (e.g., notion_key, github_token)
            
        Returns:
            Dictionary containing:
            - success: bool
            - output: conversation output (list of messages)
            - token_usage: dict with token statistics
            - turn_count: number of conversational turns
            - execution_time: execution time in seconds
            - error: error message if failed
        """
        for attempt in range(1, self.max_retries + 1):
            result = await asyncio.wait_for(
                self._execute_with_streaming(instruction, **service_config),
                timeout=self.timeout
            )

            # Success - return immediately
            if result["success"]:
                return result

            # Use unified error handling
            from src.errors import ErrorHandler
            
            error_handler = ErrorHandler(service_name=self.service)
            error_info = error_handler.handle(Exception(result["error"] or "Unknown error"))
            
            if error_info.retryable and attempt < self.max_retries:
                wait_seconds = error_handler.get_retry_delay(error_info, attempt)
                logger.warning(
                    f"[Retry] Attempt {attempt}/{self.max_retries} failed with {error_info.category.value}. "
                    f"Waiting {wait_seconds}s before retrying: {error_info.message}"
                )
                await asyncio.sleep(wait_seconds)
                continue  # Retry

            # Standardize error message
            result["error"] = error_info.message

            # Non-transient error or out of retry attempts - return last result
            return result

        # Should never reach here, but return the last result as fallback
        return result

    def execute_sync(self, instruction: str, **service_config) -> Dict[str, Any]:
        """
        Synchronous wrapper for execute method.
        
        Args:
            instruction: The instruction/prompt to execute
            **service_config: Service-specific configuration
            
        Returns:
            Dictionary containing execution results
        """
        try:
            return asyncio.run(self.execute(instruction, **service_config))
        except asyncio.TimeoutError:
            self._usage_stats["failed_executions"] += 1
            return {
                "success": False,
                "output": "",
                "token_usage": {},
                "turn_count": 0,
                "execution_time": self.timeout,
                "error": f"Execution timed out after {self.timeout} seconds",
            }

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for this agent.
        
        Returns:
            Dictionary containing usage statistics
        """
        stats = self._usage_stats.copy()
        
        # Calculate averages
        total_executions = stats["successful_executions"] + stats["failed_executions"]
        if total_executions > 0:
            stats["avg_input_tokens"] = stats["total_input_tokens"] / total_executions
            stats["avg_output_tokens"] = stats["total_output_tokens"] / total_executions
            stats["avg_total_tokens"] = stats["total_tokens"] / total_executions
            stats["avg_turns"] = stats["total_turns"] / total_executions
            stats["avg_execution_time"] = stats["total_execution_time"] / total_executions
            stats["success_rate"] = stats["successful_executions"] / total_executions * 100
        else:
            stats.update({
                "avg_input_tokens": 0.0,
                "avg_output_tokens": 0.0,
                "avg_total_tokens": 0.0,
                "avg_turns": 0.0,
                "avg_execution_time": 0.0,
                "success_rate": 0.0,
            })

        return stats

    def reset_usage_stats(self):
        """Reset usage statistics."""
        self._usage_stats = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_turns": 0,
            "total_execution_time": 0.0,
            "successful_executions": 0,
            "failed_executions": 0,
        }

    def __repr__(self):
        return (
            f"MCPAgent(service='{self.service}', model='{self.model_name}', "
            f"framework='{self.agent_framework}')"
        )


def main():
    """Example usage of the MCPAgent."""
    import os
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv(dotenv_path=".mcp_env", override=False)

    # Example: Create a Notion agent
    agent = MCPAgent(
        model_name="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        service="notion",
    )

    # Example execution
    instruction = "List all pages in my Notion workspace"
    service_config = {"notion_key": os.getenv("EVAL_NOTION_API_KEY")}

    result = agent.execute_sync(instruction, **service_config)
    print(f"Success: {result['success']}")
    print(f"Token usage: {result['token_usage']}")
    print(f"Usage stats: {agent.get_usage_stats()}")


if __name__ == "__main__":
    main()