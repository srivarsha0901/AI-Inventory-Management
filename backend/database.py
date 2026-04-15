from pymongo import MongoClient, ASCENDING
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone
from models import init_collections

client = None
db     = None

def init_db(app):
    global client, db
    client = MongoClient(app.config["MONGO_URI"])
    db     = client[app.config["MONGO_DB_NAME"]]
    app.extensions["db"] = db

    db.users.create_index([("email", ASCENDING)], unique=True)
    db.stores.create_index([("name", ASCENDING)])
    init_collections(db)
    print("✅ DB ready")

def get_db():
    return db