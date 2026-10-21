import json
from groq import Groq
from config import settings

client = Groq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """
You are GeoVision AI, an expert satellite remote-sensing analyst.

Explain supplied satellite analysis results in simple, clear,
practical language.

Return your entire response as one valid JSON object.
Do not return Markdown or text outside the JSON object.

The JSON should contain these fields:
{
  "plain_language_summary": "string",
  "key_findings": ["string"],
  "why_it_matters": "string",
  "recommended_actions": ["string"],
  "limitations": ["string"],
  "interpretation": "string",
  "technical_interpretation": "string"
}

Rules:
1. Base every finding on the supplied statistics and metadata.
2. Never invent measurements, locations, trends, causes, or risks.
3. Distinguish measured observations from possible explanations.
4. Explain uncertainty and relevant data limitations.
5. For NDVI, do not automatically equate low values with unhealthy
   vegetation.
6. For water indices and flood mapping, distinguish water signals
   from confirmed flooding.
7. For urban heat, distinguish land-surface temperature from air
   temperature.
8. Recommend practical next steps only when justified.
9. If evidence is insufficient, say so.
10. Use short sentences and familiar language.
"""


def get_llm_response(
    user_message: str,
    history: list[dict] | None = None,
    retry_error: str | None = None,
) -> dict | None:
    """Generate a JSON analysis report using Groq."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    for turn in (history or [])[-5:]:
        if turn.get("role") in {"user", "assistant"}:
            messages.append(turn)

    if retry_error:
        user_message += (
            "\n\nYour previous response failed with this error:\n"
            f"{retry_error}\n"
            "Correct the error and return one valid JSON object."
        )

    messages.append({
        "role": "user",
        "content": (
            "Respond in JSON format. Analyze the following:\n"
            + user_message
        ),
    })

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=2000,
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)

        if isinstance(result, dict):
            return result

        print("Groq returned JSON that was not an object.")
        return None

    except Exception as e:
        error_str = str(e)
        print(f"Groq error: {error_str}")

        if "rate_limit" in error_str.lower() or "429" in error_str:
            return _gemini_fallback(messages)

        return None


def _gemini_fallback(messages: list) -> dict | None:
    """Fallback to Gemini when Groq is rate limited."""

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = (
            "Return one valid JSON object. Do not use Markdown.\n\n"
            + "\n".join(
                f"{m['role'].upper()}: {m['content']}"
                for m in messages
            )
        )

        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json"
            },
        )

        result = json.loads(response.text)
        return result if isinstance(result, dict) else None

    except Exception as e:
        print(f"Gemini fallback error: {e}")
        return None
