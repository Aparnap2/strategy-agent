import os
import time
import json
import requests
import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime

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
        return response.json().get("request_id")
    except Exception as e:
        st.error(f"Error submitting request: {str(e)}")
        return None

def get_status(request_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a request."""
    try:
        response = requests.get(f"{API_BASE_URL}/status/{request_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error getting status: {str(e)}")
        return None

def get_results(request_id: str) -> Optional[Dict[str, Any]]:
    """Get the results of a completed request."""
    try:
        response = requests.get(f"{API_BASE_URL}/results/{request_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error getting results: {str(e)}")
        return None

# UI Components
def render_sidebar():
    """Render the sidebar with project information and controls."""
    with st.sidebar:
        st.title("AI Strategy Assistant")
        st.markdown("---")
        
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
        st.warning("No active request. Please submit a new request.")
        st.session_state.active_tab = "input"
        st.rerun()
        return
    
    status = get_status(st.session_state.request_id)
    
    if not status:
        st.error("Failed to get request status. Please try again.")
        st.session_state.processing = False
        st.rerun()
        return
    
    # Show progress
    progress = status.get("progress", 0)
    status_text = status.get("status", "unknown").title()
    message = status.get("message", "")
    
    st.progress(progress / 100, f"{status_text}... {progress}%")
    
    if message:
        st.info(f"**Status:** {message}")
    
    # Show result if available
    if status.get("status") == "completed":
        st.session_state.processing = False
        render_results()
        return
    
    # Show error if failed
    if status.get("status") == "failed":
        st.error(f"Processing failed: {status.get('error', 'Unknown error')}")
        st.session_state.processing = False
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
    
    results = get_results(st.session_state.request_id)
    
    if not results:
        st.error("Failed to get results. Please try again.")
        return
    
    # Show tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "Project Plan", 
        "Technical Architecture", 
        "Client Feedback",
        "Raw Data"
    ])
    
    with tab1:
        if "project_plan" in results and results["project_plan"]:
            plan = results["project_plan"]
            
            st.markdown("### Project Overview")
            st.markdown(plan.get("project_overview", "No overview provided"))
            
            st.markdown("### Project Goals")
            for goal in plan.get("goals", []):
                st.markdown(f"- {goal}")
            
            st.markdown("### Key Deliverables")
            for deliverable in plan.get("deliverables", []):
                st.markdown(f"- {deliverable}")
            
            st.markdown("### Timeline")
            st.write(f"**Start Date:** {plan.get('start_date', 'N/A')}")
            st.write(f"**End Date:** {plan.get('end_date', 'N/A')}")
            st.write(f"**Duration:** {plan.get('duration', 'N/A')} weeks")
            
            st.markdown("### Tasks")
            for task in plan.get("tasks", []):
                with st.expander(f"{task.get('task_name')} (Phase {task.get('phase')})"):
                    st.write(f"**Description:** {task.get('description')}")
                    st.write(f"**Duration:** {task.get('duration')} weeks")
                    st.write(f"**Dependencies:** {', '.join(task.get('dependencies', ['None']))}")
        else:
            st.warning("No project plan available in the results.")
    
    with tab2:
        if "technical_architecture" in results and results["technical_architecture"]:
            arch = results["technical_architecture"]
            
            st.markdown("### Technology Stack")
            for category, tech in arch.get("technology_stack", {}).items():
                st.markdown(f"**{category.title()}:** {tech}")
            
            st.markdown("### System Architecture")
            st.markdown(arch.get("system_architecture", "No architecture diagram available."))
            
            st.markdown("### API Design")
            for endpoint, details in arch.get("api_design", {}).items():
                with st.expander(f"`{endpoint}` - {details.get('method')}"):
                    st.write(f"**Description:** {details.get('description')}")
                    st.write("**Request Body:**")
                    st.code(json.dumps(details.get('request_body', {}), indent=2), language="json")
                    st.write("**Response:**")
                    st.code(json.dumps(details.get('response', {}), indent=2), language="json")
        else:
            st.warning("No technical architecture available in the results.")
    
    with tab3:
        if "consolidated_feedback" in results and results["consolidated_feedback"]:
            feedback = results["consolidated_feedback"]
            
            st.markdown("### Summary of Feedback")
            st.write(feedback.get("summary", "No summary available."))
            
            st.markdown("### Top Concerns")
            for concern in feedback.get("top_concerns", []):
                st.markdown(f"- {concern}")
            
            st.markdown("### Suggested Improvements")
            for improvement in feedback.get("suggested_improvements", []):
                st.markdown(f"- {improvement}")
            
            if "persona_feedbacks" in feedback:
                st.markdown("---")
                st.markdown("### Detailed Feedback by Persona")
                
                for persona, persona_feedback in feedback["persona_feedbacks"].items():
                    with st.expander(f"{persona}"):
                        st.markdown(f"**Strengths:** {', '.join(persona_feedback.get('strengths', []))}")
                        st.markdown(f"**Concerns:** {', '.join(persona_feedback.get('concerns', []))}")
                        st.markdown(f"**Suggestions:** {', '.join(persona_feedback.get('suggestions', []))}")
        else:
            st.warning("No consolidated feedback available in the results.")
    
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
