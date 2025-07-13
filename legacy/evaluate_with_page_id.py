import argparse
import subprocess
import sys
import os

def main():
    """
    Runs a verification script for a given scenario and task, and prints 1 for success or 0 for failure.
    Supports passing an optional page_id to the verification script.
    """
    parser = argparse.ArgumentParser(description="Run a verification script for a given scenario and task.")
    parser.add_argument("scenario", help="The name of the scenario (e.g., 'online_resume').")
    parser.add_argument("task_id", type=int, help="The ID of the task (e.g., 1).")
    parser.add_argument("--page-id", help="Optional page ID to use for verification")
    args = parser.parse_args()

    scenario = args.scenario
    task_id = args.task_id
    page_id = args.page_id

    script_path = os.path.join("tasks", scenario, f"task_{task_id}", "verify.py")

    if not os.path.exists(script_path):
        print(f"Error: Verification script not found at {script_path}", file=sys.stderr)
        print(0)
        sys.exit(1)

    project_root = os.path.abspath(os.path.dirname(__file__))
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    
    # Pass page_id through environment variable if provided
    if page_id:
        env["MCPBENCH_PAGE_ID"] = page_id
        print(f"Using page ID for verification: {page_id}", file=sys.stderr)

    try:
        # Use sys.executable to ensure the same Python interpreter is used.
        # The `check=True` will raise CalledProcessError for non-zero exit codes.
        subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=True,
            text=True,
            env=env
        )
        print(1)
    except subprocess.CalledProcessError as e:
        # The script returned a non-zero exit code, indicating failure.
        print(f"Verification failed for scenario '{scenario}' task {task_id}.", file=sys.stderr)
        print(f"--- stdout ---\n{e.stdout}", file=sys.stderr)
        print(f"--- stderr ---\n{e.stderr}", file=sys.stderr)
        print(0)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        print(0)

if __name__ == "__main__":
    main()