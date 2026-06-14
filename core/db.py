import os
import re
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timedelta
import random

MONGODB_URI = os.environ.get("MONGODB_URI", "")
client = MongoClient(
    MONGODB_URI,
    tls=True,
    tlsAllowInvalidCertificates=True,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=5000,
)
db = client["cutie_pie_bot"]

users_col        = db["users"]
groups_col       = db["groups"]
patterns_col     = db["patterns"]
messages_col     = db["messages"]
blocked_col      = db["blocked"]
premium_col      = db["premium_requests"]
pending_del      = db["pending_deletes"]
prem_state_col   = db["prem_conversation_state"]
warns_col        = db["warnings"]
notes_col        = db["notes"]
file_hashes_col  = db["file_hashes"]
captcha_col      = db["captcha_pending"]
analytics_col    = db["msg_analytics"]
gaali_col        = db["gaali_strikes"]
raid_col         = db["raid_joins"]
scheduled_col    = db["scheduled_msgs"]
context_col      = db["chat_context"]
bot_reply_col    = db["bot_reply_history"]
tagall_col       = db["tagall_jobs"]
filters_col      = db["filters"]

_flood: dict = {}

# ── MongoDB TTL Indexes — auto-delete old data ────────────
# Ye ek baar chalte hain, MongoDB khud expired records delete karta hai
# (Background mein kaam karta hai, bot pe load nahi)
def _setup_ttl_indexes():
    try:
        # Messages: 7 din baad auto-delete
        messages_col.create_index("at", expireAfterSeconds=7 * 24 * 3600, background=True)
        # Captcha: 10 min baad auto-delete (extra buffer)
        captcha_col.create_index("expires_at", expireAfterSeconds=0, background=True)
        # Raid joins: 1 din baad auto-delete
        raid_col.create_index("joined_at", expireAfterSeconds=24 * 3600, background=True)
        # Prem state (conversation): 2 din
        prem_state_col.create_index("updated_at", expireAfterSeconds=2 * 24 * 3600, background=True)
    except Exception:
        pass  # Index already exists ya permission nahi — koi baat nahi

_setup_ttl_indexes()

# ════════ USERS ════════
def save_user(user):
    users_col.update_one(
        {"user_id": user.id},
        {"$set": {"user_id": user.id, "name": user.full_name,
                  "username": user.username, "last_seen": datetime.now()}},
        upsert=True,
    )

def get_all_users():
    return list(users_col.find({}, {"user_id": 1}))

def get_user_info(user_id: int):
    return users_col.find_one({"user_id": user_id})

def is_blocked(user_id: int) -> bool:
    return blocked_col.find_one({"user_id": user_id}) is not None

def block_user(user_id: int):
    blocked_col.update_one({"user_id": user_id},
        {"$set": {"user_id": user_id, "blocked_at": datetime.now()}}, upsert=True)

def unblock_user(user_id: int):
    blocked_col.delete_one({"user_id": user_id})

# ════════ GROUPS ════════
def save_group(chat):
    groups_col.update_one({"chat_id": chat.id},
        {"$set": {"chat_id": chat.id, "title": chat.title,
                  "username": getattr(chat, "username", None),
                  "updated_at": datetime.now()}}, upsert=True)

def remove_group(chat_id: int):
    groups_col.delete_one({"chat_id": chat_id})

def get_all_groups():
    return list(groups_col.find({}, {"chat_id": 1, "title": 1}))

# ════════ SETTINGS ════════
def get_setting(chat_id: int, key: str, default=None):
    doc = groups_col.find_one({"chat_id": chat_id}, {key: 1})
    return doc.get(key, default) if doc else default

def set_setting(chat_id: int, key: str, value):
    groups_col.update_one({"chat_id": chat_id}, {"$set": {key: value}}, upsert=True)

def toggle_setting(chat_id: int, key: str, default: bool = False) -> bool:
    cur = get_setting(chat_id, key, default)
    new = not cur
    set_setting(chat_id, key, new)
    return new

