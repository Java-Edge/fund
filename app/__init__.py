from flask import Flask


def create_app() -> Flask:
    from fund_server import create_app as legacy_create_app

    return legacy_create_app()
