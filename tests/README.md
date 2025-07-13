# MCPBench Test Suite

This directory contains comprehensive tests for the MCPBench evaluation pipeline.

## Test Files

| Test File | Description |
|-----------|-------------|
| `test_task_manager.py` | Tests task discovery and management functionality |
| `test_page_duplication.py` | Tests page duplication utilities and template management |
| `test_verification.py` | Tests task verification system |
| `test_results_reporting.py` | Tests results reporting (JSON, CSV) |
| `test_end_to_end.py` | Tests complete pipeline integration |
| `run_all_tests.py` | Runs all tests and provides summary |

## Running Tests

### Individual Tests

```bash
# Activate conda environment
conda activate mcpbench

# Run individual test files
python tests/test_task_manager.py
python tests/test_page_duplication.py
python tests/test_verification.py
python tests/test_results_reporting.py
python tests/test_end_to_end.py
```

### All Tests

```bash
# Run complete test suite
conda activate mcpbench
python tests/run_all_tests.py
```

## Environment Requirements

The tests require these environment variables to be set:

- `NOTION_API_KEY` - Your Notion API key
- `MCPBENCH_API_KEY` - API key for your chosen model provider  
- `MCPBENCH_BASE_URL` - Base URL for your model provider
- `MCPBENCH_MODEL_NAME` - Name of the model to test

## Test Coverage

The test suite covers:

✅ **Task Discovery** - Finding and parsing task definitions  
✅ **Page Duplication** - Template management and page ID injection  
✅ **Verification System** - Task verification script execution  
✅ **Results Reporting** - JSON and CSV report generation  
✅ **End-to-End Integration** - Complete pipeline functionality  
✅ **Error Handling** - Graceful failure modes  
✅ **Environment Setup** - Configuration validation  

## Test Results

Tests output detailed information about:
- Component initialization
- Function execution success/failure
- Data validation
- File operations
- Integration between components

All tests are designed to run quickly without making external API calls unless necessary for basic validation.