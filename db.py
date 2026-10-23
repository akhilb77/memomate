"""MongoDB: messages and memories (database `memomate`)."""
import os
from datetime import datetime, timezone
from functools import cache

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


@cache
def _db():
    # Connect once, on first use. tz_aware=True gives back dates with a timezone.
    client = MongoClient(os.getenv("MONGODB_URI"), serverSelectionTimeoutMS=5000, tz_aware=True)
    return client["memomate"]


def now():
    return datetime.now(timezone.utc)


def setup_indexes():
    """Safe to run every start: MongoDB skips indexes that already exist."""
    # TTL index: MongoDB deletes a memory once its expires_at time has passed.
    _db().memories.create_index("expires_at", expireAfterSeconds=0)
    _db().messages.create_index([("user_id", 1), ("created_at", -1)])


def save_message(user_id, role, content, memories_used=None):
    _db().messages.insert_one({
        "user_id": user_id,
        "role": role,
        "content": content,
        "memories_used": memories_used or [],
        "created_at": now(),
    })


def recent_messages(user_id, limit=20):
    """Last `limit` messages, oldest first."""
    docs = _db().messages.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return list(docs)[::-1]


def save_memory(user_id, mem, embedding, source, expires_at):
    return _db().memories.insert_one({
        "user_id": user_id,
        "type": mem["type"],
        "content": mem["content"],
        "embedding": embedding,
        "source": source,
        "status": "active",
        "replaced_by": None,
        "created_at": now(),
        "updated_at": now(),
        "expires_at": expires_at,
    }).inserted_id


def list_memories(user_id):
    """Active, not-yet-expired memories (without the big embedding array)."""
    # The TTL cleanup runs about once a minute, so we also hide expired ones here.
    query = {
        "user_id": user_id,
        "status": "active",
        "$or": [{"expires_at": None}, {"expires_at": {"$gt": now()}}],
    }
    return list(_db().memories.find(query, {"embedding": 0}).sort("created_at", -1))


def delete_memory(user_id, memory_id):
    _db().memories.delete_one({"_id": memory_id, "user_id": user_id})
