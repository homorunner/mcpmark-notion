#!/usr/bin/env python3
"""
Verification script for Filesystem Task 3: Create Directory Structure
"""

import sys
from pathlib import Path

def get_test_directory() -> Path:
    """Get the test directory using relative path."""
    # Use relative path from this script to test environment
    script_dir = Path(__file__).parent
    return script_dir / "../../../test_environments/desktop"

def verify_directory_structure(test_dir: Path) -> bool:
    """Verify the directory structure and files were created correctly."""
    all_passed = True
    
    # Expected structure
    project_dir = test_dir / "new_project"
    src_dir = project_dir / "src"
    docs_dir = project_dir / "docs"
    
    # Expected files and their content
    expected_files = {
        project_dir / "config.txt": "Configuration settings for the project",
        src_dir / "main.txt": "Main application code would go here",
        src_dir / "utils.txt": "Utility functions and helpers",
        docs_dir / "readme.txt": "Project documentation and setup instructions"
    }
    
    # Check main project directory
    if not project_dir.exists():
        print("❌ Directory 'new_project' not found")
        return False
    print("✅ Directory 'new_project' exists")
    
    # Check subdirectories
    if not src_dir.exists():
        print("❌ Subdirectory 'src' not found")
        all_passed = False
    else:
        print("✅ Subdirectory 'src' exists")
    
    if not docs_dir.exists():
        print("❌ Subdirectory 'docs' not found")
        all_passed = False
    else:
        print("✅ Subdirectory 'docs' exists")
    
    # Check each expected file
    print("\n📄 Checking files and content:")
    for file_path, expected_content in expected_files.items():
        if not file_path.exists():
            print(f"❌ File '{file_path.relative_to(test_dir)}' not found")
            all_passed = False
            continue
        
        print(f"✅ File '{file_path.relative_to(test_dir)}' exists")
        
        try:
            actual_content = file_path.read_text().strip()
            if actual_content == expected_content:
                print(f"✅ Content matches for '{file_path.name}'")
            else:
                print(f"❌ Content mismatch for '{file_path.name}'")
                print(f"   Expected: '{expected_content}'")
                print(f"   Actual: '{actual_content}'")
                all_passed = False
        except Exception as e:
            print(f"❌ Error reading '{file_path.relative_to(test_dir)}': {e}")
            all_passed = False
    
    # Verify directory structure matches specification
    print(f"\n📊 Structure summary:")
    print(f"- Main directory: {'✅' if project_dir.exists() else '❌'}")
    print(f"- Subdirectories: {'✅' if src_dir.exists() and docs_dir.exists() else '❌'}")
    print(f"- Total files: {len([f for f in expected_files.keys() if f.exists()])}/{len(expected_files)}")
    
    return all_passed

def main():
    """Main verification function."""
    print("🔍 Verifying Filesystem Task 3: Create Directory Structure")
    print("=" * 50)
    
    test_dir = get_test_directory()
    print(f"📁 Test directory: {test_dir}")
    
    if not verify_directory_structure(test_dir):
        print("\n❌ Task 3 verification: FAIL")
        print("Directory structure was not created correctly")
        sys.exit(1)
    
    print("\n🎉 Task 3 verification: PASS")
    print("Directory structure created successfully with correct files and content")
    sys.exit(0)

if __name__ == "__main__":
    main()