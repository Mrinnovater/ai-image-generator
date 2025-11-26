# database_history.py
import os
from pymongo import MongoClient
from datetime import datetime

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["futureGoalAI"]
history = db["history"]

def save_history(name, school, goal, captured_id, ai_id, card_id):
    """
    Save student detail + GridFS file IDs to MongoDB.
    """
    history.insert_one({
        "name": name,
        "school": school,
        "goal": goal,
        "captured_image_id": captured_id,
        "ai_image_id": ai_id,
        "printable_card_id": card_id,
        "timestamp": datetime.now()
    })
