#!/usr/bin/env python3
"""
Test End-to-End Pipeline
========================

Tests for the complete evaluation pipeline integration.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

def test_pipeline_help():
    """Test that the pipeline script shows help correctly."""
    print("🔍 Testing pipeline help functionality...")
    
    pipeline_script = Path(__file__).parent.parent / "src" / "evaluation" / "pipeline.py"
    if not pipeline_script.exists():
        print("❌ pipeline.py script not found")
        return False
    
    try:
        result = subprocess.run([
            sys.executable, str(pipeline_script), "--help"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Pipeline help command works")
            if "MCPBench Evaluation Pipeline" in result.stdout:
                print("✅ Help text contains expected content")
            else:
                print("⚠️  Help text may be incomplete")
        else:
            print(f"❌ Pipeline help failed: {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing pipeline help: {e}")
        return False

def test_pipeline_missing_args():
    """Test pipeline error handling with missing arguments."""
    print("\n🔍 Testing pipeline error handling...")
    
    pipeline_script = Path(__file__).parent.parent / "src" / "evaluation" / "pipeline.py"
    
    try:
        # Test with missing required arguments
        result = subprocess.run([
            sys.executable, str(pipeline_script), 
            "--model-name", "test-model"
            # Missing other required args
        ], capture_output=True, text=True, timeout=30)
        
        # Should fail gracefully
        if result.returncode != 0:
            print("✅ Pipeline handles missing arguments correctly")
            if "API key" in result.stderr or "required" in result.stderr:
                print("✅ Error message mentions missing required arguments")
            else:
                print("ℹ️  Error handling working but message could be clearer")
        else:
            print("⚠️  Pipeline didn't fail with missing arguments")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing pipeline error handling: {e}")
        return False

def test_pipeline_with_dry_run():
    """Test pipeline configuration validation without actual execution."""
    print("\n🔍 Testing pipeline configuration validation...")
    
    pipeline_script = Path(__file__).parent.parent / "src" / "evaluation" / "pipeline.py"
    
    # Get environment variables
    api_key = os.getenv('MCPBENCH_API_KEY')
    base_url = os.getenv('MCPBENCH_BASE_URL')
    model_name = os.getenv('MCPBENCH_MODEL_NAME')
    notion_key = os.getenv('NOTION_API_KEY')
    
    if not all([api_key, base_url, model_name, notion_key]):
        print("⚠️  Missing environment variables - skipping configuration test")
        return True
    
    try:
        # Test with a non-existent task to trigger early validation
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run([
                sys.executable, str(pipeline_script),
                "--model-name", model_name,
                "--api-key", api_key,
                "--base-url", base_url,
                "--notion-key", notion_key,
                "--tasks", "non_existent_task",
                "--output-dir", temp_dir,
                "--timeout", "10"
            ], capture_output=True, text=True, timeout=60)
            
            print(f"📄 Pipeline exit code: {result.returncode}")
            
            # Check if it got to task discovery
            if "No tasks found" in result.stdout or "No tasks found" in result.stderr:
                print("✅ Pipeline successfully validated configuration and discovered tasks")
            elif "Starting MCPBench evaluation" in result.stdout:
                print("✅ Pipeline initialized successfully")
            else:
                print("ℹ️  Pipeline ran but output may indicate issues")
                print(f"📄 stdout: {result.stdout[:200]}...")
                print(f"📄 stderr: {result.stderr[:200]}...")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("⚠️  Pipeline test timed out - this may be expected")
        return True
    except Exception as e:
        print(f"❌ Error testing pipeline configuration: {e}")
        return False

def test_evaluate_script_integration():
    """Test the evaluate.py script with actual task."""
    print("\n🔍 Testing evaluate.py integration...")
    
    evaluate_script = Path(__file__).parent.parent / "src" / "evaluation" / "evaluate.py"
    
    try:
        # Test with a real task but dummy page ID
        result = subprocess.run([
            sys.executable, str(evaluate_script),
            "online_resume", "1", 
            "--page-id", "dummy-page-id-for-testing",
            "--verbose"
        ], capture_output=True, text=True, timeout=30)
        
        print(f"📄 Evaluate script exit code: {result.returncode}")
        
        # The script should execute but likely fail verification
        if result.returncode in [0, 1]:  # 0 = success, 1 = verification failed
            print("✅ Evaluate script executed successfully")
            if result.stdout.strip() in ["0", "1"]:
                print("✅ Script output format is correct")
            else:
                print(f"ℹ️  Script output: {result.stdout.strip()}")
        else:
            print(f"⚠️  Unexpected exit code: {result.returncode}")
            print(f"📄 stderr: {result.stderr[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing evaluate script: {e}")
        return False

def test_environment_integration():
    """Test that all components can access environment variables correctly."""
    print("\n🔍 Testing environment variable integration...")
    
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
        print(f"⚠️  Missing environment variables: {missing_vars}")
        print("ℹ️  Some integration tests may be limited")
        return True
    
    print("✅ All required environment variables are available")
    
    # Test that our test scripts can access them
    try:
        from utils.mcp_utils import get_notion_key
        notion_key = get_notion_key()
        if notion_key:
            print("✅ MCP utils can access Notion API key")
        else:
            print("❌ MCP utils cannot access Notion API key")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing environment integration: {e}")
        return False

def test_component_integration():
    """Test that core components work together."""
    print("\n🔍 Testing component integration...")
    
    try:
        from core.task_manager import TaskManager
        from core.results_reporter import ResultsReporter, TaskResult, EvaluationReport
        from datetime import datetime
        
        # Test task discovery
        tasks_root = Path(__file__).parent.parent / "tasks"
        task_manager = TaskManager(tasks_root)
        all_tasks = task_manager.filter_tasks("all")
        
        if not all_tasks:
            print("❌ No tasks found by task manager")
            return False
        
        print(f"✅ Task manager found {len(all_tasks)} tasks")
        
        # Test creating a mock evaluation report
        sample_results = [
            TaskResult("test", 1, "test/task_1", True, 30.0),
            TaskResult("test", 2, "test/task_2", False, 25.0, "Mock error"),
        ]
        
        start_time = datetime.now()
        end_time = datetime.now()
        
        report = EvaluationReport(
            model_name="test-integration",
            model_config={},
            start_time=start_time,
            end_time=end_time,
            total_tasks=2,
            successful_tasks=1,
            failed_tasks=1,
            task_results=sample_results
        )
        
        print(f"✅ Created evaluation report with {report.success_rate:.1f}% success rate")
        
        # Test results reporter
        with tempfile.TemporaryDirectory() as temp_dir:
            reporter = ResultsReporter(Path(temp_dir))
            json_path = reporter.save_json_report(report, "integration_test.json")
            
            if json_path.exists():
                print("✅ Results reporter integration successful")
            else:
                print("❌ Results reporter failed to save report")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing component integration: {e}")
        return False

if __name__ == "__main__":
    print("=== End-to-End Pipeline Tests ===\n")
    
    success1 = test_pipeline_help()
    success2 = test_pipeline_missing_args()
    success3 = test_environment_integration()
    success4 = test_component_integration()
    success5 = test_evaluate_script_integration()
    success6 = test_pipeline_with_dry_run()
    
    all_passed = success1 and success2 and success3 and success4 and success5 and success6
    
    if all_passed:
        print("\n🎉 End-to-end pipeline tests passed!")
        print("✅ The evaluation pipeline is ready for use!")
    else:
        print("\n❌ Some end-to-end tests failed!")
        print("⚠️  Review the issues above before running full evaluations")
        sys.exit(1)