import os
import tempfile

from flask import Flask

from . import db as db_module
from . import seed as seed_module


def create_app(test_config=None, testing=False):
    """Application factory.

    testing=True wires up a fresh, throwaway SQLite file (not the app's real
    instance DB), initializes the schema, and seeds a small demo library --
    without generating audio files -- so the whole test suite is fast and has
    no side effects on the real instance/ database.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(app.instance_path, "spotify_clone.sqlite"),
    )

    if testing:
        db_fd, db_path = tempfile.mkstemp(suffix=".sqlite")
        app.config.update(TESTING=True, DATABASE=db_path)
        app.config["_TEST_DB_FD"] = db_fd

    if test_config:
        app.config.update(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db_module.init_app(app)

    with app.app_context():
        db_module.init_db()
        if testing:
            db = db_module.get_db()
            seed_module.seed_demo_data(db, generate_audio_files=False)

    from . import routes

    app.register_blueprint(routes.bp)

    return app