# ════════ PREMIUM ════════
def is_premium(chat_id: int) -> bool:
    doc = groups_col.find_one({"chat_id": chat_id}, {"premium": 1, "premium_expires": 1})
    if not doc or not doc.get("premium"):
        return False
    exp = doc.get("premium_expires")
    if exp and exp < datetime.now():
        groups_col.update_one({"chat_id": chat_id}, {"$set": {"premium": False}})
        return False
    return True

def grant_premium(chat_id: int, days: int = 30):
    expires = datetime.now() + timedelta(days=days)
    groups_col.update_one({"chat_id": chat_id},
        {"$set": {"premium": True, "premium_expires": expires,
                  "premium_granted_at": datetime.now()}}, upsert=True)

def revoke_premium(chat_id: int):
    groups_col.update_one({"chat_id": chat_id},
        {"$set": {"premium": False, "premium_expires": None}})

def get_all_premium_groups():
    return list(groups_col.find(
        {"premium": True, "premium_expires": {"$gt": datetime.now()}},
        {"chat_id": 1, "title": 1, "premium_expires": 1, "premium_granted_at": 1}
    ))

def save_prem_request(user_id: int, group_id: int, utr: str, screenshot_id: str = None):
    doc = {"user_id": user_id, "group_id": group_id, "utr": utr,
           "screenshot": screenshot_id, "status": "pending",
           "requested_at": datetime.now()}
    return str(premium_col.insert_one(doc).inserted_id)

# ════════ PREM STATE ════════
def prem_state_get(user_id: int):
    doc = prem_state_col.find_one({"user_id": user_id})
    return {"step": doc["step"], "data": doc.get("data", {})} if doc else None

def prem_state_set(user_id: int, step: str, data: dict):
    prem_state_col.update_one({"user_id": user_id},
        {"$set": {"user_id": user_id, "step": step,
                  "data": data, "updated_at": datetime.now()}}, upsert=True)

def prem_state_del(user_id: int):
    prem_state_col.delete_one({"user_id": user_id})

def prem_state_exists(user_id: int) -> bool:
    return prem_state_col.find_one({"user_id": user_id}, {"_id": 1}) is not None

# ════════ WARNINGS ════════
def add_warn(chat_id: int, user_id: int, reason: str = "", admin_id: int = None) -> int:
    warns_col.insert_one({"chat_id": chat_id, "user_id": user_id,
                          "reason": reason, "admin_id": admin_id, "at": datetime.now()})
    return warns_col.count_documents({"chat_id": chat_id, "user_id": user_id})

def get_warns(chat_id: int, user_id: int) -> int:
    return warns_col.count_documents({"chat_id": chat_id, "user_id": user_id})

def get_warn_reasons(chat_id: int, user_id: int):
    return list(warns_col.find({"chat_id": chat_id, "user_id": user_id},
                               {"reason": 1, "at": 1}))

def reset_warns(chat_id: int, user_id: int):
    warns_col.delete_many({"chat_id": chat_id, "user_id": user_id})

# ════════ NOTES ════════
def save_note(chat_id: int, name: str, content: str, creator_id: int):
    notes_col.update_one({"chat_id": chat_id, "name": name.lower().strip()},
        {"$set": {"chat_id": chat_id, "name": name.lower().strip(),
                  "content": content, "created_by": creator_id,
                  "updated_at": datetime.now()}}, upsert=True)

def get_note(chat_id: int, name: str):
    return notes_col.find_one({"chat_id": chat_id, "name": name.lower().strip()})

def get_all_notes(chat_id: int):
    return list(notes_col.find({"chat_id": chat_id}, {"name": 1}).sort("name", 1))

def delete_note(chat_id: int, name: str):
    notes_col.delete_one({"chat_id": chat_id, "name": name.lower().strip()})

