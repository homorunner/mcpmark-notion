#!/usr/bin/env python3
"""
Verification script for Filesystem Task 2: Read and Edit File
"""

import sys
from pathlib import Path
import re

def get_test_directory() -> Path:
    """Get the test directory using relative path."""
    # Use relative path from this script to test environment
    script_dir = Path(__file__).parent
    return script_dir / "../../../test_environments/desktop"

def verify_file_edit(test_dir: Path) -> bool:
    """Verify the file was edited correctly."""
    all_passed = True
    
    # Check if file exists
    sample_file = test_dir / "sample.txt"
    if not sample_file.exists():
        print("❌ File 'sample.txt' not found")
        return False
    print("✅ File 'sample.txt' exists")
    
    try:
        content = sample_file.read_text()
        print(f"\n📄 File content:\n{content}\n")
        
        # Check that original text was replaced
        if "This is a sample file for testing." in content:
            print("❌ Original text was not replaced")
            all_passed = False
        else:
            print("✅ Original text was replaced")
        
        # Check that new text is present
        if "This file has been modified by MCP." in content:
            print("✅ New text 'This file has been modified by MCP.' found")
        else:
            print("❌ New text 'This file has been modified by MCP.' not found")
            all_passed = False
        
        # Check for "Modified on" with date
        if "Modified on" in content:
            print("✅ Contains 'Modified on' text")
            
            # Check for date format YYYY-MM-DD
            date_pattern = r'Modified on \d{4}-\d{2}-\d{2}'
            if re.search(date_pattern, content):
                print("✅ Contains 'Modified on' with date in YYYY-MM-DD format")
            else:
                print("❌ 'Modified on' found but date not in YYYY-MM-DD format")
                all_passed = False
        else:
            print("❌ Missing 'Modified on' text")
            all_passed = False
        
        # Check that other original content is preserved
        if "It contains some basic text content." in content:
            print("✅ Other original content preserved")
        else:
            print("❌ Some original content was lost")
            all_passed = False
            
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        all_passed = False
    
    return all_passed

def main():
    """Main verification function."""
    print("🔍 Verifying Filesystem Task 2: Read and Edit File")
    print("=" * 50)
    
    test_dir = get_test_directory()
    print(f"📁 Test directory: {test_dir}")
    
    if not verify_file_edit(test_dir):
        print("\n❌ Task 2 verification: FAIL")
        print("File was not edited correctly")
        sys.exit(1)
    
    print("\n🎉 Task 2 verification: PASS")
    print("File was edited successfully with correct changes")
    sys.exit(0)

if __name__ == "__main__":
    main()