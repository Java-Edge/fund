import logging

import urllib3
from flask import Flask, Response, jsonify, request
from loguru import logger

_SSL_REQUEST_PATTERNS = (
    r"\x16\x03\x01",
    "\\x16\\x03\\x01",
    "Bad request syntax",
    "Bad request version",
    "Bad HTTP/0.9",
    "Bad HTTP/1.0",
)

# SSL/坏请求拦截
class IgnoreSSLHandshakeFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not any(pattern in record.getMessage() for pattern in _SSL_REQUEST_PATTERNS)


def configure_runtime() -> None:
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.ERROR)
    if not any(isinstance(existing_filter, IgnoreSSLHandshakeFilter) for existing_filter in werkzeug_logger.filters):
        werkzeug_logger.addFilter(IgnoreSSLHandshakeFilter())

    urllib3.disable_warnings()
    urllib3.util.ssl_.DEFAULT_CIPHERS = ":".join(
        [
            "ECDHE+AESGCM",
            "ECDHE+CHACHA20",
            "ECDHE-RSA-AES128-SHA",
            "ECDHE-RSA-AES256-SHA",
            "RSA+AESGCM",
            "AES128-SHA",
            "AES256-SHA",
        ]
    )


def register_common_handlers(app: Flask) -> None:
    @app.before_request
    def handle_preflight_and_ssl() -> tuple[Response, int] | None:
        if request.method == "OPTIONS":
            return jsonify({}), 200

        if not request.environ.get("werkzeug.request"):
            return None

        try:
            if hasattr(request, "data") and request.data[:3] == b"\x16\x03\x01":
                logger.warning(f"SSL/TLS request detected on HTTP endpoint from {request.remote_addr}")
                return (
                    jsonify(
                        {
                            "error": "SSL/TLS not supported on this endpoint",
                            "message": "This server uses HTTP, not HTTPS. Please use http:// instead of https://",
                        }
                    ),
                    400,
                )
        except Exception:
            return None
        return None

    @app.errorhandler(400)
    def handle_bad_request(exc: Exception) -> tuple[Response, int]:
        error_description = str(exc.description) if hasattr(exc, "description") else str(exc)
        if any(indicator in error_description for indicator in _SSL_REQUEST_PATTERNS):
            logger.warning(f"Rejected malformed/SSL request from {request.remote_addr}")
            return (
                jsonify(
                    {
                        "error": "Bad Request",
                        "message": "Invalid HTTP request. If you're trying to use HTTPS, please use HTTP instead.",
                        "server": "HTTP only (no SSL/TLS)",
                    }
                ),
                400,
            )
        return jsonify({"error": "Bad Request", "message": error_description}), 400

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception) -> tuple[Response, int]:
        logger.error(f"Unexpected error: {type(exc).__name__}: {exc}")
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500

    @app.after_request
    def add_cors_headers(response: Response) -> Response:
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        return response