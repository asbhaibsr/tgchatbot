"""
Self-Learning Brain
─────────────────────────────────────────────
Sikhne ka tarika:
  Admin apne message ko khud reply kare →
  Bot samjhti hai: "jo message reply kiya gaya = trigger,
                    jo reply likhi = response"

  /teach trigger | response  →  direct pattern add

Ek trigger ke kai responses ho sakte hain.
Reply aate waqt sabse lamba matching pattern use hota hai.
"""

from core.db import (
    add_pattern, get_best_pattern,
    get_random_response, delete_pattern, get_all_patterns
)

# ─── ADMIN SE SEEKHNA ─────────────────────────────────────────────────

def learn_from_reply(replied_to_text: str, response_text: str, admin_id: int):
    """
    Admin ne apna hi message reply kiya →
    replied_to_text = trigger
    response_text   = response
    """
    if not replied_to_text or not response_text:
        return False
    trigger  = replied_to_text.strip()
    response = response_text.strip()
    if len(trigger) < 2 or len(response) < 1:
        return False
    add_pattern(trigger, response, added_by=admin_id)
    return True

# ─── /teach command ──────────────────────────────────────────────────

def teach_pattern(text: str, admin_id: int):
    """
    Format: trigger | response
    Returns (success, trigger, response)
    """
    if "|" not in text:
        return False, None, None
    parts    = text.split("|", 1)
    trigger  = parts[0].strip()
    response = parts[1].strip()
    if not trigger or not response:
        return False, None, None
    add_pattern(trigger, response, added_by=admin_id)
    return True, trigger, response

# ─── REPLY DHUNDNA ───────────────────────────────────────────────────

def find_reply(text: str):
    """
    Text mein best matching pattern dhundho,
    agar mila toh random response do, warna None
    """
    pattern = get_best_pattern(text)
    if not pattern:
        return None
    return get_random_response(pattern)

# ─── DELETE PATTERN ───────────────────────────────────────────────────

def forget_pattern(trigger: str):
    delete_pattern(trigger)

# ─── LIST ALL ────────────────────────────────────────────────────────

def list_patterns():
    return get_all_patterns()
