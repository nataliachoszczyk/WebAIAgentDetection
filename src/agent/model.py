"""Access to the models: OpenRouter (key from the course) or the Kaggle Model Proxy. See docs/agent.md."""

import json
import os
import time
import urllib.request
from pathlib import Path

OPENROUTER_URL = "https://openrouter.ai/api/v1"


def load_env(path=".env"):
    """Put the keys of the local .env file into os.environ. Values that are already set stay."""
    path = Path(path)
    if path.exists():
        for line in path.read_text().splitlines():
            name, sep, value = line.partition("=")
            if sep and not line.lstrip().startswith("#"):
                os.environ.setdefault(name.strip(), value.strip())


def openrouter_key():
    load_env()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not in the environment or in .env")
    return key


def spend():
    """Return the spend of the OpenRouter key: {'usage': USD, 'limit': USD, 'limit_remaining': USD}."""
    request = urllib.request.Request(f"{OPENROUTER_URL}/key", headers={"Authorization": f"Bearer {openrouter_key()}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)["data"]
    return {k: data.get(k) for k in ("usage", "limit", "limit_remaining")}


class Model:
    """One model behind an API that is compatible with the OpenAI chat API.

    `api` is `openrouter` or `kaggle`. The Kaggle Model Proxy works only in a Kaggle Benchmark Task.
    """

    def __init__(self, model, effort="medium", api="openrouter", max_tokens=8000):
        from openai import OpenAI

        self.model, self.effort, self.api, self.max_tokens = model, effort, api, max_tokens
        if api == "openrouter":
            self.client = OpenAI(base_url=OPENROUTER_URL, api_key=openrouter_key(), timeout=180, max_retries=3)
        elif api == "kaggle":
            from kaggle_benchmarks import utils

            url = os.environ["MODEL_PROXY_URL"].rstrip("/")
            url = url if url.endswith("/openapi") else url + "/openapi"
            self.client = OpenAI(base_url=url, api_key=os.environ["MODEL_PROXY_API_KEY"], timeout=180, max_retries=3,
                                 http_client=utils.build_httpx_client("model_proxy"))
        else:
            raise ValueError(f"unknown api {api}")

    def chat(self, messages, tools):
        """Send one request. Return the answer message as a dict and the usage of the request."""
        extra = {}
        if self.api == "openrouter":
            extra["usage"] = {"include": True}
            if self.effort:
                extra["reasoning"] = {"effort": self.effort}
        start = time.time()
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, tools=tools, max_tokens=self.max_tokens, extra_body=extra)
        seconds = time.time() - start
        if not response.choices:
            raise RuntimeError(f"no answer from {self.model}: {response}")
        # model_dump keeps the extra fields of OpenRouter, for example reasoning_details.
        # The next request must send them back. Then the model keeps its thoughts between tool calls.
        message = response.choices[0].message.model_dump(exclude_none=True)
        usage = response.usage.model_dump() if response.usage else {}
        details = usage.get("completion_tokens_details") or {}
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
        return message, {
            "seconds": round(seconds, 2),
            "input_tokens": usage.get("prompt_tokens", 0),
            "cached_tokens": cached or 0,
            "output_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens": details.get("reasoning_tokens", 0),
            "cost": usage.get("cost"),
            "finish": response.choices[0].finish_reason,
        }
