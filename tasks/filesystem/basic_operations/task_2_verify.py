#!/usr/bin/env python3
"""
Verification script for Filesystem Task 2: Read and Edit File
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
    file_path = test_dir / "sample.txt"
    
    if not file_path.exists():
        print("❌ File 'sample.txt' not found")
        return False
    
    try:
        content = file_path.read_text()
        
        # Check original text was replaced
        if "This is a sample file for testing." in content:
            print("❌ Original text was not replaced")
            return False
        
        # Check new text is present
        if "This file has been modified by MCP." not in content:
            print("❌ New text not found")
            return False
        
        # Check for "Modified on" with date
        if not re.search(r'Modified on \d{4}-\d{2}-\d{2}', content):
            print("❌ Missing 'Modified on' with date")
            return False
        
        # Check other content preserved
        if "It contains some basic text content." not in content:
            print("❌ Original content was lost")
            return False
            
        print("✅ File edited correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    
    if verify_task(test_dir):
        print("🎉 Task 2 verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task 2 verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()