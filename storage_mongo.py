# storage_mongo.py
import os
from pymongo import MongoClient
import gridfs
from bson import ObjectId

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["futureGoalAI"]
fs = gridfs.GridFS(db)

def save_file_to_db(file_bytes, filename, content_type):
    """
    Save file to MongoDB GridFS.
    Returns: file_id (string)
    """
    file_id = fs.put(
        file_bytes,
        filename=filename,
        content_type=content_type
    )
    return str(file_id)

def get_file_from_db(file_id):
    """
    Retrieve file from GridFS by ID.
    """
    file = fs.get(ObjectId(file_id))
    return file.read(), file.filename, file.content_type
