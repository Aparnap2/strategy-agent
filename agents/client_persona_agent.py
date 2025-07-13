import os
import json
from typing import Dict, List, Optional, Any, Literal
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
import logging
from enum import Enum
import random
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonaType(str, Enum):
    """Different types of client personas that can provide feedback."""
    TECHNICAL_CTO = "cto"
    BUSINESS_OWNER = "business_owner"
    PRODUCT_MANAGER = "product_manager"
    END_USER = "end_user"
    SECURITY_EXPERT = "security_expert"
    COST_CONSCIOUS = "cost_conscious"
    INNOVATION_SEEKER = "innovation_seeker"

class ClientPersonaAgent:
    """
    Simulates client or stakeholder feedback on technical architecture.
    
    This agent takes the technical architecture from the DevArchitectAgent and provides
    simulated feedback based on different client personas, such as CTO, business owner,
    or end-user perspectives.
    """
    
    def __init__(
        self, 
        persona_type: Optional[PersonaType] = None,
        prompt_template: Optional[PromptTemplate] = None
    ):
        """
        Initialize the ClientPersonaAgent.
        
        Args:
            persona_type: Type of persona to simulate. If None, a random persona is selected.
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
            model="openai/gpt-3.5-turbo",  # Default model, can be overridden
            temperature=0.7,  # Higher temperature for more varied feedback
            max_tokens=1000
        )
        
        # Set persona type or select a random one if not specified
        self.persona_type = persona_type or random.choice(list(PersonaType))
        
        # Set up the prompt template
        self.prompt_template = prompt_template or self._get_default_prompt_template()
    
    def _get_persona_description(self) -> Dict[str, str]:
        """Get the description and priorities for the current persona type."""
        persona_descriptions = {
            PersonaType.TECHNICAL_CTO: {
                "name": "CTO",
                "description": "A technical leader focused on system scalability, maintainability, and technical excellence.",
                "priorities": ["scalability", "technical debt", "team productivity", "technology choices"]
            },
            PersonaType.BUSINESS_OWNER: {
                "name": "Business Owner",
                "description": "A non-technical business owner focused on ROI, time-to-market, and business value.",
                "priorities": ["cost", "time-to-market", "business value", "competitive advantage"]
            },
            PersonaType.PRODUCT_MANAGER: {
                "name": "Product Manager",
                "description": "Focused on user experience, feature set, and product roadmap alignment.",
                "priorities": ["user experience", "feature set", "roadmap alignment", "market fit"]
            },
            PersonaType.END_USER: {
                "name": "End User",
                "description": "A typical user of the application, focused on usability and functionality.",
                "priorities": ["ease of use", "performance", "features", "reliability"]
            },
            PersonaType.SECURITY_EXPERT: {
                "name": "Security Expert",
                "description": "Focused on security, compliance, and data protection aspects.",
                "priorities": ["security", "compliance", "data protection", "risk mitigation"]
            },
            PersonaType.COST_CONSCIOUS: {
                "name": "Cost-Conscious Stakeholder",
                "description": "Primarily concerned with budget constraints and cost optimization.",
                "priorities": ["cost efficiency", "ROI", "budget constraints", "resource optimization"]
            },
            PersonaType.INNOVATION_SEEKER: {
                "name": "Innovation Seeker",
                "description": "Focused on cutting-edge technologies and innovative solutions.",
                "priorities": ["innovation", "modern tech stack", "competitive edge", "future-proofing"]
            }
        }
        
        return persona_descriptions.get(self.persona_type, {
            "name": "General Stakeholder",
            "description": "A general stakeholder with balanced concerns.",
            "priorities": ["overall project success"]
        })
    
    def _get_default_prompt_template(self) -> PromptTemplate:
        """Return the default prompt template for client feedback."""
        template = """You are simulating feedback from a {persona_name} perspective on a technical architecture.

Persona Description:
{persona_description}

Key Priorities:
{priorities}

Project Overview:
{project_overview}

Technical Architecture:
{architecture}

Your task is to provide constructive feedback on this architecture from your persona's perspective. Consider:
1. How well does this architecture align with your priorities?
2. What are the potential risks or concerns?
3. What improvements or alternatives would you suggest?
4. Any specific requirements or constraints to consider?

Provide your feedback in the following JSON structure:
{{
  "feedback_summary": "Brief overall impression",
  "strengths": ["..."],
  "concerns": ["..."],
  "suggestions": ["..."],
  "additional_requirements": ["..."],
  "overall_rating": 1-5,  // 1=Poor, 5=Excellent
  "confidence_in_rating": 1-5,  // 1=Low, 5=High
  "follow_up_questions": ["..."]
}}

