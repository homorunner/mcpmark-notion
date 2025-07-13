# MCPBench

A comprehensive evaluation framework for testing AI models' capabilities with the Notion API through Model Context Protocol (MCP).

## Project Structure

```
MCPBench/
├── src/                          # Source code
│   ├── core/                     # Core functionality modules
│   │   ├── notion_task_runner.py        # Main task execution engine
│   │   ├── page_duplication_manager.py  # Page duplication logic
│   │   ├── task_manager.py              # Task discovery and management
│   │   ├── task_template_manager.py     # Task template handling
│   │   └── results_reporter.py          # Results processing and reporting
│   ├── evaluation/               # Evaluation pipeline scripts
│   │   ├── pipeline.py                  # Unified evaluation pipeline (main entry point)
│   │   └── evaluate.py                  # Individual task verification tool
│   └── utils/                    # Utility modules
│       └── mcp_utils.py                 # MCP-related utilities
├── tasks/                        # Evaluation task definitions
│   ├── online_resume/            # Resume management tasks
│   ├── habit_tracker/            # Habit tracking tasks
│   ├── japan_travel_planner/     # Travel planning tasks
│   ├── job_applications/         # Job application management
│   ├── social_media_content_planning_system/  # Social media planning
│   ├── team_projects/            # Team collaboration tasks
│   └── utils/                    # Task utilities
├── data/                         # Data storage
│   ├── results/                  # Evaluation results (JSON, CSV)
│   └── logs/                     # Execution logs
├── docs/                         # Documentation
│   └── EVALUATION_README.md      # Detailed evaluation pipeline documentation
├── examples/                     # Example scripts and demos
├── scripts/                      # Utility scripts
├── tests/                        # Test files (future use)
├── materials/                    # External dependencies
│   └── notion_client/            # Notion API client
├── config.json                   # Configuration file
└── requirements.txt              # Python dependencies
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure settings:**
   Edit `config.json` with your API keys and settings.

3. **Run evaluation:**
   ```bash
   # Run all tasks with basic pipeline
   python src/evaluation/pipeline.py --model-name gpt-4 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks all
   
   # Run specific category with page duplication
   python src/evaluation/pipeline.py --model-name claude-3 --api-key YOUR_KEY --base-url YOUR_URL --notion-key YOUR_NOTION_KEY --tasks online_resume --duplicate-pages --source-pages '{"online_resume": "https://notion.so/page-url"}'
   
   # Verify individual task
   python src/evaluation/evaluate.py online_resume 1 --page-id abc123
   ```

## Documentation

- [Evaluation Pipeline Details](docs/EVALUATION_README.md) - Comprehensive guide on how the evaluation system works

## Key Features

- **Unified Evaluation Pipeline**: Single entry point for comprehensive model testing
- **Automated Task Discovery**: Automatically finds and organizes evaluation tasks
- **Page Duplication**: Optional page duplication for consistent testing environments
- **Parallel/Sequential Execution**: Configurable execution modes for optimal performance
- **Comprehensive Reporting**: JSON, CSV, and console output with detailed metrics
- **Multi-Model Support**: Compatible with various AI model providers (GPT, Claude, etc.)
- **Individual Task Verification**: Standalone verification tool for debugging
- **Extensible Architecture**: Easy to add new evaluation scenarios and task categories

## Task Categories

- **Online Resume**: Profile and skill management
- **Habit Tracker**: Personal productivity tracking
- **Travel Planning**: Trip organization and planning
- **Job Applications**: Application and interview management
- **Social Media**: Content planning and scheduling
- **Team Projects**: Collaboration and project management

## Testing

The project includes a comprehensive test suite to validate all pipeline functionality:

```bash
# Run all tests
conda activate mcpbench
python tests/run_all_tests.py

# Run individual test modules
python tests/test_task_manager.py
python tests/test_page_duplication.py
python tests/test_verification.py
python tests/test_results_reporting.py
python tests/test_end_to_end.py

# See pipeline demonstration
python tests/test_pipeline_demo.py
```

See [tests/README.md](tests/README.md) for detailed testing information.

## Contributing

Tasks are organized in the `tasks/` directory. Each task should include:
- `description.md`: Task instructions for the AI model
- `verify.py`: Verification script to check task completion
