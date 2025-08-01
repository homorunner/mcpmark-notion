#!/usr/bin/env python3
"""
Verification script for Filesystem Task 5: File Sorting by Content
"""

import sys
import os
from pathlib import Path

def get_test_directory() -> Path:
    """Get the test directory from FILESYSTEM_TEST_ROOT env var."""
    test_root = os.environ.get("FILESYSTEM_TEST_ROOT")
    if not test_root:
        raise ValueError("FILESYSTEM_TEST_ROOT environment variable is required")
    return Path(test_root)

def verify_task(test_dir: Path) -> bool:
    """Verify the task was completed correctly."""
    has_test_dir = test_dir / "has_test"
    no_test_dir = test_dir / "no_test"
    
    # Check directories exist
    if not has_test_dir.exists():
        print("❌ Directory 'has_test' not found")
        return False
    
    if not no_test_dir.exists():
        print("❌ Directory 'no_test' not found")
        return False
    
    # Check no .txt files remain in root
    root_txt_files = list(test_dir.glob("*.txt"))
    if root_txt_files:
        print(f"❌ Found {len(root_txt_files)} .txt files still in root")
        return False
    
    # Check files in has_test directory contain "test"
    has_test_files = list(has_test_dir.glob("*.txt"))
    for file_path in has_test_files:
        try:
            content = file_path.read_text().lower()
            if "test" not in content:
                print(f"❌ File '{file_path.name}' doesn't contain 'test'")
                return False
        except Exception as e:
            print(f"❌ Error reading '{file_path.name}': {e}")
            return False
    
    # Check files in no_test directory don't contain "test"
    no_test_files = list(no_test_dir.glob("*.txt"))
    for file_path in no_test_files:
        try:
            content = file_path.read_text().lower()
            if "test" in content:
                print(f"❌ File '{file_path.name}' contains 'test'")
                return False
        except Exception as e:
            print(f"❌ Error reading '{file_path.name}': {e}")
            return False
    
    print("✅ Files sorted correctly by content")
    return True

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    
    if verify_task(test_dir):
        print("🎉 Task 5 verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task 5 verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()