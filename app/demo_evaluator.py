"""
Simplified Evaluator for Demo
=============================

This module provides a minimal evaluator that orchestrates the execution
and verification of tasks without state management complexity.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import time

from demo_agent import DemoAgent
from demo_task_manager import DemoTaskManager, DemoTask


@dataclass
class EvaluationResult:
    """Result of a task evaluation."""
    task_name: str
    execution_success: bool
    verification_success: bool
    execution_time: float
    execution_error: Optional[str] = None
    verification_output: Optional[str] = None
    agent_messages: Optional[list] = None
    execution_logs: Optional[list] = None


class DemoEvaluator:
    """Simplified evaluator for demonstration."""
    
    def __init__(self, notion_key: str, model_name: str = "gpt-4o", 
                 api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize the evaluator.
        
        Args:
            notion_key: Notion API key for the agent
            model_name: Name of the model to use
            api_key: Optional API key (uses env var if not provided)
            base_url: Optional base URL (uses env var or default if not provided)
        """
        self.notion_key = notion_key
        self.model_name = model_name
        
        # Initialize components
        self.task_manager = DemoTaskManager()
        self.agent = DemoAgent(model_name, notion_key, api_key, base_url)
    
    def stop(self):
        """Stop the current evaluation."""
        self.agent.stop()
    
    def reset(self):
        """Reset the evaluator for a new evaluation."""
        self.agent.reset()
    
    def evaluate_task(self, task_name: str, page_id: str, callback=None) -> EvaluationResult:
        """Evaluate a single task.
        
        Args:
            task_name: Full task name (e.g., 'habit_tracker/task_1')
            page_id: Notion page ID to operate on
            callback: Optional callback for real-time updates
            
        Returns:
            EvaluationResult with execution and verification results
        """
        start_time = time.time()
        
        # Get the task
        task = self.task_manager.get_task_by_name(task_name)
        if not task:
            return EvaluationResult(
                task_name=task_name,
                execution_success=False,
                verification_success=False,
                execution_time=0,
                execution_error="Task not found"
            )
        
        # Get task instruction
        instruction = task.get_description()
        
        # Add page context to instruction
        full_instruction = f"You are working with Notion page ID: {page_id}\n\n{instruction}"
        
        # Execute the task with agent
        print(f"Executing task: {task_name}")
        agent_result = self.agent.execute_sync(full_instruction, callback)
        
        execution_success = agent_result["success"]
        execution_error = agent_result.get("error")
        agent_messages = agent_result.get("messages", [])
        execution_logs = agent_result.get("execution_logs", [])
        
        # If execution failed, return early
        if not execution_success:
            execution_time = time.time() - start_time
            return EvaluationResult(
                task_name=task_name,
                execution_success=False,
                verification_success=False,
                execution_time=execution_time,
                execution_error=execution_error,
                agent_messages=agent_messages,
                execution_logs=execution_logs
            )
        
        # Run verification
        print(f"\n\nVerifying task result...")
        verification_success, verification_output = self.task_manager.run_verification(task, page_id, self.notion_key)
        
        execution_time = time.time() - start_time
        
        return EvaluationResult(
            task_name=task_name,
            execution_success=execution_success,
            verification_success=verification_success,
            execution_time=execution_time,
            execution_error=execution_error,
            verification_output=verification_output,
            agent_messages=agent_messages,
            execution_logs=execution_logs
        )
    
    def format_result(self, result: EvaluationResult) -> str:
        """Format evaluation result for display."""
        lines = [
            f"Task: {result.task_name}",
            f"Execution Time: {result.execution_time:.2f}s",
            f"Execution: {'✓ Success' if result.execution_success else '✗ Failed'}",
            f"Verification: {'✓ Passed' if result.verification_success else '✗ Failed'}",
        ]
        
        if result.execution_error:
            lines.append(f"\nExecution Error: {result.execution_error}")
        
        if result.verification_output:
            lines.append(f"\nVerification Output:\n{result.verification_output}")
        
        return "\n".join(lines)