import logging

import urllib3
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from loguru import logger

from app.apis.v1 import api_v1_bp

load_dotenv()

werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.ERROR)


class IgnoreSSLHandshakeFilter(logging.Filter):
    _PATTERNS = (
        r"\x16\x03\x01",
        "\\x16\\x03\\x01",
        "Bad request syntax",
        "Bad request version",
        "Bad HTTP/0.9",
        "Bad HTTP/1.0",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(pattern in msg for pattern in self._PATTERNS)


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

app = Flask(__name__)
_app_initialized = False


@app.before_request
def detect_ssl_on_http():
    if request.environ.get("werkzeug.request"):
        try:
            if hasattr(request, "data") and request.data:
                first_bytes = request.data[:3]
                if first_bytes == b"\x16\x03\x01":
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
            pass
    return None


@app.errorhandler(400)
def handle_bad_request(exc):
    error_description = str(exc.description) if hasattr(exc, "description") else str(exc)
    if any(indicator in error_description for indicator in ["\\x16\\x03\\x01", "Bad request", "Bad HTTP"]):
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
def handle_unexpected_error(exc):
    logger.error(f"Unexpected error: {type(exc).__name__}: {str(exc)}")
    return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500


@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response


def create_app() -> Flask:
    global _app_initialized
    if _app_initialized:
        return app

    from auth import auth_bp, init_default_admin
    from holdings import holdings_bp, init_holdings_table

    app.register_blueprint(auth_bp)
    app.register_blueprint(holdings_bp)
    app.register_blueprint(api_v1_bp)

    init_default_admin()
    init_holdings_table()

    _app_initialized = True
    return app


create_app()


if __name__ == "__main__":
    create_app().run(host="localhost", port=8311)
