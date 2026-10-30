"""The only place that talks to a model: NVIDIA Nemotron served by Nebius Token Factory.

The key is read from the environment and never logged. Token usage is counted so the app can
show what an answer cost and stop before a budget is exceeded.
"""
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

BASE = os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1")
MODEL = os.environ.get("EVERYPAGE_MODEL", "nvidia/Nemotron-3.5-Super-VL")
PRICE_IN = float(os.environ.get("EVERYPAGE_PRICE_IN", "0.30"))     # USD per 1M input tokens
PRICE_OUT = float(os.environ.get("EVERYPAGE_PRICE_OUT", "0.90"))   # USD per 1M output tokens

_lock = threading.Lock()
usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}


class ModelError(RuntimeError):
    pass


def cost(prompt_tokens, completion_tokens):
    return prompt_tokens / 1e6 * PRICE_IN + completion_tokens / 1e6 * PRICE_OUT


def generate(prompt, as_json=False, timeout=60, counter=None):
    key = os.environ.get("NEBIUS_API_KEY")
    if not key:
        raise ModelError("NEBIUS_API_KEY is not set")
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "max_tokens": 1500}   # the model reasons before it answers; leave room
    if as_json:
        body["response_format"] = {"type": "json_object"}
    data = json.dumps(body).encode()
    last = None
    for attempt in range(4):
        req = urllib.request.Request(BASE + "/chat/completions", data=data,
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read())
            u = d.get("usage") or {}
            with _lock:
                usage["calls"] += 1
                usage["prompt_tokens"] += u.get("prompt_tokens", 0)
                usage["completion_tokens"] += u.get("completion_tokens", 0)
            if counter is not None:
                counter["prompt_tokens"] = counter.get("prompt_tokens", 0) + u.get("prompt_tokens", 0)
                counter["completion_tokens"] = counter.get("completion_tokens", 0) + u.get("completion_tokens", 0)
                counter["calls"] = counter.get("calls", 0) + 1
            return d["choices"][0]["message"].get("content") or ""
        except urllib.error.HTTPError as e:
            last = "HTTP %d" % e.code
            if e.code in (400, 401, 403, 404):
                break
            if e.code == 429:            # rate limited: wait as long as the service asks, at least a few seconds
                try:
                    wait = float(e.headers.get("Retry-After", "0"))
                except ValueError:
                    wait = 0.0
                time.sleep(min(20.0, max(wait, 2.0 * (attempt + 1))))
                continue
        except Exception as e:   # timeout, connection reset, bad JSON
            last = type(e).__name__
        time.sleep(1.5 * (attempt + 1))
    print("model call failed after retries: %s" % last, file=sys.stderr, flush=True)   # never the key, never the prompt
    raise ModelError("model call failed: %s" % last)
