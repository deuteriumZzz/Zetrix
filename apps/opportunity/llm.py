from __future__ import annotations

import json
import logging

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a research assistant producing structured data about a \
country's business/investment climate for entrepreneurs and individuals looking to \
buy property or start a business there. You will be given the country name and, when \
available, datapoints from established indexes as grounding context.

Rules:
- Ground every claim in the provided index datapoints where possible; only use your \
own knowledge to fill gaps, and mark those fields with lower confidence.
- Cite a source (index name or your own knowledge) for each major claim in the \
`sources` list.
- If you are not confident about a field, still provide your best estimate but lower \
the overall `confidence_score`.
- Respond with ONLY a single JSON object matching the schema below — no prose, no \
markdown fences.

Schema:
{
  "foreign_land_ownership_summary": str, "foreign_land_ownership_score": int (0-100),
  "business_registration_summary": str, "business_registration_days_estimate": int|null,
  "business_registration_cost_usd_estimate": float|null, "business_registration_score": int (0-100),
  "tax_overview_summary": str, "corporate_tax_rate_pct": float|null,
  "personal_income_tax_top_rate_pct": float|null,
  "investor_visa_summary": str, "has_digital_nomad_visa": bool,
  "has_investor_residency_program": bool,
  "overall_complexity_score": int (0-100, higher = friendlier to foreign investors),
  "confidence_score": int (0-100),
  "sources": [{"label": str, "url": str|null, "excerpt": str}]
}"""


class GroqClient:
    """Thin wrapper around Groq's OpenAI-compatible chat completions API
    (free tier — chosen over DeepSeek since request volume here is low)."""

    def __init__(self) -> None:
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not configured.")
        self._client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_API_BASE_URL,
        )

    def generate_business_climate(self, country_name: str, grounding: list[dict]) -> dict:
        """Returns the parsed JSON dict described in `_SYSTEM_PROMPT`'s schema."""
        grounding_text = json.dumps(grounding, indent=2) if grounding else "No index data available."
        response = self._client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Country: {country_name}\n\nGrounding data:\n{grounding_text}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Groq returned non-JSON content for {country_name}: {content[:500]}")
            raise
