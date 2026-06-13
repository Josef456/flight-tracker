"""Local entry point.

    python run.py          # start the development server on http://127.0.0.1:5000
"""
from app import create_app, db

app = create_app()


@app.shell_context_processor
def _shell_context():
    from app import models

    return {"db": db, "models": models}


if __name__ == "__main__":
    app.run(debug=True)
