import os
from pymongo import MongoClient
from datetime import datetime
import random

MONGODB_URI = os.environ.get("MONGODB_URI", "")
client = MongoClient(MONGODB_URI)
db = client["cutie_pie_bot"]

users_col     = db["users"]
groups_col    = db["groups"]
patterns_col  = db["patterns"]
messages_col  = db["messages"]
blocked_col   = db["blocked"]

# ── USERS ──────────────────────────────────────────────────────────────

def save_user(user):
    users_col.update_one(
        {"user_id": user.id},
        {"$set": {
            "user_id":   user.id,
            "name":      user.full_name,
            "username":  user.username,
            "last_seen": datetime.now()
        }},
        upsert=True
    )

def get_all_users():
    return list(users_col.find({}, {"user_id": 1}))

def is_blocked(user_id):
    return blocked_col.find_one({"user_id": user_id}) is not None

def block_user(user_id):
    blocked_col.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "blocked_at": datetime.now()}},
        upsert=True
    )

def unblock_user(user_id):
    blocked_col.delete_one({"user_id": user_id})

# ── GROUPS ─────────────────────────────────────────────────────────────

def save_group(chat):
    groups_col.update_one(
        {"chat_id": chat.id},
        {"$set": {
            "chat_id":   chat.id,
            "title":     chat.title,
            "username":  getattr(chat, "username", None),
            "joined_at": datetime.now()
        }},
        upsert=True
    )

def remove_group(chat_id):
    groups_col.delete_one({"chat_id": chat_id})

def get_group(chat_id):
    return groups_col.find_one({"chat_id": chat_id})

def set_group_setting(chat_id, key, value):
    groups_col.update_one(
        {"chat_id": chat_id},
        {"$set": {key: value}},
        upsert=True
    )

def get_all_groups():
    return list(groups_col.find({}, {"chat_id": 1}))

# ── PATTERNS ───────────────────────────────────────────────────────────

def add_pattern(trigger, response, added_by=None):
    trigger = trigger.lower().strip()
    patterns_col.update_one(
        {"trigger": trigger},
        {
            "$addToSet": {"responses": response},
            "$set": {
                "added_by":   added_by,
                "updated_at": datetime.now()
            }
        },
        upsert=True
    )

def get_best_pattern(text):
    """
    Text mein sab patterns dhundho, sabse lamba match lo
    (longest match = most specific)
    """
    text_lower = text.lower()
    all_patterns = list(patterns_col.find({}))
    best = None
    best_len = 0
    for p in all_patterns:
        trigger = p["trigger"]
        if trigger in text_lower and len(trigger) > best_len:
            best = p
            best_len = len(trigger)
    return best

def get_random_response(pattern_doc):
    if not pattern_doc or not pattern_doc.get("responses"):
        return None
    return random.choice(pattern_doc["responses"])

def delete_pattern(trigger):
    patterns_col.delete_one({"trigger": trigger.lower().strip()})

def get_all_patterns():
    return list(patterns_col.find({}, {"trigger": 1, "responses": 1}))

# ── MESSAGES (context memory) ──────────────────────────────────────────

def save_message(chat_id, user_id, text):
    messages_col.insert_one({
        "chat_id": chat_id,
        "user_id": user_id,
        "text":    text,
        "time":    datetime.now()
    })
    # Sirf last 300 messages per group
    count = messages_col.count_documents({"chat_id": chat_id})
    if count > 300:
        oldest = list(
            messages_col.find({"chat_id": chat_id})
            .sort("time", 1)
            .limit(count - 300)
        )
        ids = [d["_id"] for d in oldest]
        messages_col.delete_many({"_id": {"$in": ids}})

def get_recent_messages(chat_id, limit=10):
    return list(
        messages_col.find({"chat_id": chat_id})
        .sort("time", -1)
        .limit(limit)
    )

# ── GROUP MESSAGE COUNTER (beech mein bolne ke liye) ───────────────────

_msg_counters = {}  # in-memory, per chat_id

def increment_counter(chat_id):
    _msg_counters[chat_id] = _msg_counters.get(chat_id, 0) + 1
    return _msg_counters[chat_id]

def reset_counter(chat_id):
    _msg_counters[chat_id] = 0
