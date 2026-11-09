import os
from flask import Flask, send_from_directory
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from .db import init_db

load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "dev-only-change-me"),
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "dev-jwt-change-me"),
        DATABASE=os.getenv("DATABASE_PATH", "hirelens.db"),
        UPLOAD_FOLDER=os.getenv("UPLOAD_FOLDER", "uploads"),
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH_MB", "25")) * 1024 * 1024,
        JWT_ACCESS_TOKEN_EXPIRES=False,
    )
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    JWTManager(app)
    init_db(app)
    from .routes import api
    app.register_blueprint(api, url_prefix="/api")
    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")
    @app.get("/<path:path>")
    def static_proxy(path):
        return send_from_directory(app.static_folder, path)
    return app
