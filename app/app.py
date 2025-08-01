"""
MCP-League Demo Application
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

from demo_evaluator import DemoEvaluator
from demo_task_manager import DemoTaskManager
from demo_model_config import DemoModelConfig


def run_evaluation_in_thread(evaluator, task_name, page_id, log_queue):
    """Run evaluation in a separate thread."""
    try:
        def queue_callback(log_entry):
            """Thread-safe callback that uses queue instead of session_state"""
            log_queue.put(log_entry)
        
        result = evaluator.evaluate_task(task_name, page_id, callback=queue_callback)
        # Signal completion
        log_queue.put({"type": "completion", "result": result})
    except Exception as e:
        # Signal error
        log_queue.put({"type": "error", "error": str(e)})


def main():
    st.set_page_config(
        page_title="MCP-League Demo",
        page_icon="🔬",
        layout="wide"
    )
    
    # Initialize session state
    if 'is_running' not in st.session_state:
        st.session_state.is_running = False
    if 'evaluator' not in st.session_state:
        st.session_state.evaluator = None
    if 'execution_thread' not in st.session_state:
        st.session_state.execution_thread = None
    if 'logs_list' not in st.session_state:
        st.session_state.logs_list = []
    if 'current_response' not in st.session_state:
        st.session_state.current_response = None
    if 'result' not in st.session_state:
        st.session_state.result = None
    if 'log_queue' not in st.session_state:
        st.session_state.log_queue = queue.Queue()
    
    st.title("🔬 MCP-League Evaluation Demo")
    st.markdown("""
    This demo shows how MCP-League evaluates LLM agents on Notion tasks.
    Select a task, provide your Notion credentials, and watch the evaluation process.
    """)
    
    # Initialize task manager
    task_manager = DemoTaskManager()
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
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
        st.header("📝 Task Selection")
        
        # Get available tasks
        available_tasks = task_manager.get_available_tasks()
        
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
        st.header("🎯 Evaluation Target")
        
        # Page ID input
        page_id = st.text_input(
            "Notion Page ID",
            placeholder="Enter the ID of the Notion page to evaluate",
            help="The ID of the Notion page where the task should be performed"
        )
        
        st.info("""
        **How to get Page ID:**
        1. Open your Notion page in a browser
        2. Copy the URL (e.g., https://www.notion.so/Page-Name-1234567890abcdef)
        3. The Page ID is the last part: 1234567890abcdef
        """)
    
    # Evaluation section
    st.header("🚀 Run Evaluation")
    
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
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if not st.session_state.is_running:
            if st.button("▶️ Run", disabled=not ready_to_run, type="primary"):
                # Initialize evaluator
                st.session_state.evaluator = DemoEvaluator(
                    notion_key=notion_key,
                    model_name=model_name,
                    api_key=api_key or os.getenv(required_api_key_var),
                    base_url=base_url
                )
                st.session_state.evaluator.reset()
                
                # Reset session state
                st.session_state.is_running = True
                st.session_state.logs_list = []
                st.session_state.current_response = None
                st.session_state.result = None
                st.session_state.log_queue = queue.Queue()  # Create fresh queue
                
                # Start execution in background thread
                st.session_state.execution_thread = threading.Thread(
                    target=run_evaluation_in_thread,
                    args=(st.session_state.evaluator, selected_task, page_id, st.session_state.log_queue)
                )
                st.session_state.execution_thread.start()
                st.rerun()
        else:
            if st.button("⏹️ Stop", type="secondary"):
                if st.session_state.evaluator:
                    st.session_state.evaluator.stop()
                st.session_state.is_running = False
                st.rerun()
    
    with col2:
        if st.button("🗑️ Clear", disabled=st.session_state.is_running):
            st.session_state.logs_list = []
            st.session_state.current_response = None
            st.session_state.result = None
            st.rerun()
    
    with col3:
        if st.session_state.is_running:
            st.info("🔄 Running...")
        elif st.session_state.result:
            if st.session_state.result.execution_success and st.session_state.result.verification_success:
                st.success("✅ Completed")
            else:
                st.error("❌ Failed")
    
    # Real-time logs display
    if st.session_state.logs_list:
        st.subheader("🔄 Live Execution Log")
        logs_container = st.container()
        with logs_container:
            st.markdown("\n\n".join(st.session_state.logs_list))
    
    # Process queue and auto-refresh during execution
    if st.session_state.is_running:
        # Process all pending log entries from the queue
        queue_processed = False
        while not st.session_state.log_queue.empty():
            try:
                log_entry = st.session_state.log_queue.get_nowait()
                queue_processed = True
                
                if log_entry["type"] == "completion":
                    # Execution completed
                    st.session_state.result = log_entry["result"]
                    st.session_state.is_running = False
                    break
                elif log_entry["type"] == "error":
                    # Execution failed
                    st.session_state.result = None
                    st.session_state.is_running = False
                    st.error(f"Execution error: {log_entry['error']}")
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
        if queue_processed or st.session_state.is_running:
            time.sleep(0.1)  # Brief pause to reduce CPU usage
            st.rerun()
    
    # Results display (when execution is complete)
    if st.session_state.result and not st.session_state.is_running:
        result = st.session_state.result
        
        st.header("📊 Results")
        
        # Summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Execution", "✅ Success" if result.execution_success else "❌ Failed")
        with col2:
            st.metric("Verification", "✅ Passed" if result.verification_success else "❌ Failed")
        with col3:
            st.metric("Time", f"{result.execution_time:.2f}s")
        
        # Detailed results
        if result.execution_error:
            st.error(f"**Execution Error:** {result.execution_error}")
        
        if result.verification_output:
            with st.expander("Verification Output", expanded=True):
                st.code(result.verification_output)
        
        # Agent conversation
        if result.agent_messages:
            with st.expander("💬 Agent Conversation"):
                for msg in result.agent_messages:
                    if hasattr(msg, 'role') and hasattr(msg, 'content'):
                        role = msg.role
                        content = msg.content
                        if role == "user":
                            st.markdown(f"**User:** {content}")
                        elif role == "assistant":
                            st.markdown(f"**Assistant:** {content}")
        
        # Overall result
        if result.execution_success and result.verification_success:
            st.success("✅ Task completed and verified successfully!")
        else:
            st.error("❌ Task failed. See details above.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
    MCP-League Demo - Evaluating LLM Agents with Model Context Protocol
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()