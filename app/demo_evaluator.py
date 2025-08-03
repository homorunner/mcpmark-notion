"""
Simplified Evaluator for Demo
=============================

This module provides a minimal evaluator that orchestrates the execution
and verification of tasks without state management complexity.
"""

from typing import Optional
from dataclasses import dataclass
import time

from demo_agent import DemoAgent
from demo_task_manager import DemoTaskManager


@dataclass
class ExecutionResult:
    """Result of a task execution (without verification)."""
    task_name: str
    execution_success: bool
    execution_time: float
    execution_error: Optional[str] = None
    agent_messages: Optional[list] = None
    execution_logs: Optional[list] = None


@dataclass
class VerificationResult:
    """Result of a task verification."""
    task_name: str
    verification_success: bool
    verification_output: Optional[str] = None


@dataclass
class EvaluationResult:
    """Result of a complete task evaluation (execution + verification)."""
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
    
    def execute_task(self, task_name: str, page_id: str, callback=None) -> ExecutionResult:
        """Execute a single task (without verification).
        
        Args:
            task_name: Full task name (e.g., 'habit_tracker/task_1')
            page_id: Notion page ID to operate on
            callback: Optional callback for real-time updates
            
        Returns:
            ExecutionResult with execution results only
        """
        start_time = time.time()
        
        # Get the task
        task = self.task_manager.get_task_by_name(task_name)
        if not task:
            return ExecutionResult(
                task_name=task_name,
                execution_success=False,
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
        
        execution_time = time.time() - start_time
        
        return ExecutionResult(
            task_name=task_name,
            execution_success=execution_success,
            execution_time=execution_time,
            execution_error=execution_error,
            agent_messages=agent_messages,
            execution_logs=execution_logs
        )
    
    def verify_task(self, task_name: str, page_id: str) -> VerificationResult:
        """Verify a previously executed task.
        
        Args:
            task_name: Full task name (e.g., 'habit_tracker/task_1')
            page_id: Notion page ID to verify
            
        Returns:
            VerificationResult with verification results only
        """
        # Get the task
        task = self.task_manager.get_task_by_name(task_name)
        if not task:
            return VerificationResult(
                task_name=task_name,
                verification_success=False,
                verification_output="Task not found"
            )
        
        # Run verification
        print(f"\n\nVerifying task result...")
        verification_success, verification_output = self.task_manager.run_verification(task, page_id, self.notion_key)
        
        return VerificationResult(
            task_name=task_name,
            verification_success=verification_success,
            verification_output=verification_output
        )

    def evaluate_task(self, task_name: str, page_id: str, callback=None) -> EvaluationResult:
        """Evaluate a single task (execute + verify).
        
        Args:
            task_name: Full task name (e.g., 'habit_tracker/task_1')
            page_id: Notion page ID to operate on
            callback: Optional callback for real-time updates
            
        Returns:
            EvaluationResult with execution and verification results
        """
        # Execute the task
        execution_result = self.execute_task(task_name, page_id, callback)
        
        # If execution failed, return early without verification
        if not execution_result.execution_success:
            return EvaluationResult(
                task_name=execution_result.task_name,
                execution_success=False,
                verification_success=False,
                execution_time=execution_result.execution_time,
                execution_error=execution_result.execution_error,
                agent_messages=execution_result.agent_messages,
                execution_logs=execution_result.execution_logs
            )
        
        # Run verification
        verification_result = self.verify_task(task_name, page_id)
        
        return EvaluationResult(
            task_name=execution_result.task_name,
            execution_success=execution_result.execution_success,
            verification_success=verification_result.verification_success,
            execution_time=execution_result.execution_time,
            execution_error=execution_result.execution_error,
            verification_output=verification_result.verification_output,
            agent_messages=execution_result.agent_messages,
            execution_logs=execution_result.execution_logs
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