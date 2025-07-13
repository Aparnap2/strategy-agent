import os
from typing import Dict, Any, TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from agents.clarification_agent import ClarificationAgent
from agents.planner_agent import PlannerAgent
from agents.dev_architect_agent import DevArchitectAgent
from agents.client_persona_agent import ClientPersonaAgent, PersonaType
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """State for the agent workflow."""
    # User input and context
    user_input: str
    context: Dict[str, Any]
    
    # Agent outputs
    clarified_requirements: str
    project_plan: Dict[str, Any]
    technical_architecture: Dict[str, Any]
    client_feedbacks: Dict[str, Any]
    consolidated_feedback: Dict[str, Any]
    
    # Workflow control
    needs_clarification: bool
    iteration_count: int
    max_iterations: int

class AgentOrchestrator:
    """
    Orchestrates the interaction between different agents using LangGraph.
    
    This class defines the workflow and data flow between the ClarificationAgent,
    PlannerAgent, DevArchitectAgent, and ClientPersonaAgent.
    """
    
    def __init__(self, max_iterations: int = 3):
        """
        Initialize the AgentOrchestrator.
        
        Args:
            max_iterations: Maximum number of feedback iterations to allow
        """
        self.max_iterations = max_iterations
        
        # Initialize all agents
        self.clarification_agent = ClarificationAgent()
        self.planner_agent = PlannerAgent()
        self.dev_architect_agent = DevArchitectAgent()
        
        # Initialize client personas
        self.client_personas = [
            ClientPersonaAgent(persona_type=PersonaType.TECHNICAL_CTO),
            ClientPersonaAgent(persona_type=PersonaType.BUSINESS_OWNER),
            ClientPersonaAgent(persona_type=PersonaType.END_USER)
        ]
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        """Build the LangGraph workflow."""
        # Create a new graph
        workflow = StateGraph(AgentState)
        
        # Define nodes
        workflow.add_node("clarify_requirements", self._clarify_requirements)
        workflow.add_node("create_plan", self._create_plan)
        workflow.add_node("design_architecture", self._design_architecture)
        workflow.add_node("gather_feedback", self._gather_feedback)
        workflow.add_node("consolidate_feedback", self._consolidate_feedback)
        workflow.add_node("check_iteration_limit", self._check_iteration_limit)
        
        # Define edges
        workflow.add_edge("clarify_requirements", "create_plan")
        workflow.add_edge("create_plan", "design_architecture")
        workflow.add_edge("design_architecture", "gather_feedback")
        workflow.add_edge("gather_feedback", "consolidate_feedback")
        
        # Add conditional edge for feedback processing
        def route_feedback(state: AgentState) -> str:
            """Route based on whether we need to continue processing feedback."""
            result = self._should_continue(state)
            if isinstance(result, dict):
                return result.get("status", "end").lower()
            return str(result).lower()
            
        workflow.add_conditional_edges(
            "consolidate_feedback",
            route_feedback,
            {
                "continue": "check_iteration_limit",
                "end": END
            }
        )
        
        # Add conditional edge for iteration limit check
        def route_iteration(state: AgentState) -> str:
            """Route based on iteration limit check."""
            result = self._handle_iteration_limit(state)
            if isinstance(result, dict):
                return result.get("status", "max_iterations_received").lower()
            return str(result).lower()
            
        workflow.add_conditional_edges(
            "check_iteration_limit",
            route_iteration,
            {
                "continue": "clarify_requirements",
                "max_iterations_reached": END,
                "max_iterations_received": END  # Handle both cases for backward compatibility
            }
        )
        
        # Set the entry point
        workflow.set_entry_point("clarify_requirements")
        
        # Compile the workflow
        return workflow.compile()
    
    async def process_request(self, user_input: str, context: Dict[str, Any] = None, max_iterations: int = None) -> Dict[str, Any]:
        """
        Process a user request through the agent workflow.
        
        Args:
            user_input: The user's input/request
            context: Additional context for the request
            max_iterations: Override the default max iterations for this request
            
        Returns:
            Dict containing the final state of the workflow
        """
        # Use provided max_iterations or fall back to instance default
        effective_max_iterations = max_iterations if max_iterations is not None else self.max_iterations
        
        # Initialize the workflow state with all required fields
        initial_state: AgentState = {
            "user_input": user_input,
            "context": context or {},
            "clarified_requirements": "",
            "project_plan": {},
            "technical_architecture": {},
            "client_feedbacks": {},
            "consolidated_feedback": {},
            "needs_clarification": False,
            "iteration_count": 0,
            "max_iterations": effective_max_iterations
        }
        
        try:
            logger.info(f"Starting workflow processing with max_iterations={effective_max_iterations}")
            
            # Execute the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Log completion
            logger.info("Workflow processing completed successfully")
            
            # Return the final state with additional metadata
            return {
                "status": "completed",
                "result": final_state,
                "iterations_completed": final_state.get("iteration_count", 0),
                "max_iterations": effective_max_iterations,
                "success": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in workflow processing: {str(e)}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "iterations_completed": initial_state.get("iteration_count", 0),
                "max_iterations": effective_max_iterations,
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _format_final_output(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Format the final output from the workflow state."""
        return {
            "status": "completed",
            "iterations": state["iteration_count"],
            "clarified_requirements": state["clarified_requirements"],
            "project_plan": state["project_plan"],
            "technical_architecture": state["technical_architecture"],
            "client_feedbacks": state["client_feedbacks"],
            "consolidated_feedback": state["consolidated_feedback"],
            "needs_clarification": state["needs_clarification"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Node implementations
    
    async def _clarify_requirements(self, state: AgentState) -> Dict[str, Any]:
        """Clarify the user's requirements."""
        try:
            logger.info("Clarifying requirements...")
            clarified = self.clarification_agent.clarify(
                state["user_input"],
                state["context"]
            )
            return {"clarified_requirements": clarified}
        except Exception as e:
            logger.error(f"Error in clarify_requirements: {str(e)}")
            return {"clarified_requirements": f"Error: {str(e)}"}
    
    async def _create_plan(self, state: AgentState) -> Dict[str, Any]:
        """Create a project plan from the clarified requirements."""
        try:
            logger.info("Creating project plan...")
            plan = self.planner_agent.plan(
                state["clarified_requirements"],
                state["context"]
            )
            return {"project_plan": plan}
        except Exception as e:
            logger.error(f"Error in create_plan: {str(e)}")
            return {"project_plan": {"error": str(e)}}
    
    async def _design_architecture(self, state: AgentState) -> Dict[str, Any]:
        """Design the technical architecture based on the project plan."""
        try:
            logger.info("Designing technical architecture...")
            architecture = self.dev_architect_agent.design_architecture(
                state["project_plan"],
                state["context"]
            )
            return {"technical_architecture": architecture}
        except Exception as e:
            logger.error(f"Error in design_architecture: {str(e)}")
            return {"technical_architecture": {"error": str(e)}}
    
    async def _gather_feedback(self, state: AgentState) -> Dict[str, Any]:
        """Gather feedback from client personas on the technical architecture."""
        try:
            logger.info("Gathering client feedback...")
            feedbacks = {}
            
            for persona in self.client_personas:
                feedback = persona.provide_feedback(
                    state["technical_architecture"],
                    {
                        **state["context"],
                        "project_overview": state["clarified_requirements"],
                        "project_plan": state["project_plan"]
                    }
                )
                feedbacks[persona.persona_type.value] = feedback
            
            return {"client_feedbacks": feedbacks}
        except Exception as e:
            logger.error(f"Error in gather_feedback: {str(e)}")
            return {"client_feedbacks": {"error": str(e)}}
    
    async def _consolidate_feedback(self, state: AgentState) -> Dict[str, Any]:
        """
        Consolidate feedback from all client personas.
        
        This method analyzes feedback from different personas and determines if further
        clarification is needed in the next iteration.
        
        Args:
            state: The current agent state containing client feedback
            
        Returns:
            Dict containing consolidated feedback and needs_clarification flag
        """
        try:
            logger.info("Consolidating feedback from all personas...")
            
            # Validate feedback
            if not state.get("client_feedbacks") or "error" in state["client_feedbacks"]:
                logger.warning("No valid feedback to consolidate")
                return {
                    "consolidated_feedback": {"error": "No valid feedback to consolidate"},
                    "needs_clarification": False,
                    "iteration_count": state.get("iteration_count", 0)
                }
            
            # Prepare detailed consolidation
            all_feedback = state["client_feedbacks"]
            feedback_summary = []
            critical_issues = []
            
            # Process each persona's feedback
            for persona, feedback in all_feedback.items():
                if not feedback or not isinstance(feedback, dict):
                    continue
                    
                # Extract key points from feedback
                summary = feedback.get("summary", "")
                concerns = feedback.get("concerns", [])
                suggestions = feedback.get("suggestions", [])
                
                if summary:
                    feedback_summary.append(f"{persona}: {summary}")
                
                # Check for critical issues that need clarification
                if concerns and any("critical" in str(c).lower() for c in concerns):
                    critical_issues.extend(concerns)
            
            # Determine if clarification is needed
            needs_clarification = (
                bool(critical_issues) or  # Critical issues found
                len(feedback_summary) < 2 or  # Not enough feedback
                any("unclear" in f.lower() for f in feedback_summary)  # Unclear feedback
            )
            
            # Prepare consolidated feedback
            consolidated = {
                "all_feedback": all_feedback,
                "summary": "\n".join(feedback_summary) if feedback_summary else "No detailed feedback available",
                "critical_issues": critical_issues,
                "needs_clarification": needs_clarification,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Feedback consolidated. Needs clarification: {needs_clarification}")
            logger.debug(f"Consolidated feedback: {consolidated}")
            
            # Return updated state
            return {
                "consolidated_feedback": consolidated,
                "needs_clarification": needs_clarification,
                "iteration_count": state.get("iteration_count", 0) + 1
            }
            
        except Exception as e:
            logger.error(f"Error in consolidate_feedback: {str(e)}", exc_info=True)
            return {
                "consolidated_feedback": {
                    "error": f"Failed to consolidate feedback: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                },
                "needs_clarification": False,
                "iteration_count": state.get("iteration_count", 0)
            }
    
    # Conditional edge functions
    
    def _should_continue(self, state: AgentState) -> str:
        """
        Determine if we should continue with another iteration.
        
        Args:
            state: The current agent state
            
        Returns:
            str: "continue" if another iteration is needed, "end" otherwise
        """
        needs_clarification = state.get("needs_clarification", False)
        current_iteration = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", self.max_iterations)
        
        logger.info(f"Checking if another iteration is needed (Iteration {current_iteration + 1}/{max_iterations})")
        
        if needs_clarification:
            logger.info("Clarification is needed, continuing to next iteration")
            return "continue"
            
        logger.info("No more clarification needed, ending workflow")
        return "end"
    
    def _handle_iteration_limit(self, state: AgentState) -> Dict[str, str]:
        """
        Check if we've reached the maximum number of iterations.
        
        Args:
            state: The current agent state
            
        Returns:
            Dict with a 'status' key containing the next step
        """
        # Get the result from check_iteration_limit
        result = self._check_iteration_limit(state)
        
        # Ensure we have a valid status
        status = result.get("status", "continue").lower()
        
        if status == "max_iterations_reached":
            logger.warning(f"Reached maximum number of iterations ({state.get('max_iterations', self.max_iterations)})")
            return {"status": "max_iterations_reached"}
            
        logger.info(f"Continuing to iteration {state.get('iteration_count', 0) + 1}")
        return {"status": "continue"}
    
    def _check_iteration_limit(self, state: AgentState) -> Dict[str, str]:
        """
        Check if we've reached the maximum number of iterations.
        
        Args:
            state: The current agent state
            
        Returns:
            Dict with a 'status' key indicating whether to continue or end
        """
        current_iteration = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", self.max_iterations)
        
        logger.info(f"Checking iteration limit: {current_iteration + 1}/{max_iterations}")
        
        if current_iteration >= max_iterations:
            logger.warning(f"Reached maximum number of iterations ({max_iterations})")
            return {"status": "max_iterations_reached"}
            
        logger.info(f"Iteration {current_iteration + 1} of {max_iterations}, continuing...")
        return {"status": "continue"}

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        orchestrator = AgentOrchestrator()
        
        # Example user input
        user_input = "I want to build a task management application with user authentication, task creation, and due date reminders."
        
        # Run the workflow
        result = await orchestrator.process_request(user_input)
        
        # Print the result
        import json
        print(json.dumps(result, indent=2))
    
    asyncio.run(main())
