import streamlit as st
import os
from agents import ClarificationAgent, PlannerAgent, DevArchitectAgent, ClientPersonaAgent

st.title("AI Strategy Assistant")

user_input = st.text_area("Enter your project idea or request:")

if st.button("Run Pipeline"):
    if not os.getenv("OPENROUTER_API_KEY"):
        st.error("OPENROUTER_API_KEY environment variable not set. Please set it to use the LLM.")
    else:
        clarifier = ClarificationAgent()
        planner = PlannerAgent()
        architect = DevArchitectAgent()
        client = ClientPersonaAgent()

        with st.spinner("Clarifying your request..."):
            clarified = clarifier.clarify(user_input)
        st.markdown(f"**Clarified:** {clarified}")

        plan = planner.plan(clarified)
        st.markdown(f"**Plan:** {plan}")

        architecture = architect.design_architecture(plan)
        st.markdown(f"**Architecture:** {architecture}")

        feedback = client.provide_feedback(architecture)
        st.markdown(f"**Client Feedback:** {feedback}")
