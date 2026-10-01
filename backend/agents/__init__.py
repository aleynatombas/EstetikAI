"""Shared limits for every agent in the employee pipeline."""

SAFETY_RULES = """
Clinical and commercial limits:
- Do not diagnose.
- Do not recommend a personal treatment.
- Do not decide medical suitability.
- Do not guarantee a result.
- Do not invent a price, appointment date, appointment availability, doctor name, staff name, department name, package contents, accommodation, or transfer.
- Do not describe an action as completed unless the supplied context says it already happened.
- Company facts may come only from the AnythingLLM Employee Knowledge tool result.
- If a needed fact is missing or listed as not_found, require human confirmation instead of filling the gap.
""".strip()
