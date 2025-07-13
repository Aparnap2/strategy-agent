import os
import json
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
import logging
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DevArchitectAgent:
    """
    Agent responsible for designing technical architecture and implementation strategies.
    
    This agent takes the project plan from the PlannerAgent and generates a detailed
    technical architecture, including technology stack recommendations, system design,
    and initial code scaffolding.
    """
    
    def __init__(self, prompt_template: Optional[PromptTemplate] = None):
        """
        Initialize the DevArchitectAgent.
        
        Args:
            prompt_template: Optional custom prompt template. If not provided,
                           a default template will be used.
        """
        # Initialize the LLM with OpenRouter
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
            
        self.llm = ChatOpenAI(
            openai_api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            model="tngtech/deepseek-r1t2-chimera:free",
            temperature=0.5,  # Moderate temperature for balanced creativity
            max_tokens=4000
        )
        
        # Set up the prompt template
        self.prompt_template = prompt_template or self._get_default_prompt_template()
    
    def _get_default_prompt_template(self) -> PromptTemplate:
        """Return the default prompt template for architecture design."""
        template = """You are an expert software architect. Your task is to design the technical architecture for the following project plan.

Project Overview:
{project_overview}

Project Plan:
{plan}

Additional Context:
{context}

Please provide a comprehensive technical architecture that includes:
1. Technology Stack: Frontend, Backend, Database, DevOps, etc.
2. System Architecture: High-level components and their interactions
3. API Design: Key endpoints and data structures
4. Data Model: Database schema or data storage approach
5. Security Considerations: Authentication, authorization, data protection
6. Scalability: How the system will handle growth
7. Deployment Strategy: CI/CD, hosting, infrastructure as code
8. Initial Code Structure: Recommended project structure
9. Development Environment: Setup instructions
10. Testing Strategy: Unit, integration, and E2E testing approach

For each component, include:
- Description
- Justification for the choice
- Any potential alternatives considered
- Implementation considerations

Format your response as a JSON object with the following structure:
{{
  "technology_stack": {{
    "frontend": [{{ "name": "React", "version": "18.2.0", "justification": "..." }}],
    "backend": [{{ "name": "FastAPI", "version": "0.95.0", "justification": "..." }}],
    "database": [{{ "name": "PostgreSQL", "version": "15.0", "justification": "..." }}],
    "devops": [{{ "name": "Docker", "version": "20.10", "justification": "..." }}]
  }},
  "system_architecture": {{
    "components": [
      {{
        "name": "API Gateway",
        "description": "...",
        "responsibilities": ["..."],
        "interactions": ["..."]
      }}
    ],
    "diagram": "mermaid or text description of the architecture"
  }},
  "api_design": {{
    "endpoints": [
      {{
        "path": "/api/resource",
        "method": "GET",
        "description": "...",
        "request": {{...}},
        "response": {{...}}
      }}
    ]
  }},
  "data_model": {{
    "tables": [
      {{
        "name": "users",
        "fields": [
          {{"name": "id", "type": "UUID", "constraints": "PRIMARY KEY"}},
          {{"name": "email", "type": "VARCHAR(255)", "constraints": "UNIQUE, NOT NULL"}}
        ],
        "relationships": []
      }}
    ]
  }},
  "security_considerations": ["..."],
  "scalability_considerations": ["..."],
  "deployment_strategy": "...",
  "code_structure": {{
    "frontend": ["src/components/", "src/pages/", ...],
    "backend": ["app/api/", "app/models/", ...]
  }},
  "development_environment": ["..."],
  "testing_strategy": ["..."]
}}

Technical Architecture:"""
        return PromptTemplate(
            input_variables=["project_overview", "plan", "context"],
            template=template
        )
    
    def design_architecture(self, plan: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Design the technical architecture based on the project plan.
        
        Args:
            plan: Project plan from the PlannerAgent (list of tasks)
            context: Optional dictionary containing additional context
            
        Returns:
            Dictionary containing the technical architecture design
        """
        if not plan or not isinstance(plan, list):
            raise ValueError("A valid project plan must be provided")
            
        try:
            # Prepare context for the prompt
            context = context or {}
            
            # Extract project overview from the plan
            project_overview = self._extract_project_overview(plan, context)
            
            # Format the plan for the prompt
            formatted_plan = "\n".join(
                f"{i+1}. {task.get('description', 'No description')} "
                f"(Duration: {task.get('duration', '?')} days, "
                f"Priority: {task.get('priority', 'medium')})"
                for i, task in enumerate(plan)
            )
            
            # Format the prompt
            prompt = self.prompt_template.format(
                project_overview=project_overview,
                plan=formatted_plan,
                context=json.dumps(context, indent=2)
            )
            
            # Get the LLM response
            response = self.llm.invoke([
                SystemMessage(content="You are an expert software architect. Your task is to design the technical architecture for software projects."),
                HumanMessage(content=prompt)
            ])
            
            # Parse the response into a structured format
            architecture = self._parse_architecture_response(response.content)
            
            # Add any derived fields or validations
            architecture = self._enrich_architecture(architecture, plan, context)
            
            return architecture
            
        except Exception as e:
            logger.error(f"Error in DevArchitectAgent: {str(e)}", exc_info=True)
            return {
                "error": "Failed to generate technical architecture",
                "details": str(e),
                "fallback_architecture": self._get_fallback_architecture()
            }
    
    def _extract_project_overview(self, plan: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """Extract a project overview from the plan and context."""
        # Try to get the project overview from context first
        if "project_overview" in context:
            return context["project_overview"]
        
        # Otherwise, generate a summary from the plan
        high_level_tasks = [
            task for task in plan 
            if not task.get("dependencies") and 
               task.get("priority") in ["high", "critical"]
        ][:5]  # Limit to top 5 high-priority tasks
        
        if high_level_tasks:
            return "Project focuses on: " + ", ".join(
                task.get("description", "")
                for task in high_level_tasks
            )
        
        return "Project details not specified"
    
    def _parse_architecture_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into a structured architecture dictionary.
        
        Args:
            response: Raw response from the LLM
            
        Returns:
            Parsed architecture dictionary
        """
        try:
            # Clean the response to extract just the JSON portion
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            
            # Parse the JSON
            architecture = json.loads(json_str)
            
            # Basic validation of required sections
            required_sections = {
                "technology_stack", "system_architecture", "api_design", 
                "data_model", "deployment_strategy"
            }
            
            if not all(section in architecture for section in required_sections):
                logger.warning("Some required architecture sections are missing")
            
            return architecture
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse architecture response: {str(e)}")
            return self._get_fallback_architecture()
    
    def _enrich_architecture(
        self, 
        architecture: Dict[str, Any], 
        plan: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add derived fields or perform validations on the architecture.
        
        Args:
            architecture: The parsed architecture
            plan: Original project plan
            context: Additional context
            
        Returns:
            Enriched architecture dictionary
        """
        # Add metadata
        architecture["metadata"] = {
            "generated_at": str(datetime.datetime.utcnow().isoformat()),
            "plan_tasks_count": len(plan),
            "context_keys": list(context.keys()) if context else []
        }
        
        # Ensure all required sections exist
        for section in ["security_considerations", "scalability_considerations"]:
            if section not in architecture:
                architecture[section] = [f"{section.replace('_', ' ')} not specified"]
        
        return architecture
    
    def _get_fallback_architecture(self) -> Dict[str, Any]:
        """Return a minimal fallback architecture in case of errors."""
        return {
            "technology_stack": {
                "frontend": [{"name": "React", "version": "18.2.0", "justification": "Popular, well-supported frontend framework"}],
                "backend": [{"name": "FastAPI", "version": "0.95.0", "justification": "Modern, fast Python framework for APIs"}],
                "database": [{"name": "PostgreSQL", "version": "15.0", "justification": "Reliable, feature-rich relational database"}],
                "devops": [
                    {"name": "Docker", "version": "20.10", "justification": "Containerization for consistent environments"},
                    {"name": "GitHub Actions", "version": "", "justification": "CI/CD pipeline automation"}
                ]
            },
            "system_architecture": {
                "components": [
                    {
                        "name": "Frontend Application",
                        "description": "User interface built with React",
                        "responsibilities": ["Render UI", "Handle user interactions"],
                        "interactions": ["Communicates with API Gateway"]
                    },
                    {
                        "name": "API Gateway",
                        "description": "Entry point for all client requests",
                        "responsibilities": ["Route requests", "Handle authentication"],
                        "interactions": ["Processes requests from Frontend", "Delegates to microservices"]
                    },
                    {
                        "name": "Database",
                        "description": "PostgreSQL database for persistent storage",
                        "responsibilities": ["Data persistence", "Data retrieval"],
                        "interactions": ["Used by Backend Services"]
                    }
                ],
                "diagram": "[Frontend] <-> [API Gateway] <-> [Backend Services] <-> [Database]"
            },
            "api_design": {
                "endpoints": [
                    {
                        "path": "/api/health",
                        "method": "GET",
                        "description": "Health check endpoint",
                        "request": {},
                        "response": {"status": "ok"}
                    }
                ]
            },
            "data_model": {
                "tables": [
                    {
                        "name": "users",
                        "fields": [
                            {"name": "id", "type": "UUID", "constraints": "PRIMARY KEY"},
                            {"name": "email", "type": "VARCHAR(255)", "constraints": "UNIQUE, NOT NULL"},
                            {"name": "created_at", "type": "TIMESTAMP", "constraints": "DEFAULT CURRENT_TIMESTAMP"}
                        ],
                        "relationships": []
                    }
                ]
            },
            "security_considerations": [
                "Implement HTTPS",
                "Use JWT for authentication",
                "Validate all user inputs",
                "Implement rate limiting"
            ],
            "scalability_considerations": [
                "Use connection pooling for database connections",
                "Implement caching for frequently accessed data",
                "Consider read replicas for read-heavy workloads"
            ],
            "deployment_strategy": "Containerized deployment with Docker and Kubernetes",
            "code_structure": {
                "frontend": ["src/components/", "src/pages/", "src/services/", "src/styles/"],
                "backend": ["app/api/", "app/models/", "app/services/", "app/utils/"]
            },
            "development_environment": [
                "Node.js v18+ for frontend development",
                "Python 3.9+ for backend development",
                "Docker and Docker Compose for containerization",
                "VS Code with recommended extensions"
            ],
            "testing_strategy": [
                "Unit tests for all business logic",
                "Integration tests for API endpoints",
                "End-to-end tests for critical user flows",
                "Automated testing in CI/CD pipeline"
            ],
            "metadata": {
                "fallback": True,
                "generated_at": str(datetime.datetime.utcnow().isoformat())
            }
        }
