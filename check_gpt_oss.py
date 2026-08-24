"""One-off diagnostic script to check whether gpt-oss-20b (OpenAI's
open-weight model, available on Bedrock) is authorized and invokable on
this account — continuing the model-access investigation from
bedrock_access_diagnostics.py.

Looks up the exact model ID(s) via ListFoundationModels (rather than
guessing), runs GetFoundationModelAvailability for each match, then attempts
an actual invocation via the Converse API to see whether it gets further
than the authorization check.

Auth: uses the Bedrock long-term API key (bearer token) since IAM role auth
via EC2 instance metadata is only available when run on the actual server,
not locally.

Usage:
    docker compose exec -e BEDROCK_API_KEY=<key> app python check_gpt_oss.py
"""

import os

import boto3

REGION = "ap-south-1"


def main() -> None:
    api_key = os.environ.get("BEDROCK_API_KEY", "")
    if not api_key:
        raise SystemExit(
            "BEDROCK_API_KEY env var not set — pass it with "
            "`docker compose exec -e BEDROCK_API_KEY=<key> app python check_gpt_oss.py`"
        )
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = api_key

    control = boto3.client("bedrock", region_name=REGION)
    runtime = boto3.client("bedrock-runtime", region_name=REGION)

    print("=" * 80)
    print("Looking up gpt-oss model IDs via ListFoundationModels")
    print("=" * 80)

    models = control.list_foundation_models()["modelSummaries"]
    matches = [m for m in models if "gpt-oss" in m["modelId"].lower()]

    if not matches:
        print("No gpt-oss models found in list_foundation_models() for this region.")
        print("Trying known candidate IDs directly instead.\n")
        matches = [
            {"modelId": "openai.gpt-oss-20b-1:0"},
            {"modelId": "openai.gpt-oss-120b-1:0"},
        ]

    for m in matches:
        model_id = m["modelId"]
        print(f"\n--- {model_id} ---")

        try:
            avail = control.get_foundation_model_availability(modelId=model_id)
            print(f"  agreementAvailability:   {avail.get('agreementAvailability')}")
            print(f"  authorizationStatus:     {avail.get('authorizationStatus')}")
            print(f"  entitlementAvailability: {avail.get('entitlementAvailability')}")
            print(f"  regionAvailability:      {avail.get('regionAvailability')}")
        except Exception as exc:
            print(
                f"  GetFoundationModelAvailability FAILED: {type(exc).__name__}: {exc}"
            )

        try:
            response = runtime.converse(
                modelId=model_id,
                messages=[
                    {"role": "user", "content": [{"text": "Say hello in one word."}]}
                ],
            )
            text = response["output"]["message"]["content"][0]["text"]
            print(f"  Converse invocation: SUCCESS: {text}")
        except Exception as exc:
            print(f"  Converse invocation: FAILED: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
