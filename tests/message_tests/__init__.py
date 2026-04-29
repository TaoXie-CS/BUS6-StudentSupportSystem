# -*- coding: utf-8 -*-
from flask import Flask
import os
from config import Config

def create_app(test_config=None):
    """Flask application factory (must be imported in conftest.py)"""
    # Create Flask instance
    app = Flask(__name__, instance_relative_config=True)

    # Load base configuration
    app.config.from_object(Config)

    # Test configuration override (optional)
    if test_config:
        app.config.update(test_config)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register blueprints/routes
    # from app.routes import teacher_bp, student_bp
    # app.register_blueprint(teacher_bp)
    # app.register_blueprint(student_bp)

    # Initialize extensions
    # db.init_app(app)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)