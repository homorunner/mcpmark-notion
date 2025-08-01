# MCPBench Evaluation Demo

This is a minimal demonstration of the MCPBench evaluation process, focusing on how LLM agents are evaluated on Notion tasks.

## Overview

This demo simplifies the full MCPBench pipeline to showcase the core evaluation logic:
1. **Task Selection**: Choose a predefined Notion task
2. **Agent Execution**: LLM agent performs the task using MCP server
3. **Verification**: Automated script verifies the task completion
4. **Results**: Display success/failure with detailed output

## Key Simplifications

- **No State Management**: Unlike the full pipeline, this demo doesn't automatically duplicate Notion pages. Users manually provide the target page ID.
- **Manual Task Selection**: Tasks are selected from a dropdown instead of automatic discovery.
- **No Resume/Retry Logic**: Simplified error handling without complex retry mechanisms.
- **Streamlined UI**: Simple web interface for easy demonstration.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Notion**:
   - Create a Notion integration: https://www.notion.so/my-integrations
   - Get your integration token (starts with `ntn_`)
   - Share the target Notion page with your integration

3. **Configure OpenAI** (if not using environment variable):
   - Get your API key from https://platform.openai.com/api-keys
   - Or set `OPENAI_API_KEY` environment variable

## Running the Demo

1. **Start the application**:
   ```bash
   streamlit run app.py
   ```

2. **Configure in the sidebar**:
   - Select the LLM model (default: gpt-4o)
   - Enter your OpenAI API key
   - Enter your Notion integration token

3. **Select and run a task**:
   - Choose a task from the dropdown
   - Enter the Notion page ID where the task should be performed
   - Click "Run Evaluation"

4. **View results**:
   - Execution status (Success/Failed)
   - Verification result (Passed/Failed)
   - Detailed output and error messages
   - Agent conversation history

## Example Tasks

- **Habit Tracker - Task 1**: Add a new habit "no phone after 10pm" and mark it complete for Thursday-Sunday
- **Job Applications - Task 1**: Add a Google software engineer application
- **Online Resume - Task 1**: Add work experience at Apple

## Architecture

```
presentation/
├── app.py                 # Streamlit UI
├── demo_evaluator.py      # Orchestrates execution and verification
├── demo_agent.py          # Handles LLM + MCP server interaction
├── demo_task_manager.py   # Manages task selection and verification
└── requirements.txt       # Python dependencies
```

## How It Works

1. **Task Loading**: The task manager reads task descriptions from the `tasks/notion/` directory
2. **Agent Execution**: The agent uses OpenAI's API and MCP Notion server to perform the task
3. **Verification**: Python scripts verify the task was completed correctly by checking the Notion API
4. **Result Display**: Success/failure is shown with detailed logs

This demo preserves the core evaluation logic while removing complexity around automation, making it ideal for understanding how MCPBench evaluates LLM agents.