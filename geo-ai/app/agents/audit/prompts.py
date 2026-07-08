"""Prompt templates for the Audit agent."""

ACTION_PLAN_SYSTEM_PROMPT = """You are a GEO (Generative Engine Optimization) consultant.
Given a product's GEO score breakdown and review intelligence summary, produce a
prioritized action plan to move the score toward 90+.

Return STRICT JSON only:
{
  "action_plan": [
    {
      "step": "concrete action description",
      "component": "which score component this improves (e.g. faq_presence)",
      "estimated_point_impact": <float 0-20>
    }
  ]
}

Rules:
- Order steps by highest estimated impact first.
- Each step must be specific and actionable, not generic advice.
- estimated_point_impact should be realistic given the current breakdown.
- Return ONLY the JSON object."""


def build_action_plan_user_prompt(
    score_breakdown: dict, review_summary: dict | None, product_name: str
) -> str:
    import json

    parts = [
        f"Product: {product_name}",
        f"GEO Score Breakdown:\n{json.dumps(score_breakdown, indent=2)}",
    ]
    if review_summary:
        parts.append(f"Review Intelligence Summary:\n{json.dumps(review_summary, indent=2)}")
    else:
        parts.append("Review Intelligence Summary: not available yet.")
    return "\n\n".join(parts)
