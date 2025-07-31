#!/usr/bin/env python3
"""
Verification script for Filesystem Task 4: Directory Analysis
"""

import sys
from pathlib import Path
import re

def get_test_directory() -> Path:
    """Get the test directory (hardcoded path)."""
    # Use the default persistent test environment
    return Path("/workspaces/MCPBench/test_environments/desktop")

def count_files_and_dirs(test_dir: Path) -> tuple[int, int, list]:
    """Count actual files and directories in test directory."""
    files = []
    dirs = []
    txt_files = []
    
    for item in test_dir.iterdir():
        if item.is_file():
            files.append(item.name)
            if item.suffix == '.txt':
                txt_files.append(item.name)
        elif item.is_dir():
            dirs.append(item.name)
    
    return len(files), len(dirs), txt_files

def verify_directory_analysis(test_dir: Path) -> bool:
    """Verify the directory analysis report was created correctly."""
    all_passed = True
    
    # Check if report file exists
    report_file = test_dir / "directory_report.txt"
    if not report_file.exists():
        print("❌ File 'directory_report.txt' not found")
        return False
    print("✅ File 'directory_report.txt' exists")
    
    # Get actual counts
    actual_files, actual_dirs, actual_txt_files = count_files_and_dirs(test_dir)
    print(f"\n📊 Actual counts:")
    print(f"- Files: {actual_files}")
    print(f"- Directories: {actual_dirs}")
    print(f"- .txt files: {len(actual_txt_files)}")
    print(f"- .txt files list: {actual_txt_files}")
    
    try:
        content = report_file.read_text()
        print(f"\n📄 Report content:\n{content}\n")
        
        # Check for required sections
        required_patterns = [
            "Directory Analysis Report",
            "Generated:",
            "Summary:",
            "Total files:",
            "Total directories:",
            "Text files in root:",
            "Root directory .txt files:",
            "Analysis complete"
        ]
        
        for pattern in required_patterns:
            if pattern in content:
                print(f"✅ Found required section: '{pattern}'")
            else:
                print(f"❌ Missing required section: '{pattern}'")
                all_passed = False
        
        # Check date format YYYY-MM-DD
        date_pattern = r'Generated: \d{4}-\d{2}-\d{2}'
        if re.search(date_pattern, content):
            print("✅ Contains date in YYYY-MM-DD format")
        else:
            print("❌ Missing or incorrect date format")
            all_passed = False
        
        # Verify file counts are reasonable (allowing for the report file itself)
        # Extract numbers from the report
        file_count_match = re.search(r'Total files:\s*(\d+)', content)
        dir_count_match = re.search(r'Total directories:\s*(\d+)', content)
        txt_count_match = re.search(r'Text files in root:\s*(\d+)', content)
        
        if file_count_match:
            reported_files = int(file_count_match.group(1))
            # Allow for +/- 1 difference due to the report file itself
            if abs(reported_files - actual_files) <= 1:
                print(f"✅ File count reasonable: {reported_files} (actual: {actual_files})")
            else:
                print(f"❌ File count mismatch: reported {reported_files}, actual {actual_files}")
                all_passed = False
        else:
            print("❌ Could not find file count in report")
            all_passed = False
        
        if dir_count_match:
            reported_dirs = int(dir_count_match.group(1))
            if reported_dirs == actual_dirs:
                print(f"✅ Directory count matches: {reported_dirs}")
            else:
                print(f"❌ Directory count mismatch: reported {reported_dirs}, actual {actual_dirs}")
                all_passed = False
        else:
            print("❌ Could not find directory count in report")
            all_passed = False
        
        # Check that some .txt files are listed
        txt_file_section = content.split("Root directory .txt files:")[1] if "Root directory .txt files:" in content else ""
        listed_txt_files = []
        for line in txt_file_section.split('\n'):
            if line.strip().startswith('- ') and line.strip().endswith('.txt'):
                listed_txt_files.append(line.strip()[2:])  # Remove '- ' prefix
        
        if len(listed_txt_files) > 0:
            print(f"✅ Found {len(listed_txt_files)} .txt files listed in report")
            # Check if at least half of the actual txt files are listed
            if len(listed_txt_files) >= len(actual_txt_files) * 0.5:
                print("✅ Reasonable number of .txt files listed")
            else:
                print(f"⚠️  Only {len(listed_txt_files)} of {len(actual_txt_files)} .txt files listed")
        else:
            print("❌ No .txt files found in the file listing")
            all_passed = False
            
    except Exception as e:
        print(f"❌ Error reading report file: {e}")
        all_passed = False
    
    return all_passed

def main():
    """Main verification function."""
    print("🔍 Verifying Filesystem Task 4: Directory Analysis")
    print("=" * 50)
    
    test_dir = get_test_directory()
    print(f"📁 Test directory: {test_dir}")
    
    if not verify_directory_analysis(test_dir):
        print("\n❌ Task 4 verification: FAIL")
        print("Directory analysis report was not created correctly")
        sys.exit(1)
    
    print("\n🎉 Task 4 verification: PASS")
    print("Directory analysis report created successfully with accurate information")
    sys.exit(0)

if __name__ == "__main__":
    main()