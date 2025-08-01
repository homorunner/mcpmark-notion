#!/usr/bin/env python3
"""
Verification script for Filesystem Task 6: File Organization and Count
"""

import sys
import os
from pathlib import Path
import re

def get_test_directory() -> Path:
    """Get the test directory from FILESYSTEM_TEST_ROOT env var."""
    test_root = os.environ.get("FILESYSTEM_TEST_ROOT")
    if not test_root:
        raise ValueError("FILESYSTEM_TEST_ROOT environment variable is required")
    return Path(test_root)

def verify_task(test_dir: Path) -> bool:
    """Verify the task was completed correctly."""
    organized_dir = test_dir / "organized_files"
    count_file = organized_dir / "file_count.txt"
    
    # Check organized_files directory exists
    if not organized_dir.exists():
        print("❌ Directory 'organized_files' not found")
        return False
    
    # Check no .txt files remain in root
    root_txt_files = list(test_dir.glob("*.txt"))
    if root_txt_files:
        print(f"❌ Found {len(root_txt_files)} .txt files still in root")
        return False
    
    # Check count file exists
    if not count_file.exists():
        print("❌ File 'organized_files/file_count.txt' not found")
        return False
    
    # Check count file format
    try:
        content = count_file.read_text()
        pattern = r'Moved (\d+) files on (\d{4}-\d{2}-\d{2})'
        if not re.search(pattern, content):
            print("❌ Count file format incorrect")
            return False
    except Exception as e:
        print(f"❌ Error reading count file: {e}")
        return False
    
    print("✅ Files organized with correct count")
    return True

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    
    if verify_task(test_dir):
        print("🎉 Task 6 verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task 6 verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()