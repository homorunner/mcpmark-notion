#!/usr/bin/env python3
"""
MCPBench - Main Entry Point
===========================

Central entry point for MCPBench evaluation framework.

Usage:
    python mcpbench.py pipeline [options]    # Run evaluation pipeline
    python mcpbench.py evaluate [options]    # Run single task evaluation
    python mcpbench.py --help                # Show help

Examples:
    # Run full evaluation pipeline
    python mcpbench.py pipeline --model-name gpt-4 --tasks all
    
    # Run with page duplication
    python mcpbench.py pipeline --model-name claude-3 --tasks online_resume --duplicate-pages
    
    # Evaluate single task
    python mcpbench.py evaluate online_resume 1 --page-id abc123
"""

import sys
import argparse
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))


def main():
    """Main entry point with subcommand routing."""
    parser = argparse.ArgumentParser(
        description="MCPBench - AI Model Evaluation Framework for Notion API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Commands:
  pipeline    Run the evaluation pipeline on multiple tasks
  evaluate    Run evaluation for a single task
  
Examples:
  python mcpbench.py pipeline --model-name gpt-4 --tasks all
  python mcpbench.py evaluate online_resume 1 --page-id abc123
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Pipeline subcommand
    pipeline_parser = subparsers.add_parser(
        'pipeline', 
        help='Run evaluation pipeline',
        description='Run the evaluation pipeline on multiple tasks'
    )
    pipeline_parser.add_argument('--model-name', required=True, help='Name of the model to evaluate')
    pipeline_parser.add_argument('--api-key', help='API key for the model provider')
    pipeline_parser.add_argument('--base-url', help='Base URL for the model provider')
    pipeline_parser.add_argument('--notion-key', help='Notion API key')
    pipeline_parser.add_argument('--tasks', default='all', help='Tasks to run: "all", category name, or "category/task_name"')
    pipeline_parser.add_argument('--duplicate-pages', action='store_true', help='Enable page duplication for consistent evaluation')
    pipeline_parser.add_argument('--source-pages', help='JSON string mapping task categories to source page URLs')
    pipeline_parser.add_argument('--max-workers', type=int, default=3, help='Maximum number of concurrent workers')
    pipeline_parser.add_argument('--timeout', type=int, default=300, help='Timeout in seconds for each task')
    pipeline_parser.add_argument('--config', type=Path, help='Path to configuration file')
    pipeline_parser.add_argument('--output-dir', type=Path, default=Path('data/results'), help='Directory to save results')
    pipeline_parser.add_argument('--no-json', action='store_true', help='Skip JSON report generation')
    pipeline_parser.add_argument('--no-csv', action='store_true', help='Skip CSV report generation')
    
    # Evaluate subcommand  
    evaluate_parser = subparsers.add_parser(
        'evaluate',
        help='Run single task evaluation',
        description='Run evaluation for a single task'
    )
    evaluate_parser.add_argument('scenario', help='The name of the scenario (e.g., "online_resume")')
    evaluate_parser.add_argument('task_id', type=int, help='The ID of the task (e.g., 1)')
    evaluate_parser.add_argument('--page-id', help='Optional page ID to use for verification')
    evaluate_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Route to appropriate subcommand
    if args.command == 'pipeline':
        from src.evaluation.pipeline import main as pipeline_main
        # Convert argparse Namespace to sys.argv format for the pipeline script
        sys.argv = ['pipeline.py']
        for arg_name, arg_value in vars(args).items():
            if arg_name == 'command':
                continue
            if arg_value is True:  # Boolean flags
                sys.argv.append(f'--{arg_name.replace("_", "-")}')
            elif arg_value is not None and arg_value is not False:
                sys.argv.extend([f'--{arg_name.replace("_", "-")}', str(arg_value)])
        pipeline_main()
        
    elif args.command == 'evaluate':
        from src.evaluation.evaluate import main as evaluate_main
        # Convert argparse Namespace to sys.argv format for the evaluate script
        sys.argv = ['evaluate.py', args.scenario, str(args.task_id)]
        if args.page_id:
            sys.argv.extend(['--page-id', args.page_id])
        if args.verbose:
            sys.argv.append('--verbose')
        evaluate_main()


if __name__ == "__main__":
    main()