#!/usr/bin/env python3
"""
Verification script for Filesystem Task 5: File Sorting by Content
"""

import sys
from pathlib import Path

def get_test_directory() -> Path:
    """Get the test directory using relative path."""
    # Use relative path from this script to test environment
    script_dir = Path(__file__).parent
    return script_dir / "../../../test_environments/desktop"

def verify_file_sorting(test_dir: Path) -> bool:
    """Verify the file sorting by content was completed correctly."""
    all_passed = True
    
    # Check directories exist
    has_test_dir = test_dir / "has_test"
    no_test_dir = test_dir / "no_test"
    
    if not has_test_dir.exists():
        print("❌ Directory 'has_test' not found")
        return False
    print("✅ Directory 'has_test' exists")
    
    if not no_test_dir.exists():
        print("❌ Directory 'no_test' not found")
        return False
    print("✅ Directory 'no_test' exists")
    
    # Check no .txt files remain in root
    root_txt_files = list(test_dir.glob("*.txt"))
    if root_txt_files:
        print(f"❌ Found {len(root_txt_files)} .txt files still in root directory:")
        for f in root_txt_files:
            print(f"  - {f.name}")
        all_passed = False
    else:
        print("✅ No .txt files remain in root directory")
    
    # Check files in has_test directory
    has_test_files = list(has_test_dir.glob("*.txt"))
    print(f"\n📁 Files in has_test: {len(has_test_files)}")
    
    for file_path in has_test_files:
        try:
            content = file_path.read_text().lower()
            if "test" in content:
                print(f"  ✅ {file_path.name} - correctly contains 'test'")
            else:
                print(f"  ❌ {file_path.name} - does NOT contain 'test' (incorrectly sorted)")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {file_path.name} - error reading file: {e}")
            all_passed = False
    
    # Check files in no_test directory
    no_test_files = list(no_test_dir.glob("*.txt"))
    print(f"\n📁 Files in no_test: {len(no_test_files)}")
    
    for file_path in no_test_files:
        try:
            content = file_path.read_text().lower()
            if "test" not in content:
                print(f"  ✅ {file_path.name} - correctly does NOT contain 'test'")
            else:
                print(f"  ❌ {file_path.name} - contains 'test' (incorrectly sorted)")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {file_path.name} - error reading file: {e}")
            all_passed = False
    
    # Summary
    total_sorted = len(has_test_files) + len(no_test_files)
    print(f"\n📊 Summary:")
    print(f"- Files with 'test': {len(has_test_files)}")
    print(f"- Files without 'test': {len(no_test_files)}")
    print(f"- Total files sorted: {total_sorted}")
    print(f"- Files remaining in root: {len(root_txt_files)}")
    
    if total_sorted < 3:
        print(f"⚠️  Only {total_sorted} files were sorted (expected at least 3)")
        # Don't fail for this, as it depends on test environment
    
    return all_passed

def main():
    """Main verification function."""
    print("🔍 Verifying Filesystem Task 5: File Sorting by Content")
    print("=" * 50)
    
    test_dir = get_test_directory()
    print(f"📁 Test directory: {test_dir}")
    
    if not verify_file_sorting(test_dir):
        print("\n❌ Task 5 verification: FAIL")
        print("Files were not sorted correctly by content")
        sys.exit(1)
    
    print("\n🎉 Task 5 verification: PASS")
    print("Files successfully sorted by content analysis")
    sys.exit(0)

if __name__ == "__main__":
    main()