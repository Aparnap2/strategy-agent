import os
from typing import Dict, Optional, Any
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
import logging

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClarificationAgent:
    """
    Agent responsible for clarifying ambiguous or incomplete user requests.
    
    This agent interacts with the user to gather all necessary information
    required to proceed with the strategy planning process.
    """
    
    def __init__(self, prompt_template: Optional[PromptTemplate] = None):
        """
        Initialize the ClarificationAgent.
        
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
            model="tngtech/deepseek-r1t2-chimera:free",  # Using a specific model that works with OpenRouter
            temperature=0.7,
            max_tokens=1000
        )
        
        # Set up the prompt template
        self.prompt_template = prompt_template or self._get_default_prompt_template()
    
    def _get_default_prompt_template(self) -> PromptTemplate:
        """Return the default prompt template for clarification."""
        template = """You are an AI Strategy Assistant specializing in helping users define clear project requirements.

Current conversation context:
{context}

User's initial input:
{user_input}

Your task is to ask clarifying questions to gather all necessary information. Consider the following aspects:
1. Project goals and objectives
2. Target audience and user needs
3. Technical constraints or requirements
4. Timeline and resources
5. Success criteria

Ask up to 3 specific, targeted questions that would help clarify the requirements. Be concise but thorough.

Clarifying questions:"""
        return PromptTemplate(
            input_variables=["user_input", "context"],
            template=template
        )
    
    def clarify(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process the user input and return clarifying questions or refined requirements.
        
        Args:
            user_input: The raw input from the user
            context: Optional dictionary containing conversation context
            
        Returns:
            str: Clarified requirements or follow-up questions
        """
        if not user_input or not isinstance(user_input, str):
            return "Please provide a valid input to proceed."
            
        try:
            # Prepare context for the prompt
            context = context or {}
            
            # Get the prompt
            prompt = self.prompt_template.format(
                user_input=user_input,
                context=context.get("conversation_history", "No previous context")
            )
            
            # Get the LLM response
            response = self.llm.invoke([
                SystemMessage(content="You are a helpful assistant that clarifies ambiguous or incomplete user requests."),
                HumanMessage(content=prompt)
            ])
            
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error in ClarificationAgent: {str(e)}", exc_info=True)
            return "I encountered an error while processing your request. Please try again with more specific details."
    
    def process_clarification_response(self, user_response: str) -> Dict[str, Any]:
        """
        Process the user's response to clarification questions.
        
        Args:
            user_response: The user's response to clarification questions
            
        Returns:
            Dict containing the processed information and next steps
        """
        # This method can be enhanced to extract structured information
        # from the user's response
        return {
            "status": "success",
            "message": "Clarification received",
            "next_step": "proceed_to_planning"
        }