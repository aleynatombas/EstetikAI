"""Retrieves company knowledge through the AnythingLLM tool."""

from __future__ import annotations

from crewai import Agent, LLM

from backend.agents import SAFETY_RULES
from backend.tools.anythingllm_tool import AnythingLLMEmployeeKnowledgeTool


def create_knowledge_agent(llm: LLM, tool: AnythingLLMEmployeeKnowledgeTool) -> Agent:
    return Agent(
        role="Knowledge Agent",
        goal=(
            "Retrieve what the Employee Knowledge workspace actually contains "
            "and pass those excerpts on without adding facts."
        ),
        backstory=(
            "You are the only agent allowed to consult company documents. "
            "AnythingLLM is the knowledge layer. You call the employee knowledge tool, "
            "then report its excerpts and its not_found list. "
            "If the tool has no excerpt, you say the knowledge base did not contain it.\n"
            f"{SAFETY_RULES}"
        ),
        llm=llm,
        tools=[tool],
        verbose=True,
        allow_delegation=False,
        max_iter=6,
    )
