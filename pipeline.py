#!/usr/bin/env python3
"""
MCPBench Unified Evaluation Pipeline
===================================

This script provides an automated evaluation pipeline for testing Large Language Models (LLMs)
on various Multi-Step Cognitive Processes (MCP) services like Notion, GitHub, and PostgreSQL.
"""
import argparse
from pathlib import Path
from dotenv import load_dotenv

from src.logger import get_logger
from src.evaluator import MCPEvaluator
from src.factory import MCPServiceFactory
from src.model_config import ModelConfig


# Initialize logger
logger = get_logger(__name__)


def main():
    """Main entry point for the evaluation pipeline."""
    parser = argparse.ArgumentParser(
        description="MCPBench Unified Evaluation Pipeline."
    )

    supported_services = MCPServiceFactory.get_supported_services()
    supported_models = ModelConfig.get_supported_models()

    # Main configuration
    parser.add_argument(
        "--service",
        default="notion",
        choices=supported_services,
        help="MCP service to use (default: notion)",
    )
    parser.add_argument(
        "--model",
        required=True,
        choices=supported_models,
        help="Name of the model to evaluate",
    )
    parser.add_argument(
        "--tasks",
        default="all",
        help='Tasks to run: "all", a category name, or "category/task_name"',
    )
    parser.add_argument(
        "--exp-name",
        required=True,
        help="Experiment name; results are saved under results/<exp-name>/",
    )

    # Execution configuration
    parser.add_argument(
        "--timeout", type=int, default=300, help="Timeout in seconds for each task"
    )

    # Playwright configuration
    parser.add_argument(
        "--browser",
        default="chromium",
        choices=["chromium", "firefox"],
        help="Playwright browser engine to use (default: firefox)",
    )

    # Output configuration
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./results"),
        help="Directory to save results",
    )
    
    # Load arguments and environment variables
    args = parser.parse_args()
    load_dotenv(dotenv_path=".mcp_env", override=True)

    # Initialize and run the evaluation pipeline
    pipeline = MCPEvaluator(
        service=args.service,
        model=args.model,
        timeout=args.timeout,
        browser=args.browser,
        exp_name=args.exp_name,
        output_dir=args.output_dir,
    )

    pipeline.run_evaluation(args.tasks)
    logger.info(f"✓ Evaluation completed. Results saved in: {pipeline.base_experiment_dir}")


if __name__ == "__main__":
    main()
