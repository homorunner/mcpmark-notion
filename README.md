# MCPBench

A comprehensive evaluation framework for testing AI models' capabilities with the Notion API through Model Context Protocol (MCP).

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export NOTION_API_KEY="your_notion_key"
   export MCPBENCH_API_KEY="your_model_api_key"
   export MCPBENCH_BASE_URL="your_model_base_url"
   export MCPBENCH_MODEL_NAME="your_model_name"
   ```

3. **Run evaluation:**
   ```bash
   # Evaluate all tasks
   python src/evaluation/pipeline.py --model-name gpt-4o --api-key $MCPBENCH_API_KEY --base-url $MCPBENCH_BASE_URL --notion-key $NOTION_API_KEY --tasks all
   
   # Evaluate specific category
   python src/evaluation/pipeline.py --model-name gpt-4o --api-key $MCPBENCH_API_KEY --base-url $MCPBENCH_BASE_URL --notion-key $NOTION_API_KEY --tasks online_resume
   
   # Run with page duplication for consistent testing
   python src/evaluation/pipeline.py --model-name gpt-4o --api-key $MCPBENCH_API_KEY --base-url $MCPBENCH_BASE_URL --notion-key $NOTION_API_KEY --tasks online_resume --duplicate-pages --source-pages '{"online_resume": "https://notion.so/page-url"}'
   ```

## Key Features

- **Unified Evaluation Pipeline**: Single entry point for comprehensive model testing
- **Automated Task Discovery**: 20 tasks across 6 categories (online_resume, habit_tracker, japan_travel_planner, job_applications, social_media_content_planning_system, team_projects)
- **Page Duplication**: Optional page duplication for consistent testing environments
- **Comprehensive Reporting**: JSON, CSV, and console output with detailed metrics
- **Multi-Model Support**: Compatible with OpenAI, Anthropic, Google, and other providers
- **Parallel/Sequential Execution**: Configurable execution modes

## Testing

Run the complete test suite to validate functionality:

```bash
conda activate mcpbench
python tests/run_all_tests.py
```

See [tests/README.md](tests/README.md) for detailed testing information.

## Documentation

- [Evaluation Pipeline Details](docs/EVALUATION_README.md) - Comprehensive guide on how the evaluation system works

## Project Structure

```
MCPBench/
├── src/evaluation/
│   ├── pipeline.py          # Main evaluation pipeline
│   └── evaluate.py          # Individual task verification
├── tasks/                   # 20 evaluation tasks across 6 categories
├── tests/                   # Comprehensive test suite  
├── docs/                    # Documentation
└── data/results/           # Evaluation outputs (JSON, CSV)
```

## Contributing

Tasks are organized in the `tasks/` directory. Each task includes:
- `description.md`: Task instructions for the AI model
- `verify.py`: Verification script to check task completion