# ════════ FILE HASHES ════════
def store_file_hash(chat_id: int, unique_id: str, file_id: str,
                    original_caption: str, user_id: int):
    file_hashes_col.update_one({"unique_id": unique_id},
        {"$set": {"unique_id": unique_id, "file_id": file_id,
                  "original_caption": original_caption, "chat_id": chat_id,
                  "user_id": user_id, "stored_at": datetime.now()}}, upsert=True)

def find_file_by_unique_id(unique_id: str):
    return file_hashes_col.find_one({"unique_id": unique_id})

# ════════ CAPTCHA ════════
def set_captcha(chat_id: int, user_id: int, answer: str, msg_id: int, word: str = ""):
    expires = datetime.now() + timedelta(minutes=5)   # 5 min to solve
    captcha_col.update_one({"chat_id": chat_id, "user_id": user_id},
        {"$set": {"chat_id": chat_id, "user_id": user_id, "answer": str(answer),
                  "word": word, "msg_id": msg_id, "expires_at": expires,
                  "attempts": 0}}, upsert=True)

def get_captcha(chat_id: int, user_id: int):
    doc = captcha_col.find_one({"chat_id": chat_id, "user_id": user_id})
    if doc and doc["expires_at"] > datetime.now():
        return doc
    if doc:
        captcha_col.delete_one({"_id": doc["_id"]})
    return None

def inc_captcha_attempts(chat_id: int, user_id: int) -> int:
    """Increment unsolicited message attempts. Returns new count."""
    result = captcha_col.find_one_and_update(
        {"chat_id": chat_id, "user_id": user_id},
        {"$inc": {"attempts": 1}},
        return_document=True,
    )
    return result["attempts"] if result else 0

def update_captcha_input(chat_id: int, user_id: int, current_input: str):
    """Store user's current typed captcha input in DB (Vercel-safe, no in-memory)."""
    captcha_col.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"current_input": current_input}},
    )

def get_captcha_input(chat_id: int, user_id: int) -> str:
    """Get user's current typed captcha input from DB."""
    doc = captcha_col.find_one({"chat_id": chat_id, "user_id": user_id})
    return (doc.get("current_input") or "") if doc else ""

def del_captcha(chat_id: int, user_id: int):
    captcha_col.delete_one({"chat_id": chat_id, "user_id": user_id})

