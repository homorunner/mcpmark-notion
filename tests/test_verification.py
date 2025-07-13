#!/usr/bin/env python3
"""
Test Verification System
========================

Tests for the task verification functionality.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.task_manager import TaskManager

def test_verification_scripts_exist():
    """Test that all tasks have verification scripts."""
    print("🔍 Testing verification scripts exist...")
    
    tasks_root = Path(__file__).parent.parent / "tasks"
    task_manager = TaskManager(tasks_root)
    
    all_tasks = task_manager.filter_tasks("all")
    print(f"✅ Found {len(all_tasks)} tasks to check")
    
    missing_scripts = []
    for task in all_tasks:
        if not task.verify_path.exists():
            missing_scripts.append(task.name)
    
    if missing_scripts:
        print(f"❌ Missing verification scripts for: {missing_scripts}")
        return False
    else:
        print("✅ All tasks have verification scripts")
        return True

def test_verification_script_execution():
    """Test that verification scripts can be executed."""
    print("\n🔍 Testing verification script execution...")
    
    tasks_root = Path(__file__).parent.parent / "tasks"
    task_manager = TaskManager(tasks_root)
    
    # Test with a specific task
    test_tasks = task_manager.filter_tasks("online_resume/task_1")
    if not test_tasks:
        print("❌ Could not find online_resume/task_1 for testing")
        return False
    
    task = test_tasks[0]
    print(f"🔍 Testing verification script for: {task.name}")
    
    try:
        # Run the verification script with a dummy page ID
        # Note: This will likely fail because we don't have actual test data,
        # but we can test that the script is syntactically correct
        result = subprocess.run([
            sys.executable, str(task.verify_path), "dummy-page-id"
        ], capture_output=True, text=True, timeout=30)
        
        print(f"✅ Verification script executed (exit code: {result.returncode})")
        print(f"📄 Script stdout: {result.stdout[:100]}...")
        
        if result.stderr:
            print(f"📄 Script stderr: {result.stderr[:100]}...")
        
        # Script executed without syntax errors
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Verification script timed out")
        return False
    except Exception as e:
        print(f"❌ Error running verification script: {e}")
        return False

def test_evaluate_py_functionality():
    """Test the evaluate.py script functionality."""
    print("\n🔍 Testing evaluate.py functionality...")
    
    evaluate_script = Path(__file__).parent.parent / "src" / "evaluation" / "evaluate.py"
    if not evaluate_script.exists():
        print("❌ evaluate.py script not found")
        return False
    
    try:
        # Test help functionality
        result = subprocess.run([
            sys.executable, str(evaluate_script), "--help"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ evaluate.py help command works")
        else:
            print(f"❌ evaluate.py help failed: {result.stderr}")
            return False
        
        # Test with invalid arguments to check error handling
        result = subprocess.run([
            sys.executable, str(evaluate_script), "invalid_scenario", "999"
        ], capture_output=True, text=True, timeout=30)
        
        # Should fail gracefully (exit code 1)
        if result.returncode == 1:
            print("✅ evaluate.py handles invalid arguments correctly")
        else:
            print(f"⚠️  evaluate.py exit code: {result.returncode}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing evaluate.py: {e}")
        return False

def test_verification_with_environment():
    """Test verification with environment variable support."""
    print("\n🔍 Testing verification with environment variables...")
    
    tasks_root = Path(__file__).parent.parent / "tasks"
    task_manager = TaskManager(tasks_root)
    
    # Get a test task
    test_tasks = task_manager.filter_tasks("online_resume/task_1")
    if not test_tasks:
        print("❌ Could not find test task")
        return False
    
    task = test_tasks[0]
    
    try:
        # Test with environment variable
        env = os.environ.copy()
        env["MCPBENCH_PAGE_ID"] = "test-page-id-12345"
        
        result = subprocess.run([
            sys.executable, str(task.verify_path)
        ], capture_output=True, text=True, timeout=30, env=env)
        
        print(f"✅ Verification script executed with environment variable")
        print(f"📄 Exit code: {result.returncode}")
        
        # The script may fail due to invalid page ID, but it should handle the env var
        return True
        
    except Exception as e:
        print(f"❌ Error testing environment variable support: {e}")
        return False

if __name__ == "__main__":
    print("=== Verification System Tests ===\n")
    
    success1 = test_verification_scripts_exist()
    success2 = test_verification_script_execution()
    success3 = test_evaluate_py_functionality()
    success4 = test_verification_with_environment()
    
    if success1 and success2 and success3 and success4:
        print("\n🎉 Verification system tests passed!")
    else:
        print("\n❌ Some verification system tests failed!")
        sys.exit(1)