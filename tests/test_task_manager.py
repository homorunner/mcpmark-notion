#!/usr/bin/env python3
"""
Test Task Discovery and Management
=================================

Tests for the task discovery and management functionality.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.task_manager import TaskManager

def test_task_discovery():
    """Test that task manager can discover all available tasks."""
    print("🔍 Testing task discovery...")
    
    # Initialize TaskManager with correct tasks path
    tasks_root = Path(__file__).parent.parent / "tasks"
    task_manager = TaskManager(tasks_root)
    
    # Test structure validation
    print("🔍 Validating task structure...")
    issues = task_manager.validate_task_structure()
    if issues:
        print("⚠️  Structure issues found:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ Task structure validation passed")
    
    # Test discovering all tasks
    all_tasks = task_manager.filter_tasks("all")
    print(f"✅ Found {len(all_tasks)} total tasks")
    
    # Get task summary
    summary = task_manager.get_task_summary()
    print("📊 Task summary by category:")
    for category, count in summary.items():
        print(f"   {category}: {count} tasks")
    
    # Verify we have expected categories
    categories = set(task.name.split('/')[0] for task in all_tasks)
    expected_categories = {
        'online_resume', 'habit_tracker', 'japan_travel_planner', 
        'job_applications', 'social_media_content_planning_system', 'team_projects'
    }
    
    print(f"📋 Available categories: {sorted(categories)}")
    
    missing = expected_categories - categories
    if missing:
        print(f"⚠️  Missing expected categories: {missing}")
    
    extra = categories - expected_categories
    if extra:
        print(f"ℹ️  Found additional categories: {extra}")
    
    # Test category filtering
    resume_tasks = task_manager.filter_tasks("online_resume")
    print(f"✅ Found {len(resume_tasks)} online_resume tasks")
    
    # Test individual task filtering
    specific_task = task_manager.filter_tasks("online_resume/task_1")
    print(f"✅ Found {len(specific_task)} tasks for online_resume/task_1")
    
    if len(specific_task) == 1:
        task = specific_task[0]
        print(f"📄 Task details: {task.name}")
        print(f"📄 Description file: {task.description_path}")
        print(f"📄 Verify script: {task.verify_path}")
        
        # Verify files exist
        if task.description_path.exists():
            print("✅ Description file exists")
            # Read and show first few lines
            desc = task.get_description()
            first_line = desc.split('\n')[0] if desc else ""
            print(f"📄 Description preview: {first_line[:100]}...")
        else:
            print("❌ Description file missing")
            
        if task.verify_path and task.verify_path.exists():
            print("✅ Verify script exists")
        else:
            print("❌ Verify script missing")
    
    return len(all_tasks) > 0

if __name__ == "__main__":
    success = test_task_discovery()
    if success:
        print("\n🎉 Task discovery tests passed!")
    else:
        print("\n❌ Task discovery tests failed!")
        sys.exit(1)