# ════════ ANALYTICS ════════
def inc_message_count(chat_id: int, user_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    analytics_col.update_one(
        {"chat_id": chat_id, "user_id": user_id, "date": today},
        {"$inc": {"count": 1}}, upsert=True)

def get_group_stats(chat_id: int) -> dict:
    pipeline = [{"$match": {"chat_id": chat_id}},
                {"$group": {"_id": "$chat_id",
                            "total_messages": {"$sum": "$count"},
                            "active_users": {"$addToSet": "$user_id"}}}]
    result = list(analytics_col.aggregate(pipeline))
    if result:
        r = result[0]
        return {"total_messages": r["total_messages"],
                "active_users": len(r["active_users"])}
    return {"total_messages": 0, "active_users": 0}

def get_top_users(chat_id: int, limit: int = 50):
    pipeline = [{"$match": {"chat_id": chat_id}},
                {"$group": {"_id": "$user_id", "total": {"$sum": "$count"}}},
                {"$sort": {"total": -1}}, {"$limit": limit}]
    return list(analytics_col.aggregate(pipeline))

def get_user_msg_count(chat_id: int, user_id: int) -> int:
    pipeline = [{"$match": {"chat_id": chat_id, "user_id": user_id}},
                {"$group": {"_id": None, "total": {"$sum": "$count"}}}]
    result = list(analytics_col.aggregate(pipeline))
    return result[0]["total"] if result else 0

def save_active_member(chat_id: int, user_id: int):
    groups_col.update_one({"chat_id": chat_id},
        {"$addToSet": {"active_members": user_id}}, upsert=True)

def get_active_members(chat_id: int):
    doc = groups_col.find_one({"chat_id": chat_id}, {"active_members": 1})
    if doc and doc.get("active_members"):
        return [{"user_id": uid} for uid in doc["active_members"]]
    return []

# ════════ GAALI STRIKES ════════
def get_gaali_strikes(chat_id: int, user_id: int) -> int:
    doc = gaali_col.find_one({"chat_id": chat_id, "user_id": user_id})
    return doc["strikes"] if doc else 0

def inc_gaali_strike(chat_id: int, user_id: int) -> int:
    gaali_col.update_one({"chat_id": chat_id, "user_id": user_id},
        {"$inc": {"strikes": 1}, "$set": {"last_at": datetime.now()}}, upsert=True)
    return get_gaali_strikes(chat_id, user_id)

def reset_gaali_strikes(chat_id: int, user_id: int):
    gaali_col.delete_one({"chat_id": chat_id, "user_id": user_id})

# ════════ FLOOD ════════
def is_flooding(chat_id: int, user_id: int, limit: int = 5, window: int = 10) -> bool:
    import time
    now = time.time()
    key = f"{chat_id}:{user_id}"
    _flood.setdefault(key, [])
    _flood[key] = [t for t in _flood[key] if now - t < window]
    _flood[key].append(now)
    return len(_flood[key]) > limit

# ════════ RAID ════════
def record_raid_join(chat_id: int, user_id: int):
    raid_col.insert_one({"chat_id": chat_id, "user_id": user_id,
                         "joined_at": datetime.now()})

def detect_raid(chat_id: int, window_sec: int = 30, threshold: int = 5) -> bool:
    cutoff = datetime.now() - timedelta(seconds=window_sec)
    count  = raid_col.count_documents({"chat_id": chat_id,
                                       "joined_at": {"$gt": cutoff}})
    return count >= threshold

def clear_raid_log(chat_id: int):
    raid_col.delete_many({"chat_id": chat_id})

# ════════ SCHEDULED MESSAGES ════════
def add_scheduled(chat_id: int, text: str, hour: int, minute: int,
                  added_by: int) -> str:
    doc = {"chat_id": chat_id, "text": text, "hour": hour,
           "minute": minute, "added_by": added_by,
           "created_at": datetime.now()}
    return str(scheduled_col.insert_one(doc).inserted_id)

def get_scheduled(chat_id: int):
    return list(scheduled_col.find({"chat_id": chat_id}))

def del_scheduled(sched_id: str):
    from bson import ObjectId
    try:
        scheduled_col.delete_one({"_id": ObjectId(sched_id)})
        return True
    except Exception:
        return False

def get_all_scheduled():
    return list(scheduled_col.find({}))

# ════════ AUTO DELETE ════════
def schedule_delete(chat_id: int, msg_id: int, delete_at: datetime):
    pending_del.insert_one({"chat_id": chat_id, "msg_id": msg_id,
                            "delete_at": delete_at})

def get_pending_deletes():
    return list(pending_del.find({"delete_at": {"$lte": datetime.now()}}))

def remove_pending_delete(chat_id: int, msg_id: int):
    pending_del.delete_one({"chat_id": chat_id, "msg_id": msg_id})

# ════════ TAGALL JOB TRACKING ════════
def set_tagall_job(chat_id: int, message_text: str, user_ids: list,
                   admin_id: int, control_msg_id: int = None):
    tagall_col.update_one({"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "message_text": message_text,
                  "user_ids": user_ids, "current_index": 0,
                  "status": "running", "admin_id": admin_id,
                  "control_msg_id": control_msg_id,
                  "created_at": datetime.now()}}, upsert=True)

def get_tagall_job(chat_id: int):
    return tagall_col.find_one({"chat_id": chat_id})

def pause_tagall(chat_id: int):
    tagall_col.update_one({"chat_id": chat_id},
                          {"$set": {"status": "paused"}})

def resume_tagall(chat_id: int):
    tagall_col.update_one({"chat_id": chat_id},
                          {"$set": {"status": "running"}})

def update_tagall_progress(chat_id: int, current_index: int):
    tagall_col.update_one({"chat_id": chat_id},
                          {"$set": {"current_index": current_index}})

