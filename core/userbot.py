"""
userbot.py — Pyrogram session se groups ke conversations seekhna

2 modes:
  1. batch_learn_from_groups()  → /learnfromgroups command pe chalta hai
                                  Saare joined groups se patterns DB mein save karta hai
                                  Ek baar chalao → bot hamesha ke liye seekh jaata hai

  2. search_group_reply()       → fallback (jab DB mein koi pattern na mile)
                                  Quick search, result bhi DB mein cache ho jaata hai

Vercel safe: koi persistent connection nahi — sirf jab command aaye tab connect karo.
"""
import os, re, asyncio
from typing import Optional

API_ID   = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION  = os.environ.get("USERBOT_SESSION", "")

_SEARCH_TIMEOUT = 8.0   # max seconds for quick search (Vercel 10s limit ke under)
_BATCH_TIMEOUT  = 55.0  # max seconds for batch learn (Vercel 60s limit ke under)
_MAX_GROUPS     = 20    # kitne groups se seekhna hai
_HISTORY_LIMIT  = 300   # har group mein kitne messages padhna hai


# ── Helper: bekar messages skip karo ──────────────────────────────
_SKIP_WORDS = {
    "haan","nahi","ok","okay","hmm","ha","na","haa","kya","hi","bye","ty",
    "thnx","bhai","yaar","ji","lol","haha","😂","❤️","🔥","💯",
}

def _is_junk(text: str) -> bool:
    if not text or len(text.strip()) < 3:
        return True
    if text.startswith("/") or text.startswith("@"):
        return True
    if "http" in text.lower() or "t.me/" in text.lower():
        return True
    # Sirf emoji ya ek word
    clean = text.strip("😂🌸💘😄👀🥺❤️✅❌🔥💯😭😍🎉🥳 \n")
    if len(clean) < 2:
        return True
    return False

def _clean(text: str) -> str:
    text = text.strip()
    # Remove @mentions aur extra spaces
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:400]

def _word_overlap(a: str, b: str) -> int:
    stop = {
        "hai","ka","ki","ko","ke","me","mai","main","hain","tha","thi","the",
        "aur","or","to","na","nhi","nahi","kya","bhai","yaar","ok","okay",
        "a","an","is","in","it","the","and","for","of","with","this","that"
    }
    wa = {w for w in a.lower().split() if len(w) > 2 and w not in stop}
    wb = {w for w in b.lower().split() if len(w) > 2 and w not in stop}
    return len(wa & wb)


# ── Core: ek group se saare reply patterns seedhna ──────────────────
async def _learn_one_group(client, chat_id: int, limit: int = _HISTORY_LIMIT) -> int:
    """
    Ek group ki history padhke reply patterns DB mein save karo.
    Sirf 1 API call (get_chat_history) — efficient.
    Returns: kitne patterns save hue
    """
    from core.brain import learn_from_conversation

    msg_dict = {}       # {msg_id: cleaned_text}
    reply_pairs = []    # [(orig_msg_id, reply_text)]

    try:
        async for msg in client.get_chat_history(chat_id, limit=limit):
            if not msg or not msg.text:
                continue
            txt = _clean(msg.text)
            if _is_junk(txt):
                continue
            msg_dict[msg.id] = txt
            if msg.reply_to_message_id:
                reply_pairs.append((msg.reply_to_message_id, txt))
    except Exception:
        return 0

    # Match reply pairs — no extra API calls
    count = 0
    for orig_id, reply_text in reply_pairs:
        orig_text = msg_dict.get(orig_id)
        if orig_text and not _is_junk(orig_text):
            if learn_from_conversation(orig_text, reply_text):
                count += 1

    return count


# ── PUBLIC: Batch learning — /learnfromgroups command ──────────────
async def batch_learn_from_groups(status_callback=None) -> dict:
    """
    Saare joined groups se conversations seekhkar MongoDB mein save karo.
    status_callback(msg) → progress updates Telegram mein bhejne ke liye (optional).

    Returns: {"groups": N, "patterns": M, "error": None}
    """
    if not all([API_ID, API_HASH, SESSION]):
        return {"groups": 0, "patterns": 0,
                "error": "API_ID / API_HASH / USERBOT_SESSION set nahi hai Vercel env mein"}

    result = {"groups": 0, "patterns": 0, "error": None}

    try:
        from pyrogram import Client
        from pyrogram.enums import ChatType
    except ImportError:
        return {"groups": 0, "patterns": 0, "error": "pyrogram install nahi: pip install pyrogram"}

    try:
        async with Client(
            name="ub_batch",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=SESSION,
            in_memory=True,
            no_updates=True,
        ) as client:

            # Saare groups collect karo
            group_ids = []
            async for dialog in client.get_dialogs(limit=50):
                if dialog.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                    group_ids.append((dialog.chat.id, dialog.chat.title or str(dialog.chat.id)))
                if len(group_ids) >= _MAX_GROUPS:
                    break

            if not group_ids:
                return {"groups": 0, "patterns": 0, "error": "Koi group nahi mila session mein"}

            if status_callback:
                await status_callback(
                    f"⋘ 𝑙𝑒𝑎𝑟𝑛𝑖𝑛𝑔... ⋙\n"
                    f"{len(group_ids)} groups mila — shuru kar raha hoon..."
                )

            total_patterns = 0
            for i, (gid, gtitle) in enumerate(group_ids, 1):
                try:
                    count = await _learn_one_group(client, gid)
                    total_patterns += count
                    result["groups"] += 1

                    if status_callback and count > 0:
                        pct = int(i / len(group_ids) * 100)
                        bar = "█" * (pct // 10) + "▒" * (10 - pct // 10)
                        await status_callback(
                            f"{bar} {pct}%\n"
                            f"✅ {gtitle[:30]} → {count} patterns"
                        )
                except Exception:
                    continue

            result["patterns"] = total_patterns

    except Exception as e:
        result["error"] = str(e)

    return result


# ── PUBLIC: Quick fallback search + cache ───────────────────────────
async def search_group_reply(text: str) -> Optional[str]:
    """
    Quick search: userbot groups mein text jaisa conversation dhundho.
    Match milne pe DB mein cache karo + return karo.
    Timeout: 8 seconds (Vercel free limit ke under).
    """
    if not all([API_ID, API_HASH, SESSION]):
        return None
    if _is_junk(text):
        return None

    try:
        return await asyncio.wait_for(_quick_search(text), timeout=_SEARCH_TIMEOUT)
    except asyncio.TimeoutError:
        return None
    except Exception as e:
        print(f"[USERBOT] search error: {e}")
        return None


async def _quick_search(text: str) -> Optional[str]:
    try:
        from pyrogram import Client
        from pyrogram.enums import ChatType
        from core.brain import learn_from_conversation
    except ImportError:
        return None

    text_lower = text.lower().strip()

    async with Client(
        name="ub_quick",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION,
        in_memory=True,
        no_updates=True,
    ) as client:

        group_ids = []
        async for dialog in client.get_dialogs(limit=30):
            if dialog.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                group_ids.append(dialog.chat.id)
            if len(group_ids) >= 10:
                break

        best_reply = None

        for gid in group_ids:
            msg_dict = {}
            reply_pairs = []
            try:
                async for msg in client.get_chat_history(gid, limit=150):
                    if not msg or not msg.text:
                        continue
                    txt = _clean(msg.text)
                    if _is_junk(txt):
                        continue
                    msg_dict[msg.id] = txt
                    if msg.reply_to_message_id:
                        reply_pairs.append((msg.reply_to_message_id, txt))
            except Exception:
                continue

            # Find best matching pair + cache ALL pairs found
            for orig_id, reply_text in reply_pairs:
                orig_text = msg_dict.get(orig_id)
                if not orig_text:
                    continue
                # Cache in DB regardless of match
                learn_from_conversation(orig_text, reply_text)
                # Check if this is the reply we need
                if best_reply is None:
                    overlap = _word_overlap(orig_text, text_lower)
                    exact   = text_lower in orig_text.lower()
                    if exact or overlap >= 2:
                        best_reply = reply_text

        return best_reply


# ── PUBLIC: Session check ───────────────────────────────────────────
async def check_session() -> dict:
    if not all([API_ID, API_HASH, SESSION]):
        return {"active": False, "reason": "API_ID / API_HASH / USERBOT_SESSION missing"}
    try:
        from pyrogram import Client
        from pyrogram.enums import ChatType
        async with Client(
            name="ub_check",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=SESSION,
            in_memory=True,
            no_updates=True,
        ) as client:
            me     = await client.get_me()
            groups = 0
            async for dialog in client.get_dialogs(limit=100):
                if dialog.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                    groups += 1
            return {
                "active": True,
                "name":   f"{me.first_name or ''} {me.last_name or ''}".strip(),
                "phone":  me.phone_number or "N/A",
                "groups": groups,
            }
    except Exception as e:
        return {"active": False, "reason": str(e)}
