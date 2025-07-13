#!/usr/bin/env python3
"""
MCPBench Test Suite Runner
==========================

Comprehensive test runner for all MCPBench evaluation pipeline tests.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_test_script(script_path: Path, description: str) -> bool:
    """Run a test script and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Script: {script_path.name}")
    print('='*60)
    
    try:
        result = subprocess.run([
            sys.executable, str(script_path)
        ], timeout=120)  # 2 minute timeout per test
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    """Run all test scripts."""
    print("MCPBench Evaluation Pipeline Test Suite")
    print("=" * 80)
    
    # Check environment setup
    required_vars = [
        'NOTION_API_KEY',
        'MCPBENCH_API_KEY', 
        'MCPBENCH_BASE_URL',
        'MCPBENCH_MODEL_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  WARNING: Missing environment variables: {missing_vars}")
        print("Some tests may have limited functionality.")
        print()
    
    # Test scripts to run
    test_scripts = [
        ("test_task_manager.py", "Task Discovery and Management"),
        ("test_page_duplication.py", "Page Duplication and Template Management"),
        ("test_verification.py", "Verification System"),
        ("test_results_reporting.py", "Results Reporting"),
        ("test_end_to_end.py", "End-to-End Pipeline Integration"),
    ]
    
    # Run all tests
    results = []
    tests_dir = Path(__file__).parent
    
    for script_name, description in test_scripts:
        script_path = tests_dir / script_name
        if script_path.exists():
            success = run_test_script(script_path, description)
            results.append((description, success))
        else:
            print(f"❌ Test script not found: {script_name}")
            results.append((description, False))
    
    # Print summary
    print(f"\n{'='*80}")
    print("TEST SUITE SUMMARY")
    print('='*80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    print()
    
    # List results
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {description}")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
        print("✅ The MCPBench evaluation pipeline is ready for use!")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED!")
        print("⚠️  Please review the failures above before using the pipeline.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)