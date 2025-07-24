# Task Discovery Pattern Analysis

## Overview
This document analyzes the task discovery implementations across Notion, GitHub, and Filesystem services to identify common patterns and areas for improvement in the base class.

## Common Patterns Identified

### 1. Task Discovery Flow
All three services follow the same high-level pattern:
1. Check if tasks root and service directory exist
2. Iterate through category directories
3. Find task files within each category
4. Extract task ID from filename/directory name
5. Validate both instruction and verification files exist
6. Create task objects and add to list
7. Sort tasks by category and ID

### 2. Task ID Extraction
GitHub and Filesystem have identical implementations:
```python
def _extract_task_id(self, filename: str) -> Optional[int]:
    """Extract task ID from filename like 'task_1.md'."""
    import re
    match = re.match(r'task_(\d+)\.md', filename)
    return int(match.group(1)) if match else None
```

Notion handles it inline but follows the same pattern:
```python
try:
    task_id = int(task_dir.name.split("_")[1])
except (IndexError, ValueError):
    continue
```

### 3. File Organization Patterns
- **Notion**: Directory-based (`task_X/description.md`, `task_X/verify.py`)
- **GitHub/Filesystem**: File-based (`task_X.md`, `task_X_verify.py`)

## Duplicated Code Found

### FilesystemTaskManager
The FilesystemTaskManager has a complete duplicate implementation of `discover_all_tasks` (lines 134-182) that reimplements all the logic already in the base class. This violates the DRY principle and should be removed.

### Task File Info Dictionary
Each service uses slightly different keys for the same data:
- Notion: `{"task_id", "instruction_path", "verification_path"}`
- GitHub: `{"task_id", "instruction_path", "verification_path"}`
- Filesystem: `{"task_id", "description", "verification"}`

## Recommendations for Base Class Enhancement

### 1. Add Common Helper Methods
```python
# In BaseTaskManager
def _extract_task_id_from_filename(self, filename: str, pattern: str = r'task_(\d+)') -> Optional[int]:
    """Extract task ID from filename using regex pattern.
    
    Args:
        filename: The filename to extract ID from
        pattern: Regex pattern with capture group for ID
    
    Returns:
        Task ID or None if extraction fails
    """
    import re
    match = re.match(pattern + r'\.md', filename)
    return int(match.group(1)) if match else None

def _extract_task_id_from_dirname(self, dirname: str) -> Optional[int]:
    """Extract task ID from directory name like 'task_1'.
    
    Args:
        dirname: The directory name to extract ID from
    
    Returns:
        Task ID or None if extraction fails
    """
    if not dirname.startswith("task_"):
        return None
    try:
        return int(dirname.split("_")[1])
    except (IndexError, ValueError):
        return None
```

### 2. Standardize Task File Info Dictionary
Define a standard structure in the base class:
```python
@dataclass
class TaskFileInfo:
    """Standard structure for task file information."""
    task_id: int
    instruction_path: Path
    verification_path: Path
    # Optional service-specific data
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 3. Add File Pattern Hook Method
```python
# In BaseTaskManager
def _get_task_file_pattern(self) -> str:
    """Get the file pattern for task discovery.
    
    Returns:
        Glob pattern for finding task files
    """
    return "task_*.md"  # Default pattern

def _is_directory_based_tasks(self) -> bool:
    """Check if tasks are organized in directories (like Notion) or files (like GitHub).
    
    Returns:
        True if directory-based, False if file-based
    """
    return False  # Default is file-based
```

### 4. Enhanced Base Implementation
The base class `discover_all_tasks` could be enhanced to handle both directory-based and file-based task organizations:

```python
def _find_task_files(self, category_dir: Path) -> List[Dict[str, Any]]:
    """Find task files in category directory.
    
    This enhanced version can handle both directory-based (Notion) 
    and file-based (GitHub/Filesystem) task organizations.
    """
    task_files = []
    
    if self._is_directory_based_tasks():
        # Directory-based (like Notion)
        for task_dir in category_dir.iterdir():
            if not task_dir.is_dir():
                continue
            
            task_id = self._extract_task_id_from_dirname(task_dir.name)
            if task_id is None:
                continue
            
            instruction_path = task_dir / self._get_instruction_filename()
            verification_path = task_dir / self._get_verification_filename()
            
            if instruction_path.exists() and verification_path.exists():
                task_files.append({
                    "task_id": task_id,
                    "instruction_path": instruction_path,
                    "verification_path": verification_path
                })
    else:
        # File-based (like GitHub/Filesystem)
        pattern = self._get_task_file_pattern()
        for task_file in category_dir.glob(pattern):
            task_id = self._extract_task_id_from_filename(task_file.name)
            if task_id is None:
                continue
            
            verification_path = self._get_verification_path(task_file, task_id)
            if not verification_path.exists():
                logger.warning("No verification script found for task: %s", task_file)
                continue
            
            task_files.append({
                "task_id": task_id,
                "instruction_path": task_file,
                "verification_path": verification_path
            })
    
    return task_files
```

### 5. Remove Duplicate Code
1. Remove the entire `discover_all_tasks` method from FilesystemTaskManager (lines 134-182)
2. Remove `_extract_task_id` from GitHub and Filesystem task managers
3. Update services to use the new base class helper methods

## Benefits of These Changes

1. **DRY Principle**: Eliminates ~150 lines of duplicated code
2. **Consistency**: Standardizes task discovery across all services
3. **Maintainability**: Changes to task discovery logic only need to be made in one place
4. **Extensibility**: New services can easily hook into the existing pattern
5. **Type Safety**: Using dataclasses for task file info improves type checking

## Implementation Priority

1. **High Priority**: Remove duplicate `discover_all_tasks` from FilesystemTaskManager
2. **Medium Priority**: Move `_extract_task_id` to base class
3. **Low Priority**: Standardize task file info structure (requires updates to all services)