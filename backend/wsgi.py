"""
WSGI entry point for production servers (gunicorn).

Run with:  gunicorn wsgi:app

Importing this module initializes the database (creating tables and seeding the
sample catalog on first boot) and builds the in-memory course intelligence
index, which every worker process needs its own copy of.
"""

from app_ai import app, init_db

init_db()

if __name__ == '__main__':
    app.run()