{persona_name}'s Feedback:"""
        return PromptTemplate(
            input_variables=["persona_name", "persona_description", "priorities", "project_overview", "architecture"],
            template=template
        )
    
    def provide_feedback(
        self, 
        architecture: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Provide feedback on the technical architecture from the configured persona's perspective.
        
        Args:
            architecture: Technical architecture from DevArchitectAgent
            context: Optional dictionary containing additional context
            
        Returns:
            Dictionary containing structured feedback
        """
        if not architecture or not isinstance(architecture, dict):
            raise ValueError("A valid technical architecture must be provided")
            
        try:
            # Prepare context for the prompt
            context = context or {}
            persona_info = self._get_persona_description()
            
            # Format the prompt using the template
            prompt = self.prompt_template.format(
                persona_name=persona_info["name"],
                persona_description=persona_info["description"],
                priorities="\n- " + "\n- ".join(persona_info["priorities"]),
                project_overview=context.get("project_overview", "Not specified"),
                architecture=json.dumps(architecture, indent=2)
            )
            
            # Get the LLM response using ChatOpenAI
            response = self.llm.invoke([
                SystemMessage(content=f"You are a {persona_info['name']} providing feedback on a technical architecture."),
                HumanMessage(content=prompt)
            ])
            
            # Parse the response into a structured format
            feedback = self._parse_feedback_response(response.content)
            
            # Add metadata
            feedback["metadata"] = {
                "persona_type": self.persona_type.value,
                "persona_name": persona_info["name"],
                "generated_at": str(datetime.utcnow().isoformat())
            }
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error in ClientPersonaAgent: {str(e)}", exc_info=True)
            return self._get_fallback_feedback(architecture, str(e))
    
    def _parse_feedback_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into a structured feedback dictionary.
        
        Args:
            response: Raw response from the LLM
            
        Returns:
            Parsed feedback dictionary
        """
        try:
            # Clean the response to extract just the JSON portion
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON object found in response")
                
            json_str = response[json_start:json_end]
            
            # Parse the JSON
            feedback = json.loads(json_str)
            
            # Ensure all required fields exist
            required_fields = ["feedback_summary", "strengths", "concerns", "suggestions"]
            for field in required_fields:
                if field not in feedback:
                    feedback[field] = [f"No {field.replace('_', ' ')} provided"]
            
            return feedback
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse feedback response: {str(e)}")
            return self._get_fallback_feedback({}, "Failed to parse feedback response")
    
    def _get_fallback_feedback(self, architecture: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Return a fallback feedback in case of errors."""
        return {
            "feedback_summary": "Unable to generate detailed feedback due to an error.",
            "strengths": ["Unable to assess strengths"],
            "concerns": [f"Error generating feedback: {error}"],
            "suggestions": ["Please try again or provide more context about the project."],
            "additional_requirements": [],
            "overall_rating": 3,
            "confidence_in_rating": 1,
            "follow_up_questions": [
                "Can you provide more details about the project goals?",
                "What are the main technical constraints we should consider?"
            ],
            "metadata": {
                "fallback": True,
                "error": error,
                "generated_at": str(datetime.utcnow().isoformat())
            }
        }
    
    def analyze_multiple_feedbacks(
        self, 
        feedbacks: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze and consolidate feedback from multiple personas.
        
        Args:
            feedbacks: List of feedback dictionaries from different personas
            context: Optional additional context
            
        Returns:
            Consolidated analysis of all feedbacks
        """
        if not feedbacks or not isinstance(feedbacks, list):
            raise ValueError("A list of feedbacks must be provided")
            
        try:
            # Prepare the prompt for analysis
            analysis_prompt = """You are analyzing feedback from multiple stakeholders on a technical architecture.
            
Project Overview:
{project_overview}

Feedback from Stakeholders:
{feedbacks}

Please provide a consolidated analysis that:
1. Identifies common themes and patterns
2. Highlights any conflicting feedback
3. Prioritizes the most critical issues
4. Suggests a balanced way forward

Format your response as a JSON object with the following structure:
{{
  "summary": "Overall summary of the feedback",
  "key_insights": ["..."],
  "top_concerns": ["..."],
  "recommended_actions": ["..."],
  "consensus_areas": ["..."],
  "conflicting_opinions": ["..."]
}}

Analysis:"""
            
            # Format the feedbacks for the prompt
            formatted_feedbacks = []
            for i, feedback in enumerate(feedbacks, 1):
                persona = feedback.get("metadata", {}).get("persona_name", f"Stakeholder {i}")
                summary = feedback.get("feedback_summary", "No summary provided")
                formatted_feedbacks.append(f"{persona}: {summary}")
            
            # Get the analysis
            analysis_response = self.llm.invoke([
                SystemMessage(content="You are analyzing feedback from multiple stakeholders on a technical architecture."),
                HumanMessage(content=analysis_prompt.format(
                    project_overview=context.get("project_overview", "Not specified"),
                    feedbacks="\n\n".join(formatted_feedbacks)
                ))
            ])
            
            # Parse the analysis response
            analysis = json.loads(analysis_response.content[analysis_response.content.find('{'):analysis_response.content.rfind('}')+1])
            
            # Add metadata
            analysis["metadata"] = {
                "feedbacks_analyzed": len(feedbacks),
                "personas_represented": list(set(
                    f.get("metadata", {}).get("persona_name", "Unknown") 
                    for f in feedbacks
                )),
                "generated_at": str(datetime.utcnow().isoformat())
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing multiple feedbacks: {str(e)}", exc_info=True)
            return {
                "error": "Failed to analyze feedbacks",
                "details": str(e),
                "metadata": {
                    "fallback": True,
                    "generated_at": str(datetime.utcnow().isoformat())
                }
            }