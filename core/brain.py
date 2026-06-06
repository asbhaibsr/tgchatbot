import random
import re
from core.db import (
    add_pattern, get_best_pattern, find_pattern,
    get_random_response, delete_pattern, get_all_patterns,
    save_message, get_recent_messages
)

# ── Desi ladki ke natural reply templates ─────────────────────────────

_GIRL_REPLIES = [
    "haan ji bolo~ 🌸",
    "kya hua? 👀",
    "achha achha samjhi main~ 😄",
    "arey sach mein?? 😮",
    "yeh toh mujhe pata hi tha 💅",
    "hmm... soch rahi hoon 🤔",
    "OMG haan bilkul yaar! 💘",
    "nahi nahi aise nahi hota 😤",
    "chalo theek hai maan leti hoon 🙄",
    "waah kya baat hai 😍",
    "haye kitna cute ❤️",
    "pagal ho gaye ho kya 😂",
    "main to yahi sochti thi 🌸",
    "shukar hai kisi ne toh kuch bola 😂",
    "bilkul sahi kaha! 💯",
    "arey mujhe bhi batao na 🥺",
    "yeh toh hona hi tha 😏",
    "kyun tease karte ho mujhe 😒",
    "aww kitna pyara 🥺💘",
    "chai pi lo thodi relax karo 😄☕",
]

_CONFUSED_REPLIES = [
    "samjha nahi properly, dobara batao? 😅",
    "matlab? 🤔 thoda explain karo",
    "hain?? yeh kya tha 😂",
    "arey yaar abhi to dimaag kaam nahi kar raha 🥴",
    "okay wait mujhe thoda sochne do... 💭",
]

_GREETING_PATTERNS = {
    "hi": ["heyy~ 🌸", "hi hi! 💘", "haan ji! 😊", "hello jaan~ 🌺"],
    "hello": ["heyy! kya haal hai? 🌸", "hello hello~ 💘", "ji ji bolo 😄"],
    "hey": ["heyy! 😍", "heyyy~ kya chal raha hai 👀", "bolo bolo 🌸"],
    "hlo": ["heyy~ 🌸", "hello! 💘"],
    "hii": ["hiiii~ 😄💘", "heyy! 🌸"],
    "kya haal": ["main theek hoon yaar, tum batao? 🌸", "achha hoon main~ aap? 😊"],
    "kaise ho": ["main bilkul mast hoon 😄 tum batao?", "theek hoon~ aap kaise? 🌸"],
    "good morning": ["good morning! ☀️ aaj ka din acha ho tumhara~ 🌸", "morning! ☕ chai pi lo 😄"],
    "good night": ["good night~ 🌙 meethe sapne aana! 💘", "shubh ratri~ 🌙✨"],
    "bye": ["byee~ 💘 wapas aana jaldi!", "bye bye! 🌸 miss karenge~"],
    "thanks": ["arrey mention mat karo 🌸", "koi baat nahi jaan~ 💘", "yeh toh banta tha 😄"],
    "ok": ["okay~ 🌸", "theek hai 😊", "accha ji 👍"],
    "haha": ["hehe~ 😄", "😂 haan bahut funny tha!", "arey itna hasna mat 😂💘"],
    "lol": ["hahahaha 😂😂", "LOL same yaar 😂", "kyun itna hansa? 😄"],
}

# ── Do users ke beech conversation se seekhna ─────────────────────────

def learn_from_conversation(msg1_text: str, msg2_text: str, user1_id=None, user2_id=None):
    """
    User1 ne kuch kaha → User2 ne reply kiya
    Ye pattern store karo
    """
    if not msg1_text or not msg2_text:
        return False
    trigger = msg1_text.strip().lower()
    response = msg2_text.strip()
    # Bohot chhote ya generic messages skip karo
    if len(trigger) < 2 or len(response) < 1:
        return False
    # URLs aur commands skip karo
    if trigger.startswith("/") or "http" in trigger:
        return False
    add_pattern(trigger, response, added_by=user1_id)
    return True

# ── Bot ko reply karne se seekhna ─────────────────────────────────────

def learn_from_bot_reply(bot_msg_text: str, user_reply_text: str):
    """
    Bot ne kuch kaha → User ne reply kiya
    Bot ko samjhna chahiye ki uske message pe kya response aata hai
    """
    if not bot_msg_text or not user_reply_text:
        return False
    add_pattern(bot_msg_text.strip(), user_reply_text.strip())
    return True

# ── Admin se seekhna ─────────────────────────────────────────────────

def learn_from_reply(replied_to_text: str, response_text: str, admin_id: int):
    """Admin ne apna message reply kiya"""
    if not replied_to_text or not response_text:
        return False
    trigger  = replied_to_text.strip()
    response = response_text.strip()
    if len(trigger) < 2 or len(response) < 1:
        return False
    add_pattern(trigger, response, added_by=admin_id)
    return True

# ── /teach command ────────────────────────────────────────────────────

def teach_pattern(text: str, admin_id: int):
    if "|" not in text:
        return False, None, None
    parts    = text.split("|", 1)
    trigger  = parts[0].strip()
    response = parts[1].strip()
    if not trigger or not response:
        return False, None, None
    add_pattern(trigger, response, added_by=admin_id)
    return True, trigger, response

# ── Smart reply dhundna ───────────────────────────────────────────────

def find_reply(text: str):
    """
    1. DB mein best pattern dhundo
    2. Greeting patterns check karo
    3. Koi match nahi → smart girl reply banao
    """
    if not text:
        return None

    text_lower = text.lower().strip()

    # 1. DB pattern check
    pattern = get_best_pattern(text)
    if pattern:
        responses = pattern.get("responses", [])
        if responses:
            return random.choice(responses)

    # 2. Built-in greeting patterns
    for keyword, replies in _GREETING_PATTERNS.items():
        if keyword in text_lower:
            return random.choice(replies)

    # 3. Question detect karo
    if any(q in text_lower for q in ["kya", "kaun", "kahan", "kab", "kyun", "kaise", "?"]):
        return _make_question_reply(text_lower)

    # 4. Emotional keywords
    if any(w in text_lower for w in ["sad", "dukhi", "rona", "bura", "takleef", "pareshan"]):
        return random.choice([
            "aww kya hua? 🥺 bolo mujhe~",
            "arre kya chal raha hai? theek ho tum? 💘",
            "yaar sab theek ho jayega 🌸 main hoon na~",
        ])

    if any(w in text_lower for w in ["khush", "maza", "accha", "badhiya", "great", "awesome"]):
        return random.choice([
            "yayy bahut achha! 🎉💘",
            "aww itna achha sun ke dil khush ho gaya 🌸",
            "bahut badhiya yaar! main bhi khush hoon 😄",
        ])

    return None

def _make_question_reply(text: str) -> str:
    """Question ka smart reply"""
    if "kya" in text or "?" in text:
        return random.choice([
            "hmm yeh toh achha sawaal hai 🤔",
            "sochne wali baat hai... 💭",
            "arey mujhe bhi nahi pata honestly 😅",
            "main bhi yahi soch rahi thi 😄",
        ])
    if "kahan" in text:
        return random.choice(["wahan jo hona chahiye wahan 😄", "pata nahi yaar 🤷‍♀️"])
    if "kab" in text:
        return random.choice(["jab hona hoga 😏", "abhi nahi thodi der mein 😄"])
    return random.choice(_GIRL_REPLIES)

def make_girl_reply(text: str = "") -> str:
    """Jab koi pattern na mile — asli ladki ki tarah reply karo"""
    if not text:
        return random.choice(_GIRL_REPLIES)

    text_lower = text.lower()

    # Length check
    if len(text_lower) < 4:
        return random.choice(["hmm? 🌸", "haan? 👀", "bolo~ 💘"])

    # Match karo
    result = find_reply(text)
    if result:
        return result

    return random.choice(_GIRL_REPLIES)

# ── DELETE / LIST ─────────────────────────────────────────────────────

def forget_pattern(trigger: str):
    delete_pattern(trigger)

def list_patterns():
    return get_all_patterns()
