import os
import time
import json
import requests
import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
from db import save_request, get_requests, get_request

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
POLLING_INTERVAL = 2  # seconds

# Page configuration
st.set_page_config(
    page_title="AI Strategy Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        font-weight: bold;
    }
    .success { color: #4CAF50; }
    .error { color: #f44336; }
    .warning { color: #ff9800; }
    .info { color: #2196F3; }
    .card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 1rem;
        background-color: white;
    }
    </style>
""", unsafe_allow_html=True)

# Session state initialization
if 'request_id' not in st.session_state:
    st.session_state.request_id = None
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "input"
if 'show_history' not in st.session_state:
    st.session_state.show_history = False

# API Client
def submit_request(user_input: str, max_iterations: int = 3) -> Optional[str]:
    """Submit a new request to the API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/process",
            json={
                "user_input": user_input,
                "max_iterations": max_iterations
            }
        )
        response.raise_for_status()
        request_id = response.json().get("request_id")
        
        # Save the request to history
        if request_id:
            save_request(
                request_id=request_id,
                user_input=user_input,
                status='pending'
            )
            
        return request_id
    except Exception as e:
        st.error(f"Error submitting request: {str(e)}")
        return None

def get_status(request_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a request."""
    if not request_id or not isinstance(request_id, str):
        st.error("Invalid request ID")
        return None
        
    try:
        logger.info(f"Fetching status for request_id: {request_id}")
        
        # Add a small delay to prevent overwhelming the server
        time.sleep(0.5)
        
        response = requests.get(
            f"{API_BASE_URL}/status/{request_id}",
            timeout=10  # Add timeout to prevent hanging
        )
        
        # Log the raw response for debugging
        logger.debug(f"Status API response: {response.status_code}, {response.text[:500]}")
        
        response.raise_for_status()
        status_data = response.json()
        
        # Handle different response formats
        if 'result' in status_data and isinstance(status_data['result'], dict):
            status_data = status_data['result']
        
        # Ensure we have required fields
        required_fields = ['status', 'progress']
        for field in required_fields:
            if field not in status_data:
                logger.warning(f"Missing required field in status response: {field}")
                status_data[field] = 'unknown' if field == 'status' else 0
        
        # Update the request in history if it's completed
        if status_data.get('status') == 'completed':
            try:
                results = get_results(request_id)
                if results:
                    save_request(
                        request_id=request_id,
                        user_input="",  # We don't update the user input
                        status='completed',
                        result=results
                    )
            except Exception as e:
                logger.error(f"Error saving results to history: {str(e)}", exc_info=True)
                # Don't fail the entire status check if history save fails
        
        return status_data
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error connecting to API: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json().get('detail', 'No details')
                error_msg = f"{error_msg}. Details: {error_detail}"
            except:
                error_msg = f"{error_msg}. Status code: {e.response.status_code}"
        st.error(error_msg)
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON response from server: {str(e)}"
        logger.error(error_msg, exc_info=True)
        st.error(error_msg)
        
    except Exception as e:
        error_msg = f"Unexpected error getting status: {str(e)}"
        logger.error(error_msg, exc_info=True)
        st.error(error_msg)
    
    return None

def get_results(request_id: str) -> Optional[Dict[str, Any]]:
    """Get the results of a completed request."""
    try:
        # Try to get results from API
        response = requests.get(f"{API_BASE_URL}/results/{request_id}", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Try different response formats
        if 'result' in data:
            if isinstance(data['result'], dict) and 'result' in data['result']:
                return data['result']['result']
            return data['result']
        return data
        
    except requests.exceptions.RequestException as e:
        st.warning(f"API request failed: {str(e)}. Trying to load from file...")
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse API response: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
    
    # Fall back to local file if API fails
    try:
        with open('response.json', 'r') as f:
            data = json.load(f)
            if 'result' in data:
                if isinstance(data['result'], dict) and 'result' in data['result']:
                    return data['result']['result']
                return data['result']
            return data
    except FileNotFoundError:
        st.error("No local results file found.")
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse local results file: {str(e)}")
    except Exception as e:
        st.error(f"Error loading from file: {str(e)}")
    
    return None

# UI Components
def render_history_modal():
    """Render the history modal dialog."""
    if st.session_state.get('show_history', False):
        with st.sidebar.expander("History", expanded=True):
            st.markdown("### Recent Requests")
            
            # Get recent requests
            requests = get_requests(limit=10)
            
            if not requests:
                st.info("No history available yet.")
            else:
                # Create a list of request summaries
                for req in requests:
                    status_emoji = "✅" if req['status'] == 'completed' else "⏳"
                    created = datetime.fromisoformat(req['created_at']).strftime('%Y-%m-%d %H:%M')
                    
                    # Show a button for each request
                    if st.button(
                        f"{status_emoji} {created}: {req['user_input'][:30]}...",
                        key=f"history_{req['id']}",
                        use_container_width=True
                    ):
                        # Load the selected request
                        load_request(req['id'])
            
            if st.button("Close History", use_container_width=True):
                st.session_state.show_history = False

def load_request(request_id: str):
    """Load a specific request by ID."""
    request_data = get_request(request_id)
    if request_data and 'result' in request_data and request_data['result']:
        try:
            result = eval(request_data['result'])  # Convert string back to dict
            st.session_state.request_id = request_id
            st.session_state.processing = False
            st.session_state.active_tab = "results"
            st.session_state.show_history = False
            st.rerun()
        except Exception as e:
            st.error(f"Error loading request: {str(e)}")

def render_sidebar():
    """Render the sidebar with project information and controls."""
    with st.sidebar:
        st.title("AI Strategy Assistant")
        st.markdown("---")
        
        # Add history button
        if st.button("📜 View History", use_container_width=True):
            st.session_state.show_history = True
        
        # Show history if enabled
        if st.session_state.get('show_history', False):
            render_history_modal()
        else:
            st.markdown("### New Request")
        
        if st.session_state.request_id:
            st.markdown(f"**Request ID:** `{st.session_state.request_id}`")
            
            if st.session_state.processing:
                if st.button("Cancel Processing"):
                    st.session_state.processing = False
                    st.session_state.request_id = None
                    st.rerun()
            else:
                if st.button("New Request"):
                    st.session_state.request_id = None
                    st.session_state.active_tab = "input"
                    st.rerun()
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        The AI Strategy Assistant helps you plan and architect software projects 
        by generating comprehensive project plans and technical architectures 
        based on your requirements.
        """)
        
        st.markdown("### How it works")
        st.markdown("""
        1. Enter your project requirements
        2. The AI will ask clarifying questions if needed
        3. Get a detailed project plan and technical architecture
        4. Review and refine with feedback from different stakeholder personas
        """)

def render_input_form():
    """Render the input form for new requests."""
    with st.form("project_requirements"):
        st.markdown("### Project Requirements")
        
        user_input = st.text_area(
            "Describe your project or strategy request in detail:",
            height=200,
            placeholder="e.g., I want to build a task management application with user authentication, task creation, and due date reminders..."
        )
        
        max_iterations = st.slider(
            "Maximum feedback iterations:",
            min_value=1,
            max_value=5,
            value=3,
            help="Number of feedback rounds with different stakeholder personas"
        )
        
        submitted = st.form_submit_button("Generate Strategy")
        
        if submitted and user_input.strip():
            st.session_state.request_id = submit_request(user_input, max_iterations)
            if st.session_state.request_id:
                st.session_state.processing = True
                st.session_state.active_tab = "results"
                st.rerun()
            else:
                st.error("Failed to submit request. Please try again.")

def render_processing():
    """Render the processing view."""
    if not st.session_state.request_id:
        st.error("No active request. Please submit a new request.")
        st.session_state.active_tab = "input"
        st.rerun()
        return
    
    status = get_status(st.session_state.request_id)
    
    if not status:
        st.error("Failed to get status. Please try again.")
        return
    
    # Check if processing is complete
    if status.get("status") == "completed":
        st.session_state.processing = False
        st.rerun()
        return
    
    # Show progress
    progress = status.get("progress", 0)
    status_text = status.get("status", "processing").capitalize()
    
    st.markdown(f"### {status_text}...")
    st.progress(min(progress / 100, 1.0))  # Ensure progress doesn't exceed 100%
    
    # Show status message if available
    if "message" in status:
        st.info(status["message"])
    
    # Show current iteration if available
    if "iteration" in status and "max_iterations" in status:
        st.write(f"Iteration {status['iteration']} of {status['max_iterations']}")
    
    # Show cancel button
    if st.button("❌ Cancel"):
        st.session_state.processing = False
        st.session_state.active_tab = "input"
        st.rerun()
        return
    
    # Continue polling
    time.sleep(POLLING_INTERVAL)
    st.rerun()

def render_results():
    """Render the results view."""
    if not st.session_state.request_id:
        st.warning("No active request. Please submit a new request.")
        st.session_state.active_tab = "input"
        st.rerun()
        return
    
    # Try to get results from API first, then fall back to local file
    results = get_results(st.session_state.request_id)
    
    # If no results from API, try to load from local file
    if not results:
        try:
            with open('response.json', 'r') as f:
                results = json.load(f)
                results = results.get('result', {}).get('result', {})
        except Exception as e:
            st.error(f"Failed to load results: {str(e)}")
            return
    
    if not results:
        st.error("No results available. Please try again.")
        return
    
    # Show tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "Project Plan", 
        "Technical Architecture", 
        "Client Feedback",
        "Raw Data"
    ])
    
    with tab1:
        st.markdown("## Project Plan")
        
        # Display Gantt chart
        st.markdown("### Gantt Chart")
        gantt_chart = """
        gantt
            title Project Timeline
            dateFormat  YYYY-MM-DD
            axisFormat %m-%d
            
            section T1
            Conduct discovery workshop :T1, 2025-07-13, 3d
            
            section T2
            Research technical constraints :T2, 2025-07-13, 2d
            
            section T3
            Define solution architecture :T3, 2025-07-16, 3d
            
            section T4
            Implement HubSpot API :T4, 2025-07-19, 5d
            
            section T5
            Build Discord bot :T5, 2025-07-19, 5d
            
            section T6
            Develop sync engine :T6, 2025-07-24, 7d
        """
        st.components.v1.html(f"""
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <div class="mermaid">
            {gantt_chart}
        </div>
        <script>mermaid.initialize({{startOnLoad:true}});</script>
        """, height=400)
        
        # Display tasks
        if "project_plan" in results and results["project_plan"]:
            tasks = results["project_plan"]
            st.markdown("### Task Details")
            
            for task in tasks:
                with st.expander(f"{task.get('id')}: {task.get('description')}"):
                    cols = st.columns(2)
                    with cols[0]:
                        st.metric("Start Date", task.get('start_date', 'N/A').split('T')[0])
                        st.metric("End Date", task.get('end_date', 'N/A').split('T')[0])
                    with cols[1]:
                        st.metric("Duration", f"{task.get('duration')} days")
                        st.metric("Priority", task.get('priority', 'Medium'))
                    
                    st.write("**Dependencies:**", ", ".join(task.get('dependencies', ['None'])))
                    st.write("**Resources:**", ", ".join(task.get('resources', ['Not specified'])))
    
    with tab2:
        st.markdown("## Technical Architecture")
        
        if "technical_architecture" in results and results["technical_architecture"]:
            arch = results["technical_architecture"]
            
            # Display system architecture diagram
            if "system_architecture" in arch and "diagram" in arch["system_architecture"]:
                st.markdown("### System Architecture")
                st.code(arch["system_architecture"]["diagram"], language="mermaid")
            
            # Display technology stack
            if "technology_stack" in arch:
                st.markdown("### Technology Stack")
                for category, items in arch["technology_stack"].items():
                    with st.expander(f"{category.title()}"):
                        if isinstance(items, list):
                            for item in items:
                                st.markdown(f"- **{item.get('name')}** (v{item.get('version', 'N/A')})")
                                st.caption(f"*{item.get('justification', 'No justification provided.')}*")
                        elif isinstance(items, dict):
                            for name, details in items.items():
                                st.markdown(f"- **{name}** (v{details.get('version', 'N/A')})")
                                st.caption(f"*{details.get('justification', 'No justification provided.')}*")
    
    with tab3:
        st.markdown("## Client Feedback")
        
        if "client_feedbacks" in results:
            feedbacks = results["client_feedbacks"]
            
            # Show consolidated feedback if available
            if "consolidated_feedback" in results:
                cons_feedback = results["consolidated_feedback"]
                st.markdown("### Consolidated Feedback")
                st.write(cons_feedback.get("summary", "No summary available."))
                
                if "critical_issues" in cons_feedback and cons_feedback["critical_issues"]:
                    st.markdown("#### Critical Issues")
                    for issue in cons_feedback["critical_issues"]:
                        st.error(f"⚠️ {issue}")
                
                st.markdown("---")
            
            # Show individual feedbacks
            for role, feedback in feedbacks.items():
                with st.expander(f"{role.upper()} Feedback"):
                    st.markdown(f"**Summary:** {feedback.get('feedback_summary', 'No summary provided.')}")
                    
                    if "strengths" in feedback and feedback["strengths"]:
                        st.markdown("#### Strengths")
                        for strength in feedback["strengths"]:
                            st.success(f"✓ {strength}")
                    
                    if "concerns" in feedback and feedback["concerns"]:
                        st.markdown("#### Concerns")
                        for concern in feedback["concerns"]:
                            st.warning(f"⚠ {concern}")
                    
                    if "suggestions" in feedback and feedback["suggestions"]:
                        st.markdown("#### Suggestions")
                        for suggestion in feedback["suggestions"]:
                            st.info(f"💡 {suggestion}")
                    
                    if "overall_rating" in feedback:
                        st.metric("Overall Rating", 
                               f"{feedback['overall_rating']}/5", 
                               f"Confidence: {feedback.get('confidence_in_rating', 0) * 100:.0f}%")
    
    with tab4:
        st.json(results)

# Main App
def main():
    """Main application entry point."""
    st.title("AI Strategy Assistant")
    
    # Render sidebar
    render_sidebar()
    
    # Main content area
    if st.session_state.active_tab == "input":
        render_input_form()
    elif st.session_state.active_tab == "results" or st.session_state.processing:
        if st.session_state.processing:
            render_processing()
        else:
            render_results()

if __name__ == "__main__":
    main()
