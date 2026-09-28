from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


USER_AGENT = "edge-engine/0.1 (read-only research)"


class HttpError(RuntimeError):
    pass


def get_json(
    base_url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 8.0,
    attempts: int = 3,
) -> tuple[Any, float]:
    url = base_url
    if params:
        encoded = urllib.parse.urlencode(params, doseq=True)
        url = f"{base_url}?{encoded}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last_error: Exception | None = None
    for attempt in range(attempts):
        started = time.monotonic_ns()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                elapsed_ms = (time.monotonic_ns() - started) / 1_000_000
                return payload, elapsed_ms
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.25 * (2**attempt))
    raise HttpError(f"GET failed after {attempts} attempts: {url}: {last_error}")

