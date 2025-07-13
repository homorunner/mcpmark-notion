● MCPBench Evaluation Pipeline - How It Works

  Overview

  The MCPBench evaluation pipeline is an automated system that tests how well AI models can perform
   tasks using the Notion API. It evaluates models by giving them specific tasks to complete and
  then verifying whether they accomplished those tasks correctly.

  Input Requirements

  To run an evaluation, you need:

  1. Model Configuration
    - Model name (e.g., "gpt-4", "claude-3")
    - API key for accessing the model
    - Base URL for the model provider's API
  2. Notion Setup
    - Notion API key (to access and modify Notion pages)
    - Source page URLs (the "template" pages that tasks will work with)
  3. Task Selection
    - Choose which tasks to run: all tasks, a specific category (like "online_resume"), or
  individual tasks (like "online_resume/task_1")

  How the Pipeline Works

  Step 1: Task Discovery

  The system scans the tasks/ directory and finds all available evaluation tasks. Each task has:
  - A description file (description.md) explaining what the AI should do
  - A verification script (verify.py) that checks if the task was completed correctly

  Step 2: Page Preparation (With Duplication Feature)

  For each task, the pipeline:
  1. Creates a fresh copy of the source page using Playwright (web automation)
  2. Extracts the page ID from the duplicated page's URL
  3. Modifies the task description to tell the AI model to work on this specific page copy instead
  of searching for pages by name

  This ensures each evaluation starts with a clean, identical setup.

  Step 3: Task Execution

  For each task, the pipeline:
  1. Loads the task description (now pointing to the duplicated page)
  2. Creates an AI agent connected to the Notion API
  3. Gives the task to the AI model and lets it work
  4. Monitors execution with timeout protection
  5. Records how long it takes and any errors that occur

  Step 4: Verification

  After the AI completes its work:
  1. Runs the verification script to check if the task was done correctly
  2. Uses the same duplicated page that the AI worked on for consistency
  3. Records success or failure based on specific criteria (e.g., "Was the skill 'LLM Training'
  added with 50% proficiency?")

  Step 5: Cleanup

  1. Deletes the duplicated page to avoid cluttering the Notion workspace
  2. Preserves the original source page unchanged for future evaluations

  Step 6: Results Processing

  The pipeline can run tasks either:
  - Sequentially (one after another) - required when using page duplication
  - In parallel (multiple at once) - faster but only without page duplication

  Output and Reporting

  The pipeline generates comprehensive results:

  Console Output

  - Real-time progress updates during execution
  - Success/failure status for each task
  - Execution times and error messages
  - Final summary with success rates

  JSON Report

  - Complete evaluation data in machine-readable format
  - Individual task results with timestamps
  - Model configuration and metadata
  - Detailed error information

  CSV Reports

  - Spreadsheet-friendly format with task results
  - Category-wise summary statistics
  - Easy to analyze trends and patterns

  Key Metrics

  - Overall success rate (percentage of tasks completed correctly)
  - Category-wise performance (how well the model does on different types of tasks)
  - Execution times (how long each task takes)
  - Failure analysis (what went wrong for failed tasks)

  Example Evaluation Flow

  Input: "Evaluate GPT-4 on all online resume tasks"

  1. Discovery: Find 4 online resume tasks
  2. For each task:
    - Duplicate the "Maya Zhang" resume page → New page ID: abc123...
    - Modify task: "Find page named 'Maya Zhang'" → "Use page with ID: abc123..."
    - Send to GPT-4: "Add skill 'LLM Training' with type 'Machine Learning Engineer' at 50% level"
    - GPT-4 works on the page through Notion API
    - Verify: Check if the skill was added correctly on page abc123...
    - Cleanup: Delete the duplicated page
  3. Results: "3/4 tasks passed (75% success rate)"

  Output: Detailed report showing which tasks passed/failed, execution times, and specific error
  messages for debugging.

  Benefits of This Approach

  - Consistent Testing: Every evaluation starts from the same clean state
  - No Interference: Multiple evaluations don't affect each other
  - Reproducible Results: Same conditions every time
  - Detailed Insights: Know exactly what works and what doesn't
  - Scalable: Can test many models and tasks efficiently

  This pipeline essentially creates a standardized "test suite" for AI models working with Notion,
  ensuring fair and reliable comparisons of their capabilities.