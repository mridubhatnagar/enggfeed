import json

import boto3
import botocore.exceptions
import openai
from botocore.config import Config as BotoConfig

from config import settings
from constants import LLM_MODEL
from exceptions import LLMUnreachableError


def call_llm(
    prompt: str, timeout: int | None = None, return_usage: bool = False
) -> dict | tuple[dict, dict]:
    """Call the LLM via AWS Bedrock's Converse API and return the parsed JSON
    response as a dict.

    Using the Converse API (rather than a provider-specific SDK) keeps this
    provider-agnostic — switching models, including back to Anthropic once
    Bedrock access is granted, is just a change to LLM_MODEL in constants.py,
    not a rewrite of this function.

    Strips markdown code fences (```json / ```) before parsing.
    Raises LLMUnreachableError on failure, timeout, or invalid JSON.
    Default timeout from config.

    If return_usage is True, returns (result, usage) where usage is
    {"input_tokens": int, "output_tokens": int}.
    """
    effective_timeout = timeout if timeout is not None else settings.LLM_TIMEOUT_SECONDS
    client = boto3.client(
        "bedrock-runtime",
        region_name=settings.AWS_REGION,
        config=BotoConfig(
            read_timeout=effective_timeout, connect_timeout=effective_timeout
        ),
    )
    try:
        response = client.converse(
            modelId=LLM_MODEL,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            system=[
                {
                    "text": "Return only valid JSON. Do not include any explanation or prose outside the JSON object."
                }
            ],
            inferenceConfig={"maxTokens": 2048},
        )
    except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError) as exc:
        raise LLMUnreachableError(f"LLM API error: {exc}") from exc

    raw = response["output"]["message"]["content"][0]["text"].strip()

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
        raise LLMUnreachableError(f"LLM returned invalid JSON: {exc}") from exc

    if not return_usage:
        return result

    usage = {
        "input_tokens": response["usage"]["inputTokens"],
        "output_tokens": response["usage"]["outputTokens"],
    }
    return result, usage


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
