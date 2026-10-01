"""Turns verified knowledge into the employee's next operational steps."""

from __future__ import annotations

from crewai import Agent, LLM

from backend.agents import SAFETY_RULES


def create_operations_agent(llm: LLM) -> Agent:
    return Agent(
        role="Operations Agent",
        goal=(
            "Write the next operational actions for the employee using only "
            "the intake classification and the verified knowledge excerpts."
        ),
        backstory=(
            "You help an EstetikAI employee decide the next safe operational step. "
            "You route and record. You do not quote commercial terms or clinical decisions "
            "that were not present in the knowledge excerpts, and you do not claim that "
            "a booking, payment, or medical review already happened.\n"
            f"{SAFETY_RULES}"
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
