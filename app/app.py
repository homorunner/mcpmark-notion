"""
MCPBench Demo Application
========================

A minimal Streamlit application to demonstrate the evaluation process
for Notion tasks using LLM agents and MCP servers.
"""

import streamlit as st
import os
import sys
import threading
import time
import queue
from pathlib import Path

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent))

from demo_evaluator import DemoEvaluator, ExecutionResult, VerificationResult
from demo_task_manager import DemoTaskManager
from demo_model_config import DemoModelConfig


def run_execution_in_thread(evaluator, task_name, page_id, log_queue):
    """Run task execution in a separate thread."""
    try:
        def queue_callback(log_entry):
            """Thread-safe callback that uses queue instead of session_state"""
            log_queue.put(log_entry)
        
        result = evaluator.execute_task(task_name, page_id, callback=queue_callback)
        # Signal completion
        log_queue.put({"type": "execution_completion", "result": result})
    except Exception as e:
        # Signal error
        log_queue.put({"type": "error", "error": str(e)})


def run_verification_in_thread(evaluator, task_name, page_id, log_queue):
    """Run task verification in a separate thread."""
    try:
        result = evaluator.verify_task(task_name, page_id)
        # Signal completion
        log_queue.put({"type": "verification_completion", "result": result})
    except Exception as e:
        # Signal error
        log_queue.put({"type": "error", "error": str(e)})


