"""
Database schema creation script.
Creates all required tables for persistent storage.
"""

import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db import init_db, engine

def main():
    print("Initializing database tables...")
    init_db(engine)
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    main()
