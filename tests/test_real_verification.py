#!/usr/bin/env python3
"""
Test real task verification with the refactored system.
This simulates what happens during actual evaluation.
"""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.factory import MCPServiceFactory
from src.logger import get_logger

logger = get_logger(__name__)


def test_real_task_verification():
    """Test a real filesystem task verification."""
    print("Testing Real Task Verification")
    print("=" * 50)
    
    # Create components
    task_manager = MCPServiceFactory.create_task_manager("filesystem")
    state_manager = MCPServiceFactory.create_state_manager("filesystem")
    
    # Initialize
    if not state_manager.initialize():
        print("✗ Failed to initialize state manager")
        return False
    
    # Get a specific task
    tasks = task_manager.filter_tasks("basic_operations/task_1")
    if not tasks:
        print("✗ No task found")
        return False
    
    task = tasks[0]
    print(f"Testing task: {task.name}")
    print(f"Description: Create and write content to 'hello_world.txt'")
    
    # Set up task state
    if not state_manager.set_up(task):
        print("✗ Failed to set up task state")
        return False
    
    print(f"✓ Task state set up at: {state_manager.get_test_directory()}")
    
    # Task 1 expects us to create hello_world.txt with specific content
    test_dir = state_manager.get_test_directory()
    
    # Create the file that the agent would create
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"""Hello, World!
This is a test file created by MCPBench.
Current timestamp: {timestamp}"""
    
    hello_file = test_dir / "hello_world.txt"
    hello_file.write_text(content)
    print(f"✓ Created hello_world.txt with timestamp: {timestamp}")
    
    # Run the verification script
    print("\nRunning verification script...")
    
    # Set environment variable for test directory
    env = os.environ.copy()
    env['FILESYSTEM_TEST_DIR'] = str(test_dir)
    
    try:
        result = subprocess.run(
            [sys.executable, str(task.task_verification_path)],
            capture_output=True,
            text=True,
            timeout=10,
            env=env
        )
        
        if result.returncode == 0:
            print("✓ Verification PASSED!")
            if result.stdout:
                print(f"  Output: {result.stdout.strip()}")
        else:
            print("✗ Verification FAILED")
            if result.stderr:
                print(f"  Error: {result.stderr.strip()}")
            if result.stdout:
                print(f"  Output: {result.stdout.strip()}")
            
        success = result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("✗ Verification timed out")
        success = False
    except Exception as e:
        print(f"✗ Verification error: {e}")
        success = False
    
    # Clean up
    state_manager.clean_up(task)
    print("✓ Cleaned up task state")
    
    return success


def test_failing_verification():
    """Test a task that should fail verification."""
    print("\n\nTesting Failing Task Verification")
    print("=" * 50)
    
    # Create components
    task_manager = MCPServiceFactory.create_task_manager("filesystem")
    state_manager = MCPServiceFactory.create_state_manager("filesystem")
    
    # Initialize
    state_manager.initialize()
    
    # Get the same task
    tasks = task_manager.filter_tasks("basic_operations/task_1")
    task = tasks[0]
    
    # Set up task state
    state_manager.set_up(task)
    test_dir = state_manager.get_test_directory()
    
    print(f"Testing task: {task.name}")
    print("Intentionally NOT creating output file to test failure")
    
    # Run verification without creating output file
    env = os.environ.copy()
    env['FILESYSTEM_TEST_DIR'] = str(test_dir)
    
    result = subprocess.run(
        [sys.executable, str(task.task_verification_path)],
        capture_output=True,
        text=True,
        timeout=10,
        env=env
    )
    
    if result.returncode != 0:
        print("✓ Verification correctly FAILED (as expected)")
        if result.stderr:
            print(f"  Error: {result.stderr.strip()}")
    else:
        print("✗ Verification unexpectedly passed")
    
    # Clean up
    state_manager.clean_up(task)
    
    return result.returncode != 0


def main():
    """Run verification tests."""
    print("Real Task Verification Tests")
    print("=" * 70)
    print("Testing actual task verification with the refactored system...\n")
    
    # Test successful verification
    success1 = test_real_task_verification()
    
    # Test failing verification
    success2 = test_failing_verification()
    
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"✓ Successful verification test: {'PASS' if success1 else 'FAIL'}")
    print(f"✓ Failing verification test: {'PASS' if success2 else 'FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All verification tests passed!")
        print("The refactored system correctly handles both successful and failing tasks.")
    else:
        print("\n❌ Some verification tests failed.")
    
    return success1 and success2


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)