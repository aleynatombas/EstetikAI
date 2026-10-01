"""Sequential tasks for one employee request."""

from typing import Any

from crewai import Agent, Task
from crewai.tasks.task_output import TaskOutput

from backend.models.schemas import FinalResponse, IntakeResult, KnowledgeResult, OperationsResult
from backend.tools.anythingllm_tool import AnythingLLMEmployeeKnowledgeTool, get_last_retrieval


def _knowledge_guardrail(result: TaskOutput) -> tuple[bool, Any]:
    retrieval = get_last_retrieval()
    if retrieval is None or not retrieval.question.strip():
        return (
            False,
            "Call the anythingllm_employee_knowledge tool once before answering. "
            "Do not state company facts from memory.",
        )
    return True, result.raw


def create_tasks(
    intake_agent: Agent,
    knowledge_agent: Agent,
    operations_agent: Agent,
    compliance_agent: Agent,
    knowledge_tool: AnythingLLMEmployeeKnowledgeTool,
) -> list[Task]:
    intake_task = Task(
        name="intake",
        description=(
            "An EstetikAI employee submitted this request:\n\n"
            "{employee_request}\n\n"
            "Classify it in Turkish. request_type examples: Ziyaretçi talebi, "
            "Müşteri takibi, İç operasyon, Uluslararası operasyon, Eskalasyon, "
            "Politika sorusu, or Bilinmiyor. category examples: Saç ekimi, Diş, "
            "Plastik cerrahi, Danışma, Talep yönetimi, Operasyon, Politika, or Belirtilmedi. "
            "Priority must stay exactly Low, Medium, or High.\n\n"
            "Write missing_information in Turkish. "
            "Priority High is for an operational emergency, a complaint, or a request to "
            "bypass policy. A routine question about price, suitability, or a date is Medium, "
            "not a medical judgment. List missing operational details such as contact channel "
            "or whether the person is an existing lead. Do not request or interpret clinical history."
        ),
        expected_output=(
            "JSON with request_type, category, priority, and missing_information. "
            "No price, date, doctor, or medical suitability."
        ),
        agent=intake_agent,
        output_pydantic=IntakeResult,
    )

    knowledge_task = Task(
        name="knowledge",
        description=(
            "Look up the employee request in AnythingLLM Employee Knowledge.\n\n"
            "Original request:\n{employee_request}\n\n"
            "Call the anythingllm_employee_knowledge tool exactly once. "
            "The question must include the visitor need and the intake category. "
            "Copy excerpt text into verified_information. Copy the tool's not_found "
            "values. Put excerpt source titles into sources. "
            "If the tool did not return a fact, leave it out. Do not use public knowledge "
            "or the Public Knowledge workspace."
        ),
        expected_output=(
            "JSON with verified_information copied from the tool, not_found, and sources. "
            "No invented clinic facts."
        ),
        agent=knowledge_agent,
        context=[intake_task],
        tools=[knowledge_tool],
        output_pydantic=KnowledgeResult,
        guardrail=_knowledge_guardrail,
        guardrail_max_retries=2,
    )

    operations_task = Task(
        name="operations",
        description=(
            "Write the employee's next operational actions for this request:\n\n"
            "{employee_request}\n\n"
            "Use only the intake result and the knowledge excerpts. "
            "Actions may record, classify, and route the request to a human. "
            "Write every recommended_actions item and every human_confirmation_needed item in Turkish. "
            "Do not name a doctor, employee, or department. "
            "Do not state a price, package, appointment date, availability, lodging, or transfer. "
            "Do not decide medical suitability. "
            "Do not say a booking, payment, message, or clinical review has already been done. "
            "Put every dynamic gap into human_confirmation_needed."
        ),
        expected_output=(
            "JSON with recommended_actions and human_confirmation_needed. "
            "Actions are instructions, not claims that work is finished."
        ),
        agent=operations_agent,
        context=[intake_task, knowledge_task],
        output_pydantic=OperationsResult,
    )

    compliance_task = Task(
        name="compliance",
        description=(
            "Review the intake, knowledge, and operations outputs for this request:\n\n"
            "{employee_request}\n\n"
            "Produce the final employee response. Keep request_type, category, and priority "
            "from intake. verified_information may only repeat knowledge excerpts. "
            "Drop any recommended action that adds a price, appointment, named person, "
            "department, package, lodging, transfer, diagnosis, treatment, suitability decision, "
            "or result guarantee. Keep missing_information from intake.\n\n"
            "Set escalation_required to true only when the employee request asks for a price, "
            "appointment date, medical suitability, named person, package, lodging, or transfer "
            "that the knowledge tool did not verify. A greeting or general information note "
            "does not require escalation. "
            "Write reason, missing_information, and recommended_actions in Turkish. "
            "Do not add a fact in order to make the answer more complete."
        ),
        expected_output=(
            "JSON with request_type, category, priority, verified_information, "
            "missing_information, recommended_actions, escalation_required, and reason."
        ),
        agent=compliance_agent,
        context=[intake_task, knowledge_task, operations_task],
        output_pydantic=FinalResponse,
    )

    return [intake_task, knowledge_task, operations_task, compliance_task]
