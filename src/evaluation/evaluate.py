#!/usr/bin/env python3
"""
MCPBench Task Evaluator
=======================

Runs verification scripts for individual tasks with optional page ID support.

Usage:
    python evaluate.py scenario task_id
    python evaluate.py scenario task_id --page-id PAGE_ID
    
Examples:
    python evaluate.py online_resume 1
    python evaluate.py online_resume 1 --page-id abc123
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def main():
    """
    Runs a verification script for a given scenario and task, and prints 1 for success or 0 for failure.
    Supports passing an optional page_id to the verification script.
    """
    parser = argparse.ArgumentParser(
        description="Run a verification script for a given scenario and task.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python evaluate.py online_resume 1
  python evaluate.py online_resume 1 --page-id abc123
  python evaluate.py habit_tracker 2 --page-id def456
        """
    )
    
    parser.add_argument("scenario", help="The name of the scenario (e.g., 'online_resume').")
    parser.add_argument("task_id", type=int, help="The ID of the task (e.g., 1).")
    parser.add_argument("--page-id", help="Optional page ID to use for verification")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()

    scenario = args.scenario
    task_id = args.task_id
    page_id = args.page_id

    # Find the script path - handle both old and new directory structures
    script_paths = [
        Path("tasks") / scenario / f"task_{task_id}" / "verify.py",  # New structure
        Path("../tasks") / scenario / f"task_{task_id}" / "verify.py",  # From src/evaluation
        Path("../../tasks") / scenario / f"task_{task_id}" / "verify.py",  # Deeper nesting
    ]
    
    script_path = None
    for path in script_paths:
        if path.exists():
            script_path = path
            break
    
    if not script_path:
        print(f"Error: Verification script not found. Tried paths:", file=sys.stderr)
        for path in script_paths:
            print(f"  {path.absolute()}", file=sys.stderr)
        print(0)
        sys.exit(1)

    if args.verbose:
        print(f"Using verification script: {script_path.absolute()}", file=sys.stderr)

    # Set up environment
    project_root = os.path.abspath(os.path.dirname(__file__))
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    
    # Pass page_id through environment variable if provided
    if page_id:
        env["MCPBENCH_PAGE_ID"] = page_id
        if args.verbose:
            print(f"Using page ID for verification: {page_id}", file=sys.stderr)

    try:
        # Build command - support both with and without page ID as argument
        cmd = [sys.executable, str(script_path)]
        if page_id:
            # Try passing page_id as command line argument first
            cmd.append(page_id)
        
        if args.verbose:
            print(f"Running command: {' '.join(cmd)}", file=sys.stderr)
        
        # Use sys.executable to ensure the same Python interpreter is used.
        # The `check=True` will raise CalledProcessError for non-zero exit codes.
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=env
        )
        
        if args.verbose and result.stdout:
            print(f"Script output: {result.stdout}", file=sys.stderr)
        
        print(1)
        
    except subprocess.CalledProcessError as e:
        # The script returned a non-zero exit code, indicating failure.
        print(f"Verification failed for scenario '{scenario}' task {task_id}.", file=sys.stderr)
        
        if args.verbose or e.stdout or e.stderr:
            if e.stdout:
                print(f"--- stdout ---\n{e.stdout}", file=sys.stderr)
            if e.stderr:
                print(f"--- stderr ---\n{e.stderr}", file=sys.stderr)
        
        print(0)
        
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        print(0)


if __name__ == "__main__":
    main()