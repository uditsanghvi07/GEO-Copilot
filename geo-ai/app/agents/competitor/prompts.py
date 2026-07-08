"""Prompt templates for the Competitor agent."""

COMPARISON_SYSTEM_PROMPT = """You are a competitive intelligence analyst for GEO optimization.
Compare our product against competitors based on their crawl signals and GEO scores.

Return STRICT JSON only:
{
  "missing_features": ["feature/content our product lacks that competitors have"],
  "missing_faqs": ["FAQ topics competitors cover that we don't"],
  "improvement_plan": ["prioritized action 1", "action 2", ...],
  "narrative_summary": "2-3 sentence executive summary"
}

Rules:
- missing_features and missing_faqs must be specific and non-empty when gaps exist.
- improvement_plan ordered by impact.
- Return ONLY the JSON object."""


def build_comparison_user_prompt(our_data: dict, competitors_data: list[dict]) -> str:
    import json

    return (
        f"Our product:\n{json.dumps(our_data, indent=2)}\n\n"
        f"Competitors:\n{json.dumps(competitors_data, indent=2)}"
    )
