import os
from pymongo import MongoClient
from datetime import datetime, timedelta
import random
import time

MONGODB_URI = os.environ.get("MONGODB_URI", "")
client = MongoClient(
    MONGODB_URI,
    tls=True,
    tlsAllowInvalidCertificates=True,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=5000
)
db = client["cutie_pie_bot"]

users_col     = db["users"]
groups_col    = db["groups"]
patterns_col  = db["patterns"]
messages_col  = db["messages"]
blocked_col   = db["blocked"]
premium_col   = db["premium_requests"]
pending_del   = db["pending_deletes"]

_flood: dict = {}  # in-memory flood tracker

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

def set_setting(chat_id, key, value):
    groups_col.update_one(
        {"chat_id": chat_id},
        {"$set": {key: value}},
        upsert=True
    )

def get_setting(chat_id, key, default=None):
    g = groups_col.find_one({"chat_id": chat_id})
    return g.get(key, default) if g else default

def toggle_setting(chat_id, key, default=False) -> bool:
    cur = get_setting(chat_id, key, default)
    new_val = not cur
    set_setting(chat_id, key, new_val)
    return new_val

# Keep old alias for compatibility
def set_group_setting(chat_id, key, value):
    set_setting(chat_id, key, value)

def get_all_groups():
    return list(groups_col.find({}, {"chat_id": 1}))

# ── PREMIUM ────────────────────────────────────────────────────────────

def is_premium(chat_id: int) -> bool:
    g = groups_col.find_one({"chat_id": chat_id})
    if not g:
        return False
    if not g.get("premium"):
        return False
    exp = g.get("premium_expires")
    if exp and exp < datetime.now():
        set_setting(chat_id, "premium", False)
        return False
    return True

def set_premium(chat_id: int, months: int = 1):
    exp = datetime.now() + timedelta(days=30 * months)
    groups_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"premium": True, "premium_expires": exp}},
        upsert=True
    )

def revoke_premium(chat_id: int):
    set_setting(chat_id, "premium", False)
    set_setting(chat_id, "premium_expires", None)

# ── PREMIUM REQUESTS ───────────────────────────────────────────────────

def save_prem_request(user_id: int, group_id: int, utr: str, screenshot_id: str = None):
    return premium_col.insert_one({
        "user_id":    user_id,
        "group_id":   group_id,
        "utr":        utr,
        "screenshot": screenshot_id,
        "status":     "pending",
        "created_at": datetime.now(),
    })

def get_prem_request(request_id):
    from bson import ObjectId
    return premium_col.find_one({"_id": ObjectId(str(request_id))})

def update_prem_status(request_id, status: str):
    from bson import ObjectId
    premium_col.update_one({"_id": ObjectId(str(request_id))}, {"$set": {"status": status}})

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

def find_pattern(text: str):
    """Alias used by auto-mod / event handlers"""
    best = get_best_pattern(text)
    if best and best.get("responses"):
        return random.choice(best["responses"])
    return None

def get_random_response(pattern_doc):
    if not pattern_doc or not pattern_doc.get("responses"):
        return None
    return random.choice(pattern_doc["responses"])

def del_pattern(trigger: str):
    patterns_col.delete_one({"trigger": trigger.lower().strip()})

def delete_pattern(trigger):
    del_pattern(trigger)

def get_all_patterns():
    return list(patterns_col.find({}, {"trigger": 1, "responses": 1}))

def list_patterns():
    return get_all_patterns()

# ── WARNINGS ──────────────────────────────────────────────────────────

warns_col = db["warnings"]

def add_warn(chat_id: int, user_id: int, reason: str = "", admin_id: int = None) -> int:
    warns_col.insert_one({
        "chat_id":  chat_id,
        "user_id":  user_id,
        "reason":   reason,
        "admin_id": admin_id,
        "time":     datetime.now(),
    })
    return warns_col.count_documents({"chat_id": chat_id, "user_id": user_id})

def get_warns(chat_id: int, user_id: int) -> int:
    return warns_col.count_documents({"chat_id": chat_id, "user_id": user_id})

def get_warn_reasons(chat_id: int, user_id: int):
    docs = warns_col.find({"chat_id": chat_id, "user_id": user_id})
    return [d.get("reason") or "No reason" for d in docs]

def reset_warns(chat_id: int, user_id: int):
    warns_col.delete_many({"chat_id": chat_id, "user_id": user_id})

# ── MESSAGES (context memory) ──────────────────────────────────────────

def save_message(chat_id, user_id, text):
    messages_col.insert_one({
        "chat_id": chat_id,
        "user_id": user_id,
        "text":    text,
        "time":    datetime.now()
    })
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

# ── GROUP MESSAGE COUNTER ──────────────────────────────────────────────

_msg_counters = {}

def increment_counter(chat_id):
    _msg_counters[chat_id] = _msg_counters.get(chat_id, 0) + 1
    return _msg_counters[chat_id]

def reset_counter(chat_id):
    _msg_counters[chat_id] = 0

# ── FLOOD TRACKER ─────────────────────────────────────────────────────

def is_flooding(chat_id: int, user_id: int, limit: int = 5, window: int = 10) -> bool:
    now = time.time()
    key = (chat_id, user_id)
    _flood.setdefault(key, [])
    _flood[key] = [t for t in _flood[key] if now - t < window]
    _flood[key].append(now)
    return len(_flood[key]) > limit

# ── PENDING DELETES ────────────────────────────────────────────────────

def schedule_delete(chat_id: int, msg_id: int, delete_at: datetime):
    pending_del.insert_one({"chat_id": chat_id, "msg_id": msg_id, "delete_at": delete_at})

def get_due_deletes():
    return list(pending_del.find({"delete_at": {"$lte": datetime.now()}}))

def remove_delete(doc_id):
    pending_del.delete_one({"_id": doc_id})

# ── ACTIVE MEMBERS TRACKER ────────────────────────────────────────────

def save_active_member(chat_id: int, user_id: int):
    users_col.update_one(
        {"user_id": user_id},
        {"$addToSet": {"active_in": chat_id}},
        upsert=True
    )

def get_active_members(chat_id: int):
    return list(users_col.find({"active_in": chat_id}, {"user_id": 1}))
