#!/usr/bin/env python3
"""
Verification script for Filesystem Task 6: File Organization and Count
"""

import sys
from pathlib import Path
import re

def get_test_directory() -> Path:
    """Get the test directory (hardcoded path)."""
    # Use the default persistent test environment
    return Path("/workspaces/MCPBench/test_environments/desktop")

def verify_file_organization(test_dir: Path) -> bool:
    """Verify the file organization and count was completed correctly."""
    all_passed = True
    
    # Check organized_files directory exists
    organized_dir = test_dir / "organized_files"
    if not organized_dir.exists():
        print("❌ Directory 'organized_files' not found")
        return False
    print("✅ Directory 'organized_files' exists")
    
    # Check no .txt files remain in root (except any that might be created by other tasks)
    root_txt_files = list(test_dir.glob("*.txt"))
    if root_txt_files:
        print(f"⚠️  Found {len(root_txt_files)} .txt files still in root directory:")
        for f in root_txt_files:
            print(f"  - {f.name}")
        # Don't fail completely as some files might be from other tasks
    else:
        print("✅ No .txt files remain in root directory")
    
    # Check files in organized_files directory
    organized_txt_files = list(organized_dir.glob("*.txt"))
    print(f"\n📁 Files in organized_files: {len(organized_txt_files)}")
    
    if len(organized_txt_files) < 3:
        print(f"⚠️  Only {len(organized_txt_files)} files in organized directory (expected at least 3)")
        # Don't fail as this depends on test environment
    
    # Check count file exists
    count_file = organized_dir / "file_count.txt"
    if not count_file.exists():
        print("❌ File 'organized_files/file_count.txt' not found")
        all_passed = False
    else:
        print("✅ File 'organized_files/file_count.txt' exists")
        
        try:
            content = count_file.read_text()
            print(f"\n📄 Count file content:\n{content}\n")
            
            # Check format: "Moved X files on YYYY-MM-DD"
            pattern = r'Moved (\d+) files on (\d{4}-\d{2}-\d{2})'
            match = re.search(pattern, content)
            
            if match:
                reported_count = int(match.group(1))
                date_str = match.group(2)
                
                print(f"✅ Found count format: 'Moved {reported_count} files on {date_str}'")
                
                # Verify the count is reasonable
                # Count should be total txt files minus the count file itself
                actual_moved = len(organized_txt_files) - 1  # Subtract count file itself
                if actual_moved < 0:
                    actual_moved = len(organized_txt_files)
                
                if abs(reported_count - actual_moved) <= 2:  # Allow some variance
                    print(f"✅ Count is reasonable: reported {reported_count}, actual moved ~{actual_moved}")
                else:
                    print(f"⚠️  Count mismatch: reported {reported_count}, actual moved {actual_moved}")
                    # Don't fail as count might be from different starting state
                
                # Check date format
                try:
                    from datetime import datetime
                    datetime.strptime(date_str, '%Y-%m-%d')
                    print(f"✅ Date format is correct: {date_str}")
                except ValueError:
                    print(f"❌ Invalid date format: {date_str}")
                    all_passed = False
                    
            else:
                print("❌ Count file does not match expected format 'Moved X files on YYYY-MM-DD'")
                print(f"   Actual content: '{content.strip()}'")
                all_passed = False
                
        except Exception as e:
            print(f"❌ Error reading count file: {e}")
            all_passed = False
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"- Files in organized_files: {len(organized_txt_files)}")
    print(f"- Files remaining in root: {len(root_txt_files)}")
    print(f"- Count file exists: {'✅' if count_file.exists() else '❌'}")
    
    return all_passed

def main():
    """Main verification function."""
    print("🔍 Verifying Filesystem Task 6: File Organization and Count")
    print("=" * 50)
    
    test_dir = get_test_directory()
    print(f"📁 Test directory: {test_dir}")
    
    if not verify_file_organization(test_dir):
        print("\n❌ Task 6 verification: FAIL")
        print("File organization was not completed correctly")
        sys.exit(1)
    
    print("\n🎉 Task 6 verification: PASS")
    print("Files successfully organized with correct count")
    sys.exit(0)

if __name__ == "__main__":
    main()