import os
from app import app, db

print("Using DATABASE_URL =", os.getenv("DATABASE_URL"))

with app.app_context():
    print("Engine URL:", db.engine.url)
    db.create_all()
    print("✅ db.create_all() complete")
