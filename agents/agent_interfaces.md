# Agent Interfaces & Communication Flow

## Overview
This document describes the interface (methods, inputs, outputs) for each agent and the data flow between them.

---

## 1. ClarificationAgent
- **Method:** `clarify(user_input: str, context: dict = None) -> str`
- **Input:** Raw user input, optional context
- **Output:** Clarified, structured requirements (str)
- **Notes:** Uses LLM to detect ambiguity, ask follow-ups, and clarify intent.

## 2. PlannerAgent
- **Method:** `plan(clarified_requirements: str, context: dict = None) -> list`
- **Input:** Clarified requirements (str), optional context
- **Output:** List of steps/tasks (list of str)
- **Notes:** Uses LLM to decompose requirements into actionable steps.

## 3. DevArchitectAgent
- **Method:** `design_architecture(plan: list, context: dict = None) -> dict`
- **Input:** Plan (list of steps), optional context
- **Output:** Architecture details (dict)
- **Notes:** Uses LLM to suggest architecture, tech stack, and code scaffolding.

## 4. ClientPersonaAgent
- **Method:** `provide_feedback(architecture: dict, context: dict = None) -> str`
- **Input:** Architecture (dict), optional context
- **Output:** Feedback or new requirements (str)
- **Notes:** Uses LLM to simulate client feedback or constraints.

---

## Data Flow
1. **User Input** → ClarificationAgent
2. **Clarified Requirements** → PlannerAgent
3. **Plan** → DevArchitectAgent
4. **Architecture** → ClientPersonaAgent
5. **Feedback** → (loop or display)

Agents are orchestrated via LangGraph, passing outputs as inputs to the next agent in the pipeline. 