def clear_tagall_job(chat_id: int):
    tagall_col.delete_one({"chat_id": chat_id})

def is_tagall_paused(chat_id: int) -> bool:
    doc = tagall_col.find_one({"chat_id": chat_id}, {"status": 1})
    return doc.get("status") == "paused" if doc else False

# ════════ AI CONTEXT ════════
def push_context(chat_id: int, user_name: str, text: str):
    if not text or len(text) < 2:
        return
    msg = {"user": user_name, "text": text[:200], "at": datetime.now()}
    context_col.update_one({"chat_id": chat_id},
        {"$push": {"messages": {"$each": [msg], "$slice": -6}}}, upsert=True)

def push_bot_reply(chat_id: int, reply: str):
    bot_reply_col.update_one({"chat_id": chat_id},
        {"$push": {"replies": {"$each": [reply], "$slice": -10}}}, upsert=True)

def get_recent_bot_replies(chat_id: int) -> list:
    doc = bot_reply_col.find_one({"chat_id": chat_id})
    return doc.get("replies", []) if doc else []

# ════════ PATTERNS ════════
def add_pattern(trigger: str, response: str, added_by=None):
    trigger  = trigger.strip().lower()[:200]
    response = response.strip()[:500]
    if not trigger or not response:
        return
    patterns_col.update_one({"trigger": trigger},
        {"$addToSet": {"responses": response},
         "$set": {"updated_at": datetime.now(), "added_by": added_by}},
        upsert=True)

def get_best_pattern(text: str):
    text_lower = text.strip().lower()
    doc = patterns_col.find_one({"trigger": text_lower})
    if doc:
        return doc
    docs = list(patterns_col.find({}))
    best, best_len = None, 0
    for d in docs:
        t = d.get("trigger", "")
        if t in text_lower and len(t) > best_len:
            best, best_len = d, len(t)
    return best

def delete_pattern(trigger: str):
    patterns_col.delete_one({"trigger": trigger.strip().lower()})

def get_all_patterns():
    return list(patterns_col.find({}, {"trigger": 1, "responses": 1}))

# ════════ MESSAGES ════════
def save_message(chat_id: int, user_id: int, text: str):
    if not text or len(text) < 3:
        return
    messages_col.insert_one({"chat_id": chat_id, "user_id": user_id,
                              "text": text[:500], "at": datetime.now()})

# ════════ GET_CONTEXT + GET_RECENT_MESSAGES (brain.py needs these) ════════
def get_context(chat_id: int) -> list:
    """Return last 6 messages for a chat (used by AI brain for context)."""
    doc = context_col.find_one({"chat_id": chat_id})
    return doc.get("messages", []) if doc else []

def get_recent_messages(chat_id: int, limit: int = 20) -> list:
    """Return last N messages for a chat (used by learning system)."""
    return list(
        messages_col.find({"chat_id": chat_id})
        .sort("at", DESCENDING)
        .limit(limit)
    )

# ════════ FILTERS ════════
def save_filter(chat_id: int, keyword: str, response: dict):
    """Save a filter response. Multiple responses per keyword supported."""
    keyword = keyword.lower().strip()[:100]
    filters_col.update_one(
        {"chat_id": chat_id, "keyword": keyword},
        {
            "$push": {"responses": response},
            "$set": {"updated_at": datetime.now()},
            "$setOnInsert": {
                "chat_id": chat_id,
                "keyword": keyword,
                "created_at": datetime.now(),
            },
        },
        upsert=True,
    )

def get_filter(chat_id: int, keyword: str):
    keyword = keyword.lower().strip()
    return filters_col.find_one({"chat_id": chat_id, "keyword": keyword})

def get_all_filters(chat_id: int) -> list:
    return list(filters_col.find({"chat_id": chat_id}).sort("keyword", 1))

def delete_filter(chat_id: int, keyword: str) -> bool:
    keyword = keyword.lower().strip()
    result = filters_col.delete_one({"chat_id": chat_id, "keyword": keyword})
    return result.deleted_count > 0

def delete_all_filters(chat_id: int) -> int:
    result = filters_col.delete_many({"chat_id": chat_id})
    return result.deleted_count

def find_matching_filter(chat_id: int, text: str):
    """Find first filter whose keyword appears in the message text."""
    import re as _re
    if not text:
        return None
    text_lower = text.lower()
    all_f = list(filters_col.find({"chat_id": chat_id}, {"keyword": 1, "responses": 1}))
    # Word-boundary match
    for f in all_f:
        kw = f.get("keyword", "")
        if not kw:
            continue
        try:
            if _re.search(r"(?<!\w)" + _re.escape(kw) + r"(?!\w)", text_lower):
                return f
        except Exception:
            if kw in text_lower:
                return f
    return None

# ════════ STICKERS ════════
stickers_col = db["chat_stickers"]

def save_sticker(chat_id: int, file_id: str):
    """Save a sticker file_id for this chat (max 50)."""
    stickers_col.update_one(
        {"chat_id": chat_id},
        {
            "$addToSet": {"file_ids": file_id},
            "$setOnInsert": {"chat_id": chat_id},
        },
        upsert=True,
    )
    # Keep max 50
    stickers_col.update_one(
        {"chat_id": chat_id, "$expr": {"$gt": [{"$size": "$file_ids"}, 50]}},
        {"$pop": {"file_ids": -1}},
    )

def get_stickers(chat_id: int) -> list:
    doc = stickers_col.find_one({"chat_id": chat_id})
    return doc.get("file_ids", []) if doc else []

def remove_sticker(chat_id: int, file_id: str):
    stickers_col.update_one({"chat_id": chat_id}, {"$pull": {"file_ids": file_id}})

def clear_stickers(chat_id: int):
    stickers_col.delete_one({"chat_id": chat_id})

# ════════ MOVIE REQUESTS (tag users who asked for this movie today) ════════
movie_requests_col = db["movie_requests"]
# Auto-delete movie requests after 2 days (tagging is only for today anyway)
try:
    movie_requests_col.create_index("requested_at", expireAfterSeconds=2 * 24 * 3600, background=True)
except Exception:
    pass

def save_movie_request(chat_id: int, user_id: int, user_name: str, query: str):
    movie_requests_col.insert_one({
        "chat_id": chat_id, "user_id": user_id,
        "user_name": user_name, "query": query.lower().strip(),
        "requested_at": datetime.now(),
    })

def get_requesters_today(chat_id: int, movie_key: str) -> list:
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    reqs = list(movie_requests_col.find({
        "chat_id": chat_id, "requested_at": {"$gte": today_start},
    }))
    movie_lower = movie_key.lower()

    # ── Extract meaningful words from movie name (skip filler words) ──
    _SKIP = {"the", "and", "or", "of", "in", "a", "an", "to", "is", "it",
              "ke", "ka", "ki", "ko", "se", "hai", "tha", "thi", "ho", "na"}
    movie_words = [
        w for w in re.split(r'\s+', movie_lower)
        if len(w) >= 3 and w not in _SKIP
    ]

    seen, matched = set(), []
    for r in reqs:
        q = r.get("query", "")
        if len(q) < 2:
            continue
        q_lower = q.lower()

        # Method 1: direct substring (e.g. "pushpa 2" in "pushpa 2 the rule")
        is_match = (q_lower in movie_lower or movie_lower in q_lower)

        # Method 2: word-overlap — any movie word found in query text
        # Handles "pushpa 2 chahiye", "yaar dunki upload karo", etc.
        if not is_match and movie_words:
            is_match = any(
                re.search(r'\b' + re.escape(w) + r'\b', q_lower)
                for w in movie_words
            )

        if is_match:
            uid = r["user_id"]
            if uid not in seen:
                seen.add(uid)
                matched.append(r)

    return matched[:8]

