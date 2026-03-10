import os

import httpx
from openai import APIConnectionError, OpenAI


# Configure these via environment variables when possible.
openai_api_key = os.environ.get("OPENAI_API_KEY", "")
openai_api_base = os.environ.get("OPENAI_API_BASE", "https://llm-api.arc.vt.edu/api/v1")

if not openai_api_key:
    raise RuntimeError(
        "Missing OPENAI_API_KEY. Set it in your shell before running this script."
    )

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
    # Some environments resolve IPv6 first and fail with Errno 101 (no route).
    # Binding the client to an IPv4 local address avoids that failure mode.
    http_client=httpx.Client(
        transport=httpx.HTTPTransport(local_address="0.0.0.0"),
        timeout=20.0,
    ),
)

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is Virginia Tech's mascot?"},
]

model = "gpt-oss-120b"


try:
    response = client.chat.completions.create(model=model, messages=messages)
    print(response.choices[0].message.content)
except APIConnectionError:
    print(
        "Connection error to LLM API. Your network cannot reach the API endpoint.\n"
        "Try: connect to required VPN, verify proxy settings, and test the endpoint with curl."
    )
