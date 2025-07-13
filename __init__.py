import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Log loaded environment variables (optional, for debugging)
if os.getenv('DEBUG', '').lower() in ('true', '1', 't'):
    print("Loaded environment variables:")
    for key, value in os.environ.items():
        if key.startswith(('OPENROUTER_', 'DEBUG')):
            print(f"{key}: {'*' * 8 if 'KEY' in key or 'SECRET' in key else value}")

from .agents import (
    ClarificationAgent,
    PlannerAgent,
    DevArchitectAgent,
    ClientPersonaAgent
)
from .agent_orchestrator import AgentOrchestrator

__all__ = [
    'ClarificationAgent',
    'PlannerAgent',
    'DevArchitectAgent',
    'ClientPersonaAgent',
    'AgentOrchestrator'
]
