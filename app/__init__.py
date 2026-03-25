from flask import Flask


def create_app() -> Flask:
    from app.factory import create_app as app_factory

    return app_factory()