"""One-off diagnostic script to systematically test AWS Bedrock model access
across every combination of endpoint, API, auth method, and model we've
tried in this debugging session — to pin down exactly which combination(s)
actually work for this account.

Reads the Bedrock long-term API key from the BEDROCK_API_KEY env var (pass
it via `docker compose exec -e BEDROCK_API_KEY=... app python
bedrock_access_diagnostics.py`, or set it in .env.prod first).

Usage:
    docker compose exec -e BEDROCK_API_KEY=<key> app python bedrock_access_diagnostics.py
"""

import os

RESULTS: list[tuple[str, str]] = []


def record(label: str, ok: bool, detail: str) -> None:
    status = "PASS" if ok else "FAIL"
    RESULTS.append((label, f"{status}: {detail}"))
    print(f"[{status}] {label}: {detail}", flush=True)


def get_bedrock_api_key() -> str:
    key = os.environ.get("BEDROCK_API_KEY", "")
    if not key:
        raise SystemExit(
            "BEDROCK_API_KEY env var not set — pass it with -e or set it first."
        )
    return key


def test_converse_iam(model_id: str, region: str, label: str) -> None:
    import boto3

    try:
        client = boto3.client("bedrock-runtime", region_name=region)
        response = client.converse(
            modelId=model_id,
            messages=[
                {"role": "user", "content": [{"text": "Say hello in one word."}]}
            ],
        )
        record(label, True, response["output"]["message"]["content"][0]["text"])
    except Exception as exc:
        record(label, False, f"{type(exc).__name__}: {exc}")


def test_converse_bearer(model_id: str, region: str, label: str, api_key: str) -> None:
    import boto3

    old = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = api_key
    try:
        client = boto3.client("bedrock-runtime", region_name=region)
        response = client.converse(
            modelId=model_id,
            messages=[
                {"role": "user", "content": [{"text": "Say hello in one word."}]}
            ],
        )
        record(label, True, response["output"]["message"]["content"][0]["text"])
    except Exception as exc:
        record(label, False, f"{type(exc).__name__}: {exc}")
    finally:
        if old is None:
            os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)
        else:
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = old


def test_mantle_chat_completions(
    model_id: str, region: str, path: str, label: str, api_key: str
) -> None:
    from openai import OpenAI

    try:
        client = OpenAI(
            base_url=f"https://bedrock-mantle.{region}.api.aws{path}",
            api_key=api_key,
        )
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Say hello in one word."}],
        )
        record(label, True, response.choices[0].message.content)
    except Exception as exc:
        record(label, False, f"{type(exc).__name__}: {exc}")


def test_mantle_anthropic_messages(
    model_id: str, region: str, label: str, api_key: str
) -> None:
    """Claude on bedrock-mantle uses the native Anthropic Messages API, not
    OpenAI Chat Completions — per AWS's own getting-started sample for
    Claude Sonnet 5, base_url is https://bedrock-mantle.{region}.api.aws/anthropic
    and the SDK appends /v1/messages itself."""
    from anthropic import Anthropic

    try:
        client = Anthropic(
            base_url=f"https://bedrock-mantle.{region}.api.aws/anthropic",
            api_key=api_key,
        )
        response = client.messages.create(
            model=model_id,
            max_tokens=64,
            messages=[{"role": "user", "content": "Say hello in one word."}],
        )
        record(label, True, response.content[0].text)
    except Exception as exc:
        record(label, False, f"{type(exc).__name__}: {exc}")


def main() -> None:
    api_key = get_bedrock_api_key()
    region = "ap-south-1"

    print("=" * 80)
    print("Bedrock access diagnostics")
    print("=" * 80)

    # Claude — Converse API, IAM role auth (known baseline)
    test_converse_iam(
        "global.anthropic.claude-sonnet-4-6", region, "Claude / Converse / IAM role"
    )

    # Claude — Converse API, bearer token auth (NEW — untested combo)
    test_converse_bearer(
        "global.anthropic.claude-sonnet-4-6",
        region,
        "Claude / Converse / Bearer token",
        api_key,
    )

    # Nova Pro — Converse API, bearer token auth (NEW — untested combo)
    test_converse_bearer(
        "amazon.nova-pro-v1:0", region, "Nova Pro / Converse / Bearer token", api_key
    )

    # Qwen3 Coder Next — mantle + Chat Completions (known working)
    test_mantle_chat_completions(
        "qwen.qwen3-coder-next",
        region,
        "/v1",
        "Qwen3 Coder Next / mantle+ChatCompletions",
        api_key,
    )

    # GPT-5.6 Terra — mantle + Chat Completions, corrected /openai/v1 path
    test_mantle_chat_completions(
        "openai.gpt-5.6-terra",
        region,
        "/openai/v1",
        "GPT-5.6 Terra / mantle+ChatCompletions",
        api_key,
    )

    # Claude Sonnet 4.6 is NOT offered on bedrock-mantle at all (confirmed via
    # AWS's endpoint-availability table) — that's why it 404'd, not auth.
    # Claude Sonnet 5 IS listed as mantle-supported, with confirmed model ID
    # "anthropic.claude-sonnet-5" from its model card — try that instead.
    test_mantle_anthropic_messages(
        "anthropic.claude-sonnet-5",
        region,
        "Claude Sonnet 5 / mantle+Messages",
        api_key,
    )

    print("=" * 80)
    print("Summary:")
    for label, result in RESULTS:
        print(f"  {label}: {result}")


if __name__ == "__main__":
    main()
