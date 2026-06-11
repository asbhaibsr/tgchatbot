import os
import asyncio
import re
from typing import Optional

API_ID   = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION  = os.environ.get("USERBOT_SESSION", "")

_SEARCH_TIMEOUT = 4.0   # max seconds to wait for userbot search
_MAX_GROUPS     = 15    # max groups to search
_HISTORY_LIMIT  = 80    # messages to read per group


def _is_junk(text: str) -> bool:
    """True if text is too short, a command, or just emoji."""
    if not text or len(text.strip()) < 3:
        return True
    if text.startswith("/"):
        return True
    if len(text.strip("😂🌸💘😄👀🥺❤️✅❌🔥💯😭😍🎉🥳 \n")) < 2:
        return True
    return False


def _word_overlap(a: str, b: str) -> int:
    """Count meaningful words in common between two texts."""
    stop = {"hai", "ka", "ki", "ko", "ke", "me", "mai", "main", "hain",
            "tha", "thi", "the", "aur", "or", "to", "na", "nhi", "nahi",
            "kya", "bhai", "yaar", "ok", "okay", "a", "an", "is", "in",
            "it", "the", "and", "for", "of", "with", "this", "that"}
    wa = {w for w in a.lower().split() if len(w) > 2 and w not in stop}
    wb = {w for w in b.lower().split() if len(w) > 2 and w not in stop}
    return len(wa & wb)


async def _do_search(text: str) -> Optional[str]:
    """Core search — runs inside asyncio.wait_for."""
    try:
        from pyrogram import Client
        from pyrogram.enums import ChatType
    except ImportError:
        print("[USERBOT] pyrogram not installed")
        return None

    text_lower = text.lower().strip()

    async with Client(
        name="ub_search",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION,
        in_memory=True,
        no_updates=True,          # don't receive updates, only make requests
    ) as client:

        # ── Step 1: Collect group chat IDs ──────────────────
        group_ids: list[int] = []
        async for dialog in client.get_dialogs(limit=40):
            if dialog.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                group_ids.append(dialog.chat.id)
            if len(group_ids) >= _MAX_GROUPS:
                break

        if not group_ids:
            return None

        # ── Step 2: Search each group ────────────────────────
        for chat_id in group_ids:
            try:
                # Fetch recent reply-messages from group history
                reply_msgs: list = []
                async for msg in client.get_chat_history(chat_id, limit=_HISTORY_LIMIT):
                    if msg.reply_to_message_id and msg.text and not _is_junk(msg.text):
                        reply_msgs.append(msg)

                # For each reply, get original message and check similarity
                for reply_msg in reply_msgs:
                    try:
                        orig = await client.get_messages(chat_id, reply_msg.reply_to_message_id)
                        if not orig or not orig.text:
                            continue
                        overlap = _word_overlap(orig.text, text_lower)
                        exact   = text_lower in orig.text.lower()
                        if exact or overlap >= 2:
                            result = reply_msg.text.strip()
                            if _is_junk(result):
                                continue
                            # ── Cache this pattern in DB ──────
                            try:
                                from core.db import add_pattern
                                add_pattern(orig.text.lower().strip(), result)
                            except Exception:
                                pass
                            return result
                    except Exception:
                        continue

            except Exception:
                continue

    return None


async def search_group_reply(text: str) -> Optional[str]:
    """
    Public API: Search userbot groups for a reply to `text`.
    Returns the reply text or None.
    Has a hard timeout of _SEARCH_TIMEOUT seconds.
    """
    if not all([API_ID, API_HASH, SESSION]):
        return None
    if _is_junk(text):
        return None
    try:
        return await asyncio.wait_for(_do_search(text), timeout=_SEARCH_TIMEOUT)
    except asyncio.TimeoutError:
        print(f"[USERBOT] Search timeout for: {text[:40]}")
        return None
    except Exception as e:
        print(f"[USERBOT] Error: {e}")
        return None


async def check_session() -> dict:
    """
    Check if string session is valid.
    Returns dict: {active: bool, name: str, phone: str, groups: int}
    """
    if not all([API_ID, API_HASH, SESSION]):
        return {
            "active": False,
            "reason": "API_ID / API_HASH / USERBOT_SESSION set nahi hai",
        }
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
            me      = await client.get_me()
            groups  = 0
            async for dialog in client.get_dialogs(limit=50):
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
