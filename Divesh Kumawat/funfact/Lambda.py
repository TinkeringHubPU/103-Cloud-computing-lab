import boto3
import random
import json
from botocore.config import Config

# --- Bedrock client with built-in retry/backoff for throttling ---
# retries.mode="adaptive" auto-backs-off on ThrottlingException instead of
# failing on the first hiccup under load.
bedrock_config = Config(
    retries={
        "max_attempts": 3,
        "mode": "adaptive"
    },
    read_timeout=300,
    connect_timeout=10
)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("CloudFacts")

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1", config=bedrock_config)

MODEL_ID = "global.amazon.nova-2-lite-v1:0"

# --- Module-level cache ---
# Lambda reuses the same execution environment across invocations (a "warm
# start"). Caching the facts here means we only scan DynamoDB once per
# container instead of on every single request.
_facts_cache = None


def build_response(body_dict, status_code=200):
    """Helper to build a consistent API response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps(body_dict)
    }


def fetch_random_fact():
    """
    Return a random fact string, or None if empty.
    Uses a module-level cache so we only hit DynamoDB once per warm
    container, and only pulls the FactText attribute (not the whole item)
    to keep the scan payload small.
    """
    global _facts_cache

    if _facts_cache is None:
        response = table.scan(ProjectionExpression="FactText")
        items = response.get("Items", [])

        # Handle pagination in case the table grows past the 1MB scan limit
        while "LastEvaluatedKey" in response:
            response = table.scan(
                ProjectionExpression="FactText",
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))

        _facts_cache = [item["FactText"] for item in items if "FactText" in item]

    if not _facts_cache:
        return None

    return random.choice(_facts_cache)


def invoke_nova(fact_text):
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": (
                        f"Take this cloud computing fact and make it fun and engaging "
                        f"in 1-2 sentences maximum. Keep it short and witty: {fact_text}"
                    )
                }
            ]
        }
    ]

    request_body = {
        "messages": messages,
        "inferenceConfig": {
            "maxTokens": 100,
            "temperature": 0.7,
            "reasoningConfig": {
                "type": "disabled"   # simple rewrite task doesn't need reasoning at all
            }
        }
    }

    resp = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(request_body),
        accept="application/json",
        contentType="application/json"
    )

    result = json.loads(resp["body"].read())

    witty_fact = ""
    if "output" in result and "message" in result["output"]:
        content_blocks = result["output"]["message"].get("content", [])
        for block in content_blocks:
            if "text" in block:
                witty_fact = block["text"].strip()
                break

    return witty_fact if witty_fact else None


def lambda_handler(event, context):
    # Step 1: Fetch a random fact from DynamoDB (cached across warm starts)
    fact = fetch_random_fact()
    if not fact:
        return build_response({"fact": "No facts available in DynamoDB."})

    # Step 2: Invoke Amazon Nova 2 Lite (global inference profile)
    try:
        witty_fact = invoke_nova(fact)

        # Fallback: if response is empty or suspiciously long, use original fact
        if not witty_fact or len(witty_fact) > 300:
            print("Warning: Nova response was empty or too long. Falling back to original fact.")
            witty_fact = fact

    except Exception as e:
        # Log full error details to CloudWatch for debugging
        print(f"Bedrock invocation failed.")
        print(f"Error type   : {type(e).__name__}")
        print(f"Error details: {str(e)}")
        witty_fact = "Nahi Hua"  # unchanged, as requested

    # Step 3: Return the witty (or fallback) fact
    return build_response({"fact": witty_fact})