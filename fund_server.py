from flask import Flask

from app.factory import create_app as build_app

app = build_app()

def create_app() -> Flask:
    return app

if __name__ == "__main__":
    create_app().run(host="localhost", port=8311)