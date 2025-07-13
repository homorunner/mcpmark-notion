#!/usr/bin/env python3
"""
Test Results Reporting
======================

Tests for the results reporting functionality.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.results_reporter import ResultsReporter, EvaluationReport, TaskResult

def test_task_result_creation():
    """Test TaskResult object creation and serialization."""
    print("🔍 Testing TaskResult creation...")
    
    try:
        # Create a test task result
        task_result = TaskResult(
            category="online_resume",
            task_id=1,
            task_name="online_resume/task_1",
            success=True,
            execution_time=45.5,
            error_message=None
        )
        
        print("✅ TaskResult created successfully")
        print(f"📄 Task: {task_result.task_name}")
        print(f"📄 Success: {task_result.success}")
        print(f"📄 Time: {task_result.execution_time}s")
        print(f"📄 Status: {task_result.status}")
        
        # Test failed task result
        failed_result = TaskResult(
            category="online_resume",
            task_id=2,
            task_name="online_resume/task_2",
            success=False,
            execution_time=30.0,
            error_message="Verification failed: skill not found"
        )
        
        print("✅ Failed TaskResult created successfully")
        print(f"📄 Failed task status: {failed_result.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating TaskResult: {e}")
        return False

def test_evaluation_report_creation():
    """Test EvaluationReport creation and metrics calculation."""
    print("\n🔍 Testing EvaluationReport creation...")
    
    try:
        # Create sample task results
        task_results = [
            TaskResult("online_resume", 1, "online_resume/task_1", True, 45.5),
            TaskResult("online_resume", 2, "online_resume/task_2", False, 30.0, "Error"),
            TaskResult("habit_tracker", 1, "habit_tracker/task_1", True, 60.0),
            TaskResult("habit_tracker", 2, "habit_tracker/task_2", True, 55.0),
        ]
        
        # Create evaluation report
        start_time = datetime.now()
        end_time = datetime.now()
        
        report = EvaluationReport(
            model_name="gpt-4o",
            model_config={"base_url": "https://api.openai.com/v1", "temperature": 0.1},
            start_time=start_time,
            end_time=end_time,
            total_tasks=4,
            successful_tasks=3,
            failed_tasks=1,
            task_results=task_results
        )
        
        print("✅ EvaluationReport created successfully")
        print(f"📄 Model: {report.model_name}")
        print(f"📄 Success rate: {report.success_rate:.1f}%")
        print(f"📄 Execution time: {report.execution_time}")
        
        # Test category stats
        category_stats = report.get_category_stats()
        print(f"📄 Categories: {list(category_stats.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating EvaluationReport: {e}")
        return False

def test_json_reporting():
    """Test JSON report generation."""
    print("\n🔍 Testing JSON report generation...")
    
    try:
        reporter = ResultsReporter()
        
        # Create test data
        task_results = [
            TaskResult("test", 1, "test/task_1", True, 30.0),
            TaskResult("test", 2, "test/task_2", False, 25.0, "Error"),
        ]
        
        start_time = datetime.now()
        end_time = datetime.now()
        
        report = EvaluationReport(
            model_name="test-model",
            model_config={},
            start_time=start_time,
            end_time=end_time,
            total_tasks=2,
            successful_tasks=1,
            failed_tasks=1,
            task_results=task_results
        )
        
        # Create temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output_dir = Path(temp_dir)
            reporter_with_temp_dir = ResultsReporter(temp_output_dir)
            
            json_path = reporter_with_temp_dir.save_json_report(report, "test_report.json")
            print("✅ JSON report saved successfully")
            
            # Verify the file exists and is valid JSON
            if json_path.exists():
                with open(json_path) as f:
                    data = json.load(f)
                print("✅ JSON report is valid JSON")
                print(f"📄 Report contains {len(data.get('task_results', []))} task results")
                
                # Check required fields - updated to match actual implementation
                required_fields = ['model_name', 'start_time', 'summary', 'task_results']
                for field in required_fields:
                    if field in data:
                        print(f"✅ Required field '{field}' present")
                    else:
                        print(f"❌ Missing required field '{field}'")
                        return False
            else:
                print("❌ JSON report file not created")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing JSON reporting: {e}")
        return False

def test_csv_reporting():
    """Test CSV report generation."""
    print("\n🔍 Testing CSV report generation...")
    
    try:
        reporter = ResultsReporter()
        
        # Create test data
        task_results = [
            TaskResult("online_resume", 1, "online_resume/task_1", True, 30.0),
            TaskResult("online_resume", 2, "online_resume/task_2", False, 25.0, "Skill not found"),
            TaskResult("habit_tracker", 1, "habit_tracker/task_1", True, 40.0),
        ]
        
        start_time = datetime.now()
        end_time = datetime.now()
        
        report = EvaluationReport(
            model_name="test-model",
            model_config={},
            start_time=start_time,
            end_time=end_time,
            total_tasks=3,
            successful_tasks=2,
            failed_tasks=1,
            task_results=task_results
        )
        
        # Create temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output_dir = Path(temp_dir)
            reporter_with_temp_dir = ResultsReporter(temp_output_dir)
            
            results_path = reporter_with_temp_dir.save_csv_report(report, "test_results.csv")
            summary_path = reporter_with_temp_dir.save_summary_csv(report, "test_summary.csv")
            print("✅ CSV reports saved successfully")
            
            # Verify files exist
            if results_path.exists() and summary_path.exists():
                print("✅ Both CSV files created")
                
                # Read and check content
                with open(results_path) as f:
                    results_content = f.read()
                    if "online_resume/task_1" in results_content:
                        print("✅ Results CSV contains task data")
                    else:
                        print("❌ Results CSV missing task data")
                        return False
                
                with open(summary_path) as f:
                    summary_content = f.read()
                    if "online_resume" in summary_content:
                        print("✅ Summary CSV contains category data")
                    else:
                        print("❌ Summary CSV missing category data")
                        return False
            else:
                print("❌ CSV files not created")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing CSV reporting: {e}")
        return False

def test_results_reporter_initialization():
    """Test ResultsReporter initialization."""
    print("\n🔍 Testing ResultsReporter initialization...")
    
    try:
        reporter = ResultsReporter()
        print("✅ ResultsReporter initialized successfully")
        
        # Test that it has expected methods
        expected_methods = ['save_json_report', 'save_csv_report', 'save_summary_csv']
        for method in expected_methods:
            if hasattr(reporter, method):
                print(f"✅ Method '{method}' available")
            else:
                print(f"❌ Method '{method}' missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing ResultsReporter: {e}")
        return False

if __name__ == "__main__":
    print("=== Results Reporting Tests ===\n")
    
    success1 = test_results_reporter_initialization()
    success2 = test_task_result_creation()
    success3 = test_evaluation_report_creation()
    success4 = test_json_reporting()
    success5 = test_csv_reporting()
    
    if success1 and success2 and success3 and success4 and success5:
        print("\n🎉 Results reporting tests passed!")
    else:
        print("\n❌ Some results reporting tests failed!")
        sys.exit(1)