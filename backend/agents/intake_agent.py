"""Classifies an employee request without making a clinical decision."""

from __future__ import annotations

from crewai import Agent, LLM

from backend.agents import SAFETY_RULES


def create_intake_agent(llm: LLM) -> Agent:
    return Agent(
        role="Intake Agent",
        goal=(
            "Classify the employee request by type, category, and priority, "
            "and list missing operational details."
        ),
        backstory=(
            "You are the intake step for EstetikAI employees. "
            "You sort the request so later agents know what to look up. "
            "You do not answer the visitor and you do not make a medical decision.\n"
            f"{SAFETY_RULES}"
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