# ════════ FILE FORWARD CACHE (1 day) ════════
forward_cache_col = db["forward_cache"]

def save_forward_cache(caption_key: str, unique_id: str, file_id: str, is_doc: bool):
    forward_cache_col.update_one(
        {"caption_key": caption_key},
        {"$set": {
            "caption_key": caption_key, "unique_id": unique_id,
            "file_id": file_id, "is_doc": is_doc,
            "cached_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24),
        }},
        upsert=True,
    )

def get_forward_cache(caption_key: str):
    return forward_cache_col.find_one({
        "caption_key": caption_key,
        "expires_at": {"$gt": datetime.now()},
    })

# ════════ BIO PERMISSIONS ════════
bio_perm_col = db["bio_permissions"]

def grant_bio_perm(chat_id: int, user_id: int):
    bio_perm_col.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"chat_id": chat_id, "user_id": user_id, "granted_at": datetime.now()}},
        upsert=True,
    )

def has_bio_perm(chat_id: int, user_id: int) -> bool:
    return bio_perm_col.find_one({"chat_id": chat_id, "user_id": user_id}) is not None

def revoke_bio_perm(chat_id: int, user_id: int):
    bio_perm_col.delete_one({"chat_id": chat_id, "user_id": user_id})

# ════════ CAPTCHA TOKENS (new PM-based verification flow) ════════
captcha_token_col = db["captcha_tokens"]

def set_captcha_token(chat_id: int, user_id: int, token: str, msg_id: int):
    captcha_token_col.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {
            "chat_id": chat_id, "user_id": user_id,
            "token": token, "msg_id": msg_id,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=5),
        }},
        upsert=True,
    )

def get_captcha_token_doc(chat_id: int, user_id: int):
    return captcha_token_col.find_one({"chat_id": chat_id, "user_id": user_id})

def get_captcha_token_by_user(user_id: int):
    """Find any pending captcha for this user across ALL groups — used for PM verification."""
    return captcha_token_col.find_one({
        "user_id": user_id,
        "expires_at": {"$gt": datetime.now()},   # only non-expired
    })

def del_captcha_token(chat_id: int, user_id: int):
    captcha_token_col.delete_one({"chat_id": chat_id, "user_id": user_id})

# ════════ GLOBAL STICKER PACKS (owner sets from PM) ════════
global_stickers_col = db["global_stickers"]

def save_global_stickers(file_ids: list):
    global_stickers_col.delete_many({})   # replace old pack
    if file_ids:
        global_stickers_col.insert_many([{"file_id": fid} for fid in file_ids])

def get_global_stickers() -> list:
    return [d["file_id"] for d in global_stickers_col.find({}, {"file_id": 1})]


# ════════════════════════════════════════════════════════
# CLEANUP — Delete stale data so MongoDB stays lean
# Call this probabilistically on every request (1% chance)
# so old data auto-removes without a cron job on Vercel
# ════════════════════════════════════════════════════════

def cleanup_old_data():
    """
    Remove expired / stale records from MongoDB.
    Vercel mein cron nahi hai — isliye har request pe 1% chance pe run karo.
    
    Kya delete hota hai:
      messages_col      → 7+ din purane messages (learning data)
      movie_requests_col→ 2+ din purane requests (daily tagging done)
      captcha_col       → expired captchas (5 min ke baad)
      captcha_token_col → expired tokens (5 min ke baad)
    """
    try:
        now = datetime.now()
        # 1. Group messages older than 7 days
        messages_col.delete_many({
            "at": {"$lt": now - timedelta(days=7)}
        })
        # 2. Movie requests older than 2 days
        movie_requests_col.delete_many({
            "requested_at": {"$lt": now - timedelta(days=2)}
        })
        # 3. Expired captchas
        captcha_col.delete_many({
            "expires_at": {"$lt": now}
        })
        # 4. Expired captcha tokens
        captcha_token_col.delete_many({
            "expires_at": {"$lt": now}
        })
    except Exception:
        pass   # Cleanup failure should never crash the bot