def main():
    st.set_page_config(
        page_title="MCPBench Demo",
        page_icon="🔬",
        layout="wide"
    )
    
    # Initialize session state
    if 'is_executing' not in st.session_state:
        st.session_state.is_executing = False
    if 'is_verifying' not in st.session_state:
        st.session_state.is_verifying = False
    if 'evaluator' not in st.session_state:
        st.session_state.evaluator = None
    if 'execution_thread' not in st.session_state:
        st.session_state.execution_thread = None
    if 'verification_thread' not in st.session_state:
        st.session_state.verification_thread = None
    if 'logs_list' not in st.session_state:
        st.session_state.logs_list = []
    if 'current_response' not in st.session_state:
        st.session_state.current_response = None
    if 'execution_result' not in st.session_state:
        st.session_state.execution_result = None
    if 'verification_result' not in st.session_state:
        st.session_state.verification_result = None
    if 'log_queue' not in st.session_state:
        st.session_state.log_queue = queue.Queue()
    if 'selected_task_name' not in st.session_state:
        st.session_state.selected_task_name = None
    if 'selected_page_id' not in st.session_state:
        st.session_state.selected_page_id = None
    
    st.title("🔬 MCPBench Evaluation Demo")
    st.markdown("""
    This demo shows how MCPBench evaluates LLM agents on Notion tasks.
    Select a task, provide your Notion credentials, and watch the evaluation process.
    """)
    
    # Initialize task manager
    task_manager = DemoTaskManager()
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Model selection with provider grouping
        model_display_info = DemoModelConfig.get_display_info()
        
        # Group models by provider
        providers = {}
        for model_name, info in model_display_info.items():
            provider = info["provider"]
            if provider not in providers:
                providers[provider] = []
            providers[provider].append(model_name)
        
        # Create selection options with provider labels
        model_options = []
        for provider in sorted(providers.keys()):
            for model in sorted(providers[provider]):
                model_options.append(model)
        
        model_name = st.selectbox(
            "Select Model",
            options=model_options,
            format_func=lambda x: model_display_info[x]["display_name"],
            index=0
        )
        
        # Show required API key info
        model_info = model_display_info[model_name]
        st.info(f"This model requires: {model_info['api_key_var']}")
        
        # API Key (dynamic based on selected model)
        api_key_var = model_display_info[model_name]["api_key_var"]
        api_key = st.text_input(
            f"API Key ({api_key_var})",
            value=os.getenv(api_key_var, ""),
            type="password",
            help=f"Your API key for {model_name}. Can also be set via {api_key_var} environment variable."
        )
        
        # Notion API Key
        notion_key = st.text_input(
            "Notion API Key",
            type="password",
            help="Your Notion integration API key"
        )
        
        # Optional: Custom base URL
        with st.expander("Advanced Settings"):
            base_url = st.text_input(
                "API Base URL",
                value="https://api.openai.com/v1",
                help="Custom API endpoint (for proxy or alternative providers)"
            )
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Task Selection")
        
        # Get available tasks grouped by input (category) – one task per input, max 5 inputs
        all_tasks = task_manager.get_available_tasks()
        available_tasks = []
        seen_categories = set()
        for task in all_tasks:
            category = task["value"].split("/", 1)[0]
            if category not in seen_categories:
                seen_categories.add(category)
                available_tasks.append(task)
            if len(available_tasks) >= 5:
                break
        
        if not available_tasks:
            st.error("No tasks found. Please ensure the tasks directory exists.")
            return
        
        # Task dropdown
        selected_task = st.selectbox(
            "Select a Task",
            options=[task["value"] for task in available_tasks],
            format_func=lambda x: next(t["label"] for t in available_tasks if t["value"] == x)
        )
        
        # Show task description
        if selected_task:
            task = task_manager.get_task_by_name(selected_task)
            if task:
                st.subheader("Task Description")
                with st.expander("View task instructions", expanded=True):
                    st.markdown(task.get_description())
    
    with col2:
        # Display template URL if task is selected
        if selected_task:
            task = task_manager.get_task_by_name(selected_task)
            if task:
                template_url = task.get_template_url()
                gt_page_url = task.get_gt_page_url()
                if template_url:
                    st.header("Notion Input Page")
                    st.markdown(f"**Input Page URL:** [{template_url}]({template_url})")
                    st.info("""
                    **Steps to proceed:**
                    1. Click the input page URL above to open it in Notion
                    2. Duplicate the input page to your workspace (must be connected to your API key)
                    3. Copy the duplicated page's URL
                    4. Extract the Page ID (last part after the page name, e.g., `1234567890abcdef`)
                    5. Enter the Page ID below
                    """)
                if gt_page_url:
                    st.header("Ground Truth Output Page")
                    st.markdown(f"**Output Page URL (for reference):** [{gt_page_url}]({gt_page_url})")
        
        st.header("Notion Page ID")
        
        # Page ID input
        page_id = st.text_input(
            "Enter the ID of the duplicated Notion page",
            help="The ID from your duplicated Notion page URL (e.g., from https://notion.so/Page-Name-1234567890abcdef, use 1234567890abcdef)"
        )
        
        # (Ground-Truth Output Page now displayed above with Notion Input Page)
    
    # Evaluation section
    st.header("Run Evaluation")
    
    # Validation
    # Get the required API key variable for validation
    required_api_key_var = model_display_info[model_name]["api_key_var"]
    
    ready_to_run = all([
        api_key or os.getenv(required_api_key_var),
        notion_key,
        page_id,
        selected_task
    ])
    
    if not ready_to_run:
        missing = []
        if not (api_key or os.getenv(required_api_key_var)):
            missing.append(f"API Key ({required_api_key_var})")
        if not notion_key:
            missing.append("Notion API Key")
        if not page_id:
            missing.append("Page ID")
        if not selected_task:
            missing.append("Task selection")
        
        st.warning(f"Please provide: {', '.join(missing)}")
    
    # Control buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        # Run button (for execution only)
        if not st.session_state.is_executing:
            if st.button("Run", disabled=not ready_to_run, type="primary"):
                # Initialize evaluator
                st.session_state.evaluator = DemoEvaluator(
                    notion_key=notion_key,
                    model_name=model_name,
                    api_key=api_key or os.getenv(required_api_key_var),
                    base_url=base_url
                )
                st.session_state.evaluator.reset()
                
                # Store task and page info for later verification
                st.session_state.selected_task_name = selected_task
                st.session_state.selected_page_id = page_id
                
                # Reset session state for execution
                st.session_state.is_executing = True
                st.session_state.logs_list = []
                st.session_state.current_response = None
                st.session_state.execution_result = None
                st.session_state.verification_result = None
                st.session_state.log_queue = queue.Queue()  # Create fresh queue
                
                # Start execution in background thread
                st.session_state.execution_thread = threading.Thread(
                    target=run_execution_in_thread,
                    args=(st.session_state.evaluator, selected_task, page_id, st.session_state.log_queue)
                )
                st.session_state.execution_thread.start()
                st.rerun()
        else:
            if st.button("Stop", type="secondary"):
                if st.session_state.evaluator:
                    st.session_state.evaluator.stop()
                st.session_state.is_executing = False
                st.rerun()
    
    with col2:
        # Verify button (independent of execution)
        can_verify = (
            ready_to_run and  # Same requirements as Run button
            not st.session_state.is_executing and
            not st.session_state.is_verifying
        )
        
        if can_verify:
            if st.button("Verify", type="primary"):
                # Create evaluator if it doesn't exist
                if not st.session_state.evaluator:
                    st.session_state.evaluator = DemoEvaluator(
                        notion_key=notion_key,
                        model_name=model_name,
                        api_key=api_key or os.getenv(required_api_key_var),
                        base_url=base_url
                    )
                
                st.session_state.is_verifying = True
                # Start verification in background thread using current form values
                st.session_state.verification_thread = threading.Thread(
                    target=run_verification_in_thread,
                    args=(st.session_state.evaluator, selected_task, page_id, st.session_state.log_queue)
                )
                st.session_state.verification_thread.start()
                st.rerun()
        elif st.session_state.is_verifying:
            st.info("Verifying...")
        else:
            st.button("Verify", disabled=True, help="Please provide all required configuration")

    with col3:
        if st.button("Clear", disabled=st.session_state.is_executing or st.session_state.is_verifying):
            st.session_state.logs_list = []
            st.session_state.current_response = None
            st.session_state.execution_result = None
            st.session_state.verification_result = None
            st.session_state.selected_task_name = None
            st.session_state.selected_page_id = None
            st.rerun()
    
    with col4:
        # Status indicator
        if st.session_state.is_executing:
            st.info("Executing...")
        elif st.session_state.is_verifying:
            st.info("Verifying...")
        elif st.session_state.execution_result and st.session_state.verification_result:
            if st.session_state.execution_result.execution_success and st.session_state.verification_result.verification_success:
                st.success("✅ Completed")
            else:
                st.error("❌ Failed")
        elif st.session_state.execution_result:
            if st.session_state.execution_result.execution_success:
                st.success("✅ Executed")
            else:
                st.error("❌ Execution Failed")
    
    # Real-time logs display
    if st.session_state.logs_list:
        st.subheader("Live Execution Log")
        logs_container = st.container()
        with logs_container:
            st.markdown("\n\n".join(st.session_state.logs_list))
    
    # Process queue and auto-refresh during execution or verification
    if st.session_state.is_executing or st.session_state.is_verifying:
        # Process all pending log entries from the queue
        queue_processed = False
        while not st.session_state.log_queue.empty():
            try:
                log_entry = st.session_state.log_queue.get_nowait()
                queue_processed = True
                
                if log_entry["type"] == "execution_completion":
                    # Execution completed
                    st.session_state.execution_result = log_entry["result"]
                    st.session_state.is_executing = False
                    break
                elif log_entry["type"] == "verification_completion":
                    # Verification completed
                    st.session_state.verification_result = log_entry["result"]
                    st.session_state.is_verifying = False
                    break
                elif log_entry["type"] == "error":
                    # Error occurred
                    if st.session_state.is_executing:
                        st.session_state.is_executing = False
                    if st.session_state.is_verifying:
                        st.session_state.is_verifying = False
                    st.error(f"Error: {log_entry['error']}")
                    break
                elif log_entry["type"] == "tool_call":
                    # Tool call log
                    timestamp = log_entry.get("timestamp", 0)
                    st.session_state.logs_list.append(f"🔧 **{timestamp:.1f}s**  {log_entry['message']}")
                    st.session_state.current_response = None
                elif log_entry["type"] == "response":
                    # Response log
                    timestamp = log_entry.get("timestamp", 0)
                    content = log_entry["content"].strip()
                    if content:
                        response_text = f"📢 **{timestamp:.1f}s**  {content}"
                        
                        if st.session_state.current_response is None:
                            st.session_state.logs_list.append(response_text)
                            st.session_state.current_response = len(st.session_state.logs_list) - 1
                        else:
                            st.session_state.logs_list[st.session_state.current_response] = response_text
            except queue.Empty:
                break
        
        # Rerun if we processed any queue items or if still running
        if queue_processed or st.session_state.is_executing or st.session_state.is_verifying:
            time.sleep(0.1)  # Brief pause to reduce CPU usage
            st.rerun()
    
    # Results display
    if st.session_state.execution_result or st.session_state.verification_result:
        st.header("📊 Results")
        
        # Execution Results
        if st.session_state.execution_result:
            execution_result = st.session_state.execution_result
            
            st.subheader("Execution Results")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Status", "✅ Success" if execution_result.execution_success else "❌ Failed")
            with col2:
                st.metric("Time", f"{execution_result.execution_time:.2f}s")
            
            if execution_result.execution_error:
                st.error(f"**Execution Error:** {execution_result.execution_error}")
            
            # Agent conversation
            if execution_result.agent_messages:
                with st.expander("💬 Agent Conversation"):
                    for msg in execution_result.agent_messages:
                        if hasattr(msg, 'role') and hasattr(msg, 'content'):
                            role = msg.role
                            content = msg.content
                            if role == "user":
                                st.markdown(f"**User:** {content}")
                            elif role == "assistant":
                                st.markdown(f"**Assistant:** {content}")
        
        # Verification Results
        if st.session_state.verification_result:
            verification_result = st.session_state.verification_result
            
            st.subheader("🔍 Verification Results")
            st.metric("Status", "✅ Passed" if verification_result.verification_success else "❌ Failed")
            
            if verification_result.verification_output:
                with st.expander("Verification Output", expanded=True):
                    st.code(verification_result.verification_output)
        
        # Overall result (only if both are complete)
        if (st.session_state.execution_result and st.session_state.verification_result and 
            not st.session_state.is_executing and not st.session_state.is_verifying):
            if (st.session_state.execution_result.execution_success and 
                st.session_state.verification_result.verification_success):
                st.success("✅ Task completed and verified successfully!")
            else:
                st.error("❌ Task failed. See details above.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
    MCPBench Demo - Evaluating LLM Agents with Model Context Protocol
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()