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

### Changed
- **BREAKING**: BaseTaskManager now requires only 3 abstract methods instead of 9
  - `_get_service_directory_name()`
  - `_get_task_organization()`
  - `_create_task_instance()`
- FilesystemTaskManager refactored to remove duplicate LLM execution logic
- Factory pattern simplified with ServiceComponents registration
- Task discovery logic consolidated in base class
- Error messages standardized across all services

### Fixed
- Separation of concerns violation in FilesystemTaskManager
- Code duplication in service factory implementations
- Inconsistent error handling across services

### Removed
- ~400 lines of duplicate LLM execution code from FilesystemTaskManager
- Individual service factory classes (replaced with generic factory)
- Duplicate `extract_task_id` methods from services

### Performance
- Reduced codebase size by ~900 lines
- New service implementation reduced from ~200 to ~50-70 lines
- Factory code reduced by 15.7%
- Service implementations reduced by up to 65%

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

### For Error Handling

Use the new standardized error handling:
```python
from src.errors import ErrorHandler, standardize_error_message

# Automatic classification and retry logic
handler = ErrorHandler(service_name="your_service")
error_info = handler.handle(exception)
if handler.should_retry(error_info, attempt):
    delay = handler.get_retry_delay(error_info, attempt)
```