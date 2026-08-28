import json
import logging
import smtplib
import threading
from datetime import datetime, timezone
from email.mime.text import MIMEText

import anthropic
import openai

from config import settings
from constants import (
    ANTHROPIC_MODEL,
    EMBEDDING_COST_PER_MILLION_TOKENS,
    EMBEDDING_MODEL,
    LLM_MODEL_COST_PER_MILLION_TOKENS,
)
from exceptions import LLMUnreachableError

logger = logging.getLogger(__name__)

# In-process, per-UTC-day call counters — resets on day rollover or process
# restart. Not shared across worker processes; meant for log visibility,
# not as a source of truth (llm_usage table is authoritative for that).
_daily_call_counts: dict[str, int] = {}
_daily_call_count_date = None
_daily_call_count_lock = threading.Lock()


def _record_daily_call(provider: str) -> int:
    """Increment and return today's call count for the given provider."""
    global _daily_call_count_date
    today = datetime.now(timezone.utc).date()
    with _daily_call_count_lock:
        if _daily_call_count_date != today:
            _daily_call_counts.clear()
            _daily_call_count_date = today
        _daily_call_counts[provider] = _daily_call_counts.get(provider, 0) + 1
        return _daily_call_counts[provider]


def call_llm(
    prompt: str,
    timeout: int | None = None,
    return_usage: bool = False,
    model: str = ANTHROPIC_MODEL,
) -> dict | tuple[dict, dict]:
    """Call the LLM and return the parsed JSON response as a dict.

    Strips markdown code fences (```json / ```) before parsing.
    Raises LLMUnreachableError on failure, timeout, or invalid JSON.
    Default timeout from config. Defaults to ANTHROPIC_MODEL — pass model=
    to route a call to a different model (rates looked up from
    LLM_MODEL_COST_PER_MILLION_TOKENS).

    If return_usage is True, returns (result, usage) where usage is
    {"input_tokens": int, "output_tokens": int, "model": str}.
    """
    effective_timeout = timeout if timeout is not None else settings.LLM_TIMEOUT_SECONDS
    call_number_today = _record_daily_call("anthropic")
    logger.info(
        "LLM call starting — provider=anthropic model=%s prompt_chars=%d timeout=%ds "
        "calls_today=%d",
        model,
        len(prompt),
        effective_timeout,
        call_number_today,
    )
    client = anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=effective_timeout,
    )
    try:
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
            system="Return only valid JSON. Do not include any explanation or prose outside the JSON object.",
        )
    except anthropic.APITimeoutError as exc:
        logger.error("LLM call timed out — provider=anthropic model=%s", model)
        raise LLMUnreachableError("LLM request timed out") from exc
    except anthropic.APIError as exc:
        logger.error(
            "LLM call failed — provider=anthropic model=%s error=%s",
            model,
            exc,
        )
        raise LLMUnreachableError(f"LLM API error: {exc}") from exc

    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    input_cost_rate, output_cost_rate = LLM_MODEL_COST_PER_MILLION_TOKENS[model]
    cost_usd = (
        input_tokens / 1_000_000 * input_cost_rate
        + output_tokens / 1_000_000 * output_cost_rate
    )
    logger.info(
        "LLM call succeeded — provider=anthropic model=%s input_tokens=%d "
        "output_tokens=%d cost_usd=%.6f",
        model,
        input_tokens,
        output_tokens,
        cost_usd,
    )

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
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(
            "LLM returned invalid JSON — provider=anthropic model=%s error=%s",
            model,
            exc,
        )
        raise LLMUnreachableError(f"LLM returned invalid JSON: {exc}") from exc

    if not return_usage:
        return result

    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model": model,
    }
    return result, usage


def embed_text(text: str) -> list[float]:
    """Embed a text string using text-embedding-3-small via the OpenAI SDK.

    Raises LLMUnreachableError on failure.
    """
    call_number_today = _record_daily_call("openai")
    logger.info(
        "Embedding call starting — provider=openai model=%s calls_today=%d",
        EMBEDDING_MODEL,
        call_number_today,
    )
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        total_tokens = response.usage.total_tokens
        cost_usd = total_tokens / 1_000_000 * EMBEDDING_COST_PER_MILLION_TOKENS
        logger.info(
            "Embedding call succeeded — provider=openai model=%s total_tokens=%d "
            "cost_usd=%.6f",
            EMBEDDING_MODEL,
            total_tokens,
            cost_usd,
        )
        return response.data[0].embedding
    except Exception as exc:
        logger.error(
            "Embedding call failed — provider=openai model=%s error=%s",
            EMBEDDING_MODEL,
            exc,
        )
        raise LLMUnreachableError(f"Failed to embed text: {exc}") from exc


def send_alert_email(subject: str, body: str) -> None:
    """Send a plain-text alert email via SMTP.

    No-ops with a warning log if SMTP isn't configured — never raises,
    since a failed alert-delivery attempt shouldn't ever break the caller.
    """
    if not (settings.SMTP_HOST and settings.SMTP_USERNAME and settings.ALERT_EMAIL_TO):
        logger.warning(
            "send_alert_email skipped — SMTP not configured (SMTP_HOST/SMTP_USERNAME/ALERT_EMAIL_TO)"
        )
        return

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = settings.ALERT_EMAIL_TO

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(
                settings.SMTP_FROM_EMAIL, [settings.ALERT_EMAIL_TO], message.as_string()
            )
        logger.info(
            "Alert email sent — to=%s subject=%r", settings.ALERT_EMAIL_TO, subject
        )
    except Exception as exc:
        logger.error("Failed to send alert email: %s", exc, exc_info=True)
