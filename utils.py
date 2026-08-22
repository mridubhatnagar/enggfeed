import json

import anthropic
import openai

from config import settings
from exceptions import LLMUnreachableError


def call_llm(prompt: str, timeout: int | None = None) -> dict:
    """Call the LLM and return the parsed JSON response as a dict.

    Strips markdown code fences (```json / ```) before parsing.
    Raises LLMUnreachableError on failure, timeout, or invalid JSON.
    Default timeout from config.
    """
    effective_timeout = timeout if timeout is not None else settings.LLM_TIMEOUT_SECONDS
    client = anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=effective_timeout,
    )
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
            system="Return only valid JSON. Do not include any explanation or prose outside the JSON object.",
        )
    except anthropic.APITimeoutError as exc:
        raise LLMUnreachableError("LLM request timed out") from exc
    except anthropic.APIError as exc:
        raise LLMUnreachableError(f"LLM API error: {exc}") from exc

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Drop the opening fence line (```json or ```)
        lines = lines[1:]
        # Drop the closing fence if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMUnreachableError(f"LLM returned invalid JSON: {exc}") from exc


def embed_text(text: str) -> list[float]:
    """Embed a text string using text-embedding-3-small via the OpenAI SDK.

    Raises LLMUnreachableError on failure.
    """
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding
    except Exception as exc:
        raise LLMUnreachableError(f"Failed to embed text: {exc}") from exc
