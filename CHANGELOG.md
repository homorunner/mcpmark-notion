# Changelog

All notable changes to MCPBench will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Centralized configuration schema with validation (`src/config/config_schema.py`)
- Unified error taxonomy and handling system (`src/errors.py`)
- Generic service factory pattern to reduce code duplication
- Smart defaults in BaseTaskManager for task discovery
- Configuration export/import capabilities
- Automatic retry strategies based on error types
- Consolidated service definitions in single source (`src/services.py`)
- Generic MCP server builder (`src/agent_mcp_builder.py`)
- Dynamic service loading from definitions
- Runtime template substitution for sensitive values

### Changed
- **BREAKING**: BaseTaskManager now requires only 3 abstract methods instead of 9
  - `_get_service_directory_name()`
  - `_get_task_organization()`
  - `_create_task_instance()`
- FilesystemTaskManager refactored to remove duplicate LLM execution logic
- Factory pattern simplified with ServiceComponents registration
- Task discovery logic consolidated in base class
- Error messages standardized across all services
- Agent uses non-streaming API by default to avoid pydantic validation errors
- MCP server creation moved to centralized builder pattern
- Service configuration mapping now uses dictionary lookups instead of if-elif chains

### Fixed
- Separation of concerns violation in FilesystemTaskManager
- Code duplication in service factory implementations
- Inconsistent error handling across services
- Pydantic logprobs validation error in streaming mode
- Over-engineered error handling reduced from 358 to 57 lines

### Removed
- ~400 lines of duplicate LLM execution code from FilesystemTaskManager
- Individual service factory classes (replaced with generic factory)
- Duplicate `extract_task_id` methods from services
- ~200 lines of hardcoded service-specific logic in agent.py
- Complex error classification system (kept only essential retry logic)
- Scattered service-specific if-elif chains across multiple files

### Performance
- Reduced codebase size by ~900 lines
- New service implementation reduced from ~200 to ~50-70 lines
- Factory code reduced by 15.7%
- Service implementations reduced by up to 65%
- Error handling reduced by 84% while maintaining functionality

## Migration Guide

### For Service Implementers

If you have custom services, you'll need to update them to use the new base class:

1. Remove any LLM execution logic from task managers
2. Implement the 3 required abstract methods:
   ```python
   def _get_service_directory_name(self) -> str:
       return "your_service"
   
   def _get_task_organization(self) -> str:
       return "file"  # or "directory"
   
   def _create_task_instance(self, **kwargs) -> YourTask:
       return YourTask(**kwargs)
   ```

3. Register your service in the factory:
   ```python
   ServiceComponents(
       task_manager_class=YourTaskManager,
       state_manager_class=YourStateManager,
       login_helper_class=YourLoginHelper,
   )
   ```

### For Configuration

Environment variables remain the same, but you can now:
- Export configuration templates: `MCPServiceFactory.export_config_template("service", "path.yaml")`
- Validate configurations: `MCPServiceFactory.validate_config("service")`
- Get debug info: `MCPServiceFactory.get_config_info("service")`

### For Adding New Services

To add a new MCP service:
1. Add service definition to `src/services.py`:
   ```python
   "your_service": {
       "components": {
           "task_manager": "src.mcp_services.your_service.your_service_task_manager.YourServiceTaskManager",
           "state_manager": "src.mcp_services.your_service.your_service_state_manager.YourServiceStateManager",
           "login_helper": "src.mcp_services.your_service.your_service_login_helper.YourServiceLoginHelper",
       },
       "config_mapping": {
           "state_manager": {
               "api_key": "api_key",  # Maps config key to constructor param
           }
       },
       "mcp_server": {
           "type": "stdio",  # or "http"
           "command": "npx",
           "args": ["-y", "@your/mcp-server"],
           "requires_config": {
               "env": {
                   "YOUR_API_KEY": "{api_key}"  # Runtime substitution
               }
           }
       },
       "eval_config": {
           "api_key": "api_key"  # What to pass to agent
       }
   }
   ```

2. Implement the three service components (task_manager, state_manager, login_helper)
3. No need to modify agent.py, factory.py, or evaluator.py!

### For Error Handling

Use the simplified error handling:
```python
from src.errors import standardize_error_message, is_retryable_error, get_retry_delay

# Standardize error message
error_msg = standardize_error_message(str(exception), service="your_service")

# Check if retryable
if is_retryable_error(error_msg):
    delay = get_retry_delay(attempt)
    # Retry after delay
```