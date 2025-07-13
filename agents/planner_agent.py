import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from the project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Configure logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Now import other modules after environment is loaded
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate

class PlannerAgent:
    """
    Agent responsible for breaking down clarified requirements into actionable steps.
    
    This agent takes the output from the ClarificationAgent and creates a detailed
    project plan with tasks, dependencies, and estimated timelines.
    """
    
    def __init__(self, prompt_template: Optional[PromptTemplate] = None):
        """
        Initialize the PlannerAgent.
        
        Args:
            prompt_template: Optional custom prompt template. If not provided,
                           a default template will be used.
        """
        # Initialize the LLM with OpenRouter
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
            
        # Configure the LLM with OpenRouter
        model_name = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")
        logger.info(f"Initializing PlannerAgent with model: {model_name}")
        
        try:
            self.llm = ChatOpenAI(
                openai_api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                model=model_name,
                temperature=0.3,  # Lower temperature for more deterministic planning
                max_tokens=2000,
                timeout=30  # Add timeout to prevent hanging
            )
            
            # Test the connection
            self.llm.invoke([HumanMessage(content="Test")])
            logger.info("Successfully connected to OpenRouter API")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChatOpenAI with model {model_name}: {str(e)}")
            raise
        
        # Set up the prompt template
        self.prompt_template = prompt_template or self._get_default_prompt_template()
    
    def _get_default_prompt_template(self) -> PromptTemplate:
        """Return the default prompt template for planning."""
        template = """You are an expert project planner. Your task is to break down the following project requirements into a detailed, actionable plan.
        
Project Requirements:
{requirements}

Additional Context:
{context}

Create a comprehensive project plan with the following structure for each task:
1. Task ID (e.g., T1, T2)
2. Task Description (clear and specific)
3. Dependencies (list of task IDs or 'None')
4. Estimated Duration (in days)
5. Required Resources/Skills

For the project, please consider:
- Breaking down complex tasks into smaller, manageable subtasks
- Identifying parallel workstreams
- Considering technical dependencies
- Accounting for review and testing phases
- Including buffer time for unexpected delays

Format your response as a JSON array of task objects. Each task should have:
- id: Unique identifier (string)
- description: Detailed task description (string)
- dependencies: List of task IDs this task depends on (array of strings)
- duration: Estimated duration in days (number)
- resources: List of required resources/skills (array of strings)
- priority: Priority level (high/medium/low)

Example:
[
  {{
    "id": "T1",
    "description": "Set up development environment",
    "dependencies": [],
    "duration": 2,
    "resources": ["DevOps"],
    "priority": "high"
  }},
  {{
    "id": "T2",
    "description": "Design database schema",
    "dependencies": [],
    "duration": 3,
    "resources": ["Backend", "Database"],
    "priority": "high"
  }}
]

Project Plan:"""
        return PromptTemplate(
            input_variables=["requirements", "context"],
            template=template
        )
    
    def plan(self, requirements: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Generate a detailed project plan from requirements.
        
        Args:
            requirements: Clarified requirements from the ClarificationAgent
            context: Optional dictionary containing additional context
            
        Returns:
            List of task dictionaries, each containing task details
        """
        if not requirements or not isinstance(requirements, str):
            raise ValueError("Valid requirements must be provided")
            
        try:
            # Prepare context for the prompt
            context = context or {}
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            
            # Format the prompt
            prompt = self.prompt_template.format(
                requirements=requirements,
                context=context_str
            )
            
            # Get the LLM response
            response = self.llm.invoke([
                SystemMessage(content="You are an expert project planner. Your task is to break down project requirements into a detailed, actionable plan."),
                HumanMessage(content=prompt)
            ])
            
            # Parse the response into a structured format
            tasks = self._parse_plan_response(response.content)
            
            # Add timeline information
            tasks = self._calculate_timeline(tasks)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error in PlannerAgent: {str(e)}", exc_info=True)
            raise RuntimeError("Failed to generate project plan. Please try again with more specific requirements.")
    
    def _parse_plan_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse the LLM response into a structured list of tasks.
        
        Args:
            response: Raw response from the LLM
            
        Returns:
            List of parsed task dictionaries
        """
        try:
            # Clean the response to extract just the JSON portion
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            json_str = response[json_start:json_end]
            
            # Parse the JSON
            tasks = json.loads(json_str)
            
            # Validate the structure
            required_keys = {"id", "description", "dependencies", "duration", "resources", "priority"}
            for task in tasks:
                if not all(key in task for key in required_keys):
                    raise ValueError("Invalid task structure in response")
            
            return tasks
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse plan response: {str(e)}")
            # Fallback to a simple format if parsing fails
            return [{
                "id": "T1",
                "description": "Review and refine project requirements",
                "dependencies": [],
                "duration": 1,
                "resources": ["Project Manager"],
                "priority": "high",
                "notes": "Automatic fallback task due to parsing error"
            }]
    
    def _calculate_timeline(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add start and end dates to tasks based on dependencies and durations.
        
        Args:
            tasks: List of tasks with dependencies and durations
            
        Returns:
            List of tasks with added timeline information
        """
        if not tasks:
            return []
            
        # Create a map of task_id to task for easier lookup
        task_map = {task["id"]: task for task in tasks}
        
        # Helper function to calculate end date for a task
        def get_task_end_date(task_id: str) -> datetime:
            task = task_map[task_id]
            
            # If we've already calculated the end date, return it
            if "end_date" in task and isinstance(task["end_date"], datetime):
                return task["end_date"]
                
            # If no dependencies, start from today
            if not task.get("dependencies"):
                task["start_date"] = datetime.now()
            else:
                # Start date is the latest end date of all dependencies
                deps_end_dates = [get_task_end_date(dep) for dep in task["dependencies"]]
                task["start_date"] = max(deps_end_dates) if deps_end_dates else datetime.now()
            
            # Ensure duration is a number
            duration_days = int(task.get("duration", 1))  # Default to 1 day if duration is missing
            
            # Calculate end date based on duration
            task["end_date"] = task["start_date"] + timedelta(days=duration_days)
            return task["end_date"]
        
        # Calculate end dates for all tasks
        for task in tasks:
            try:
                # Ensure task has required fields
                if "id" not in task:
                    task["id"] = f"task_{len(task_map) + 1}"
                if "duration" not in task:
                    task["duration"] = 1  # Default to 1 day
                
                # Calculate dates
                get_task_end_date(task["id"])
                
                # Convert datetime objects to ISO format strings for JSON serialization
                if isinstance(task["start_date"], datetime):
                    task["start_date"] = task["start_date"].isoformat()
                if isinstance(task["end_date"], datetime):
                    task["end_date"] = task["end_date"].isoformat()
                    
            except Exception as e:
                logger.error(f"Error calculating timeline for task {task.get('id', 'unknown')}: {str(e)}")
                # Set default values on error
                now = datetime.now().isoformat()
                task["start_date"] = now
                task["end_date"] = (datetime.now() + timedelta(days=1)).isoformat()
        
        return tasks
