#!/usr/bin/env python3
"""
MCPBench Pipeline Demonstration
===============================

A demonstration script showing how to use the MCPBench evaluation pipeline.
This script tests basic functionality and provides usage examples.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.task_manager import TaskManager
from core.results_reporter import ResultsReporter, TaskResult, EvaluationReport
from core.task_template_manager import TaskTemplateManager
from datetime import datetime

def demonstrate_task_discovery():
    """Demonstrate task discovery capabilities."""
    print("🎯 DEMO: Task Discovery")
    print("-" * 40)
    
    tasks_root = Path(__file__).parent.parent / "tasks"
    task_manager = TaskManager(tasks_root)
    
    # Show all available tasks
    all_tasks = task_manager.filter_tasks("all")
    summary = task_manager.get_task_summary()
    
    print(f"📋 Total tasks available: {len(all_tasks)}")
    print("📊 Tasks by category:")
    for category, count in summary.items():
        print(f"   {category}: {count} tasks")
    
    # Show a specific task
    online_resume_tasks = task_manager.filter_tasks("online_resume")
    if online_resume_tasks:
        task = online_resume_tasks[0]
        description = task.get_description()
        print(f"\n📄 Sample task: {task.name}")
        print(f"📄 Description preview: {description[:100]}...")
    
    print("✅ Task discovery demonstration complete\n")

def demonstrate_template_management():
    """Demonstrate template management capabilities."""
    print("🎯 DEMO: Template Management")
    print("-" * 40)
    
    template_manager = TaskTemplateManager()
    
    # Sample task description
    original_description = '''Find page named "Maya Zhang", then in "Skills" section, perform task：
1. Add skill "Python" 
2. Set type as "Programming Language"
3. Set proficiency to 90%'''
    
    print("📄 Original description:")
    print(original_description)
    
    # Convert to use page ID
    page_id = "12345678-1234-5678-1234-567812345678"
    modified_description = template_manager.convert_legacy_description(
        original_description, page_id
    )
    
    print("\n📄 Modified description:")
    print(modified_description)
    
    # Extract page name
    page_name = template_manager.extract_page_name_from_description(original_description)
    print(f"\n📄 Extracted page name: {page_name}")
    
    print("✅ Template management demonstration complete\n")

def demonstrate_results_reporting():
    """Demonstrate results reporting capabilities."""
    print("🎯 DEMO: Results Reporting")
    print("-" * 40)
    
    # Create sample evaluation results
    task_results = [
        TaskResult("online_resume", 1, "online_resume/task_1", True, 45.2),
        TaskResult("online_resume", 2, "online_resume/task_2", True, 38.7),
        TaskResult("online_resume", 3, "online_resume/task_3", False, 42.1, "Skill not found"),
        TaskResult("habit_tracker", 1, "habit_tracker/task_1", True, 52.3),
        TaskResult("habit_tracker", 2, "habit_tracker/task_2", True, 48.9),
    ]
    
    start_time = datetime.now()
    end_time = datetime.now()
    
    report = EvaluationReport(
        model_name="gpt-4o-demo",
        model_config={"base_url": "https://api.openai.com/v1", "temperature": 0.1},
        start_time=start_time,
        end_time=end_time,
        total_tasks=5,
        successful_tasks=4,
        failed_tasks=1,
        task_results=task_results
    )
    
    print(f"📊 Demo Evaluation Results:")
    print(f"   Model: {report.model_name}")
    print(f"   Success Rate: {report.success_rate:.1f}%")
    print(f"   Total Tasks: {report.total_tasks}")
    print(f"   Successful: {report.successful_tasks}")
    print(f"   Failed: {report.failed_tasks}")
    
    # Show category breakdown
    category_stats = report.get_category_stats()
    print(f"\n📊 Results by Category:")
    for category, stats in category_stats.items():
        print(f"   {category}: {stats['successful']}/{stats['total']} "
              f"({stats['success_rate']:.1f}%)")
    
    # Save reports to temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        reporter = ResultsReporter(Path(temp_dir))
        
        json_path = reporter.save_json_report(report, "demo_report.json")
        csv_path = reporter.save_csv_report(report, "demo_results.csv")
        summary_path = reporter.save_summary_csv(report, "demo_summary.csv")
        
        print(f"\n📄 Reports saved to temporary directory:")
        print(f"   JSON: {json_path.name}")
        print(f"   CSV Results: {csv_path.name}")
        print(f"   CSV Summary: {summary_path.name}")
    
    print("✅ Results reporting demonstration complete\n")

def demonstrate_pipeline_usage():
    """Demonstrate how to use the evaluation pipeline."""
    print("🎯 DEMO: Pipeline Usage Examples")
    print("-" * 40)
    
    print("📋 Command Examples:")
    print()
    
    print("1️⃣  Run all tasks (basic mode):")
    print("   python src/evaluation/pipeline.py \\")
    print("     --model-name gpt-4o \\")
    print("     --api-key $MCPBENCH_API_KEY \\")
    print("     --base-url $MCPBENCH_BASE_URL \\")
    print("     --notion-key $NOTION_API_KEY \\")
    print("     --tasks all")
    print()
    
    print("2️⃣  Run specific category:")
    print("   python src/evaluation/pipeline.py \\")
    print("     --model-name gpt-4o \\")
    print("     --api-key $MCPBENCH_API_KEY \\")
    print("     --base-url $MCPBENCH_BASE_URL \\")
    print("     --notion-key $NOTION_API_KEY \\")
    print("     --tasks online_resume")
    print()
    
    print("3️⃣  Run with page duplication:")
    print("   python src/evaluation/pipeline.py \\")
    print("     --model-name gpt-4o \\")
    print("     --api-key $MCPBENCH_API_KEY \\")
    print("     --base-url $MCPBENCH_BASE_URL \\")
    print("     --notion-key $NOTION_API_KEY \\")
    print("     --tasks online_resume \\")
    print("     --duplicate-pages \\")
    print('     --source-pages \'{"online_resume": "https://notion.so/page-url"}\'')
    print()
    
    print("4️⃣  Verify individual task:")
    print("   python src/evaluation/evaluate.py \\")
    print("     online_resume 1 \\")
    print("     --page-id abc123...")
    print()
    
    print("✅ Pipeline usage demonstration complete\n")

def check_environment():
    """Check environment setup."""
    print("🎯 DEMO: Environment Check")
    print("-" * 40)
    
    required_vars = [
        'NOTION_API_KEY',
        'MCPBENCH_API_KEY', 
        'MCPBENCH_BASE_URL',
        'MCPBENCH_MODEL_NAME'
    ]
    
    print("🔍 Environment Variables:")
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Show first 10 characters for security
            display_value = value[:10] + "..." if len(value) > 10 else value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: NOT SET")
            all_set = False
    
    if all_set:
        print("\n✅ All environment variables are configured!")
        print("🚀 Ready to run evaluations!")
    else:
        print("\n⚠️  Some environment variables are missing.")
        print("💡 Please set them in your .env file or environment.")
    
    print("✅ Environment check complete\n")

def main():
    """Run all demonstrations."""
    print("=" * 60)
    print("MCPBench Evaluation Pipeline - DEMONSTRATION")
    print("=" * 60)
    print()
    
    check_environment()
    demonstrate_task_discovery()
    demonstrate_template_management()
    demonstrate_results_reporting()
    demonstrate_pipeline_usage()
    
    print("=" * 60)
    print("🎉 DEMONSTRATION COMPLETE!")
    print("✅ MCPBench evaluation pipeline is ready for use.")
    print("📚 See tests/README.md for more information.")
    print("=" * 60)

if __name__ == "__main__":
    main()