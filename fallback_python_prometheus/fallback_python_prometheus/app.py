import json
import logging
import os
from datetime import datetime, timezone

import requests
from flask import Flask, Response, jsonify, request
from prometheus_client import Counter, CONTENT_TYPE_LATEST, generate_latest

app = Flask(__name__)

PRIMARY_URL = os.getenv("PRIMARY_URL", "https://jsonplaceholder.typicode.com/todos")
FALLBACK_URL = os.getenv("FALLBACK_URL", "https://dummyjson.com/todos")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "5"))
PORT = int(os.getenv("PORT", "8000"))

fallback_counter = Counter(
    "fallback_triggered_total",
    "Number of times the fallback backend was used"
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            payload.update(record.extra_fields)
        return json.dumps(payload, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("fallback_app")
logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.addHandler(handler)
logger.propagate = False


def fetch_json(url: str):
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


@app.route("/")
def home():
    return jsonify(
        {
            "service": "python-fallback-prometheus-demo",
            "endpoints": ["/todos", "/metrics", "/health"],
            "usage": "Use /todos?failPrimary=true to force the fallback for testing.",
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/todos")
def get_todos():
    fail_primary = request.args.get("failPrimary", "false").lower() == "true"

    try:
        if fail_primary:
            raise requests.RequestException("Primary backend failure was forced for testing.")

        primary_data = fetch_json(PRIMARY_URL)
        return jsonify(
            {
                "source": "primary",
                "backend": PRIMARY_URL,
                "count": len(primary_data) if isinstance(primary_data, list) else len(primary_data.get("todos", [])),
                "data": primary_data,
            }
        )

    except Exception as primary_error:
        fallback_counter.inc()
        logger.info(
            "Fallback activated",
            extra={
                "extra_fields": {
                    "event": "fallback_triggered",
                    "primary_backend": PRIMARY_URL,
                    "fallback_backend": FALLBACK_URL,
                    "reason": str(primary_error),
                    "path": request.path,
                    "query": request.query_string.decode("utf-8"),
                    "remote_addr": request.remote_addr,
                }
            },
        )

        try:
            fallback_data = fetch_json(FALLBACK_URL)
            count = len(fallback_data) if isinstance(fallback_data, list) else len(fallback_data.get("todos", []))
            return jsonify(
                {
                    "source": "fallback",
                    "backend": FALLBACK_URL,
                    "count": count,
                    "data": fallback_data,
                }
            )
        except Exception as fallback_error:
            logger.error(
                "Both backends failed",
                extra={
                    "extra_fields": {
                        "event": "all_backends_failed",
                        "primary_backend": PRIMARY_URL,
                        "fallback_backend": FALLBACK_URL,
                        "primary_error": str(primary_error),
                        "fallback_error": str(fallback_error),
                    }
                },
            )
            return jsonify(
                {
                    "error": "Both backends failed",
                    "primary_error": str(primary_error),
                    "fallback_error": str(fallback_error),
                }
            ), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
