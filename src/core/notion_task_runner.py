#!/usr/bin/env python3
"""
Notion Batch Task Runner
========================

A simplified, non-interactive wrapper around the Notion Agent that executes a
single task read from a file (default: instructions.md) and then exits.

Usage
-----
$ python notion_task_runner.py [task_file_path]

• `task_file_path` 
– Path to the file whose entire contents will be sent to the
  agent as the user prompt. If omitted, `instructions.md` in the current working
  directory is used.

This script reuses helper utilities from `mcp_utils.py` where possible to
avoid code duplication (e.g. environment loading and MCP server creation).
"""

import os
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Reuse helper utilities from the interactive CLI implementation
from utils.mcp_utils import (
    get_notion_key,
    create_model_provider,
    create_mcp_server,
)

from agents import Agent, Runner, gen_trace_id, trace, ModelSettings, ModelProvider, RunConfig
from openai.types.responses import ResponseTextDeltaEvent
from agents.run_context import RunContextWrapper

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def read_task_file(path: Path) -> str:
    """Return the full text content of *path*.

    Parameters
    ----------
    path : pathlib.Path
        Path to the text/markdown file containing the task.
    """
    if not path.exists():
        raise FileNotFoundError(f"Task file '{path}' does not exist")

    return path.read_text(encoding="utf-8")


# Ensure the logs directory exists
LOGS_DIR = Path("./logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

async def run_single_task(agent: Agent, task_content: str, custom_model_provider: ModelProvider) -> str:
    """Send *task_content* to *agent* and stream the response to stdout.

    Returns
    -------
    str
        The full assistant response gathered from the streamed deltas.
    """

    # Prepare the conversation with a single user message
    conversation = [{"content": task_content, "role": "user"}]

    # Run the agent and stream events
    result = Runner.run_streamed(agent, max_turns=20, input=conversation, run_config=RunConfig(model_provider=custom_model_provider))

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


# ---------------------------------------------------------------------------
# Compatibility wrapper for the new evaluation pipeline
# ---------------------------------------------------------------------------

def run_single_task_file(
    task_file_path: str,
    model_name: str,
    api_key: str,
    base_url: str,
    notion_key: str,
    timeout: int = 300,
) -> dict:
    """Execute *task_file_path* with the Notion Agent synchronously.

    This is a convenience wrapper around :pyfunc:`run_single_task` that is
    compatible with the signature expected by the *new* unified evaluation
    pipeline located in ``src/evaluation/pipeline.py``.  It hides the
    asynchronous boilerplate for spinning up the MCP server and running the
    agent, returning a *dict* with ``success``, ``output`` and ``error`` keys
    similar to what the pipeline expects.

    Parameters
    ----------
    task_file_path : str
        Path to the Markdown task description file.
    model_name : str
        The name of the model to use for the evaluation (e.g. ``gpt-4o``).
    api_key : str
        API key for the model provider.
    base_url : str
        Base URL for the model provider.
    notion_key : str
        Notion integration token used by the MCP server.
    timeout : int, optional
        Maximum time (in seconds) to allow the model to run before aborting.

    Returns
    -------
    dict
        A mapping with the following keys:

        ``success``
            ``True`` when the task ran without raising, ``False`` otherwise.
        ``output``
            Raw assistant response as a *str* (may be empty on error).
        ``error``
            Error message when ``success`` is ``False``.
    """

    task_path = Path(task_file_path)

    try:
        # -------------------------------------------------------------------
        # Prepare model provider & MCP server (async context)                 
        # -------------------------------------------------------------------
        custom_model_provider = create_model_provider(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
        )

        async def _run() -> str:
            """Internal coroutine that performs the actual evaluation."""
            async with await create_mcp_server(notion_key) as server:
                agent = Agent(name="Notion Agent", mcp_servers=[server])
                ModelSettings.tool_choice = "required"

                task_content = read_task_file(task_path)

                # Delegate to the original *async* implementation to stream
                # the response.
                return await run_single_task(agent, task_content, custom_model_provider)

        # -------------------------------------------------------------------
        # Execute with timeout handling                                       
        # -------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------

async def main(task_file: Path) -> int:
    """Run the Notion batch task runner."""
    try:
        # Environment & config
        notion_key = get_notion_key()
        custom_model_provider = create_model_provider()

        # Prepare MCP server
        async with await create_mcp_server(notion_key) as server:
            # Build the agent
            agent = Agent(
                name="Notion Agent",
                mcp_servers=[server],
            )
            ModelSettings.tool_choice = "required"

            # Trace for debugging in OpenAI dashboard
            trace_id = gen_trace_id()
            with trace(workflow_name="Notion Agent Batch Runner", trace_id=trace_id):
                print(
                    f"Trace URL: https://platform.openai.com/traces/trace?trace_id={trace_id}"
                )

                # Optional: list available tools (useful for debugging)
                run_context = RunContextWrapper(context=None)
                dummy_agent = Agent(name="Tmp", instructions="Tmp")
                tools = await server.list_tools(run_context, dummy_agent)
                print(f"{len(tools)} tools available\n")
                print(tools)
                
                # Read the task content and execute
                task_content = read_task_file(task_file)
                print(f"=== Executing Task from '{task_file}' ===\n")
                assistant_response = await run_single_task(agent, task_content, custom_model_provider)

                # -----------------------------------------------------------------
                # Persist results to ./logs/<timestamp>.json
                # -----------------------------------------------------------------
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_path = LOGS_DIR / f"{timestamp}.json"

                try:
                    with log_path.open("w", encoding="utf-8") as fp:
                        json.dump(assistant_response, fp, ensure_ascii=False, indent=2)
                    print(f"\nResults saved to '{log_path}'.")
                except Exception as log_exc:
                    print(f"Failed to write results log: {log_exc}")

    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    # Determine the task file path from CLI args (default: instructions.md)
    task_path = Path(sys.argv[1] if len(sys.argv) > 1 else "instructions.md")

    try:
        exit_code = asyncio.run(main(task_path))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Goodbye!")
        sys.exit(0)