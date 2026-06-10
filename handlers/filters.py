import os
import re
import random
from datetime import datetime

from telegram import (
    Update, Message,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

from core.db import (
    save_filter,
    get_filter,
    get_all_filters,
    delete_filter,
    delete_all_filters,
    find_matching_filter,
)

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

async def _is_user_admin(context, chat_id: int, user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        m = await context.bot.get_chat_member(chat_id, user_id)
        return m.status in ("administrator", "creator")
    except Exception:
        return False


def _extract_keyword(text: str):
    """
    Parse keyword + rest from filter command args.
    Supports:
      'multi word keyword' rest text
      "multi word keyword" rest text
      singleword rest text
    Returns (keyword_lower, rest_text)
    """
    text = text.strip()
    if text.startswith("'"):
        end = text.find("'", 1)
        if end != -1:
            return text[1:end].lower().strip(), text[end + 1:].strip()
    elif text.startswith('"'):
        end = text.find('"', 1)
        if end != -1:
            return text[1:end].lower().strip(), text[end + 1:].strip()
    parts = text.split(None, 1)
    if parts:
        return parts[0].lower(), parts[1].strip() if len(parts) > 1 else ""
    return None, None


def _parse_buttons(text: str):
    """
    Parse [Button Text](url_or_callback) syntax from text.
    Buttons on the SAME LINE become the same row.
    Returns (clean_text_without_buttons, button_rows_list)

    Example:
      "Hello!\n[Visit Us](https://t.me/ch)\n[Web](https://example.com) [More](https://ex.com)"
      →  clean = "Hello!"
         rows  = [[{url btn}], [{url btn}, {url btn}]]
    """
    if not text:
        return text, []

    btn_re = re.compile(r'\[([^\[\]\n]+)\]\(([^()\n]+)\)')
    lines = text.split("\n")
    clean_lines = []
    button_rows = []

    for line in lines:
        matches = list(btn_re.finditer(line))
        if matches:
            row = []
            for m in matches:
                btn_label = m.group(1).strip()
                btn_data  = m.group(2).strip()
                if btn_data.startswith(("http://", "https://", "tg://")):
                    row.append({"text": btn_label, "url": btn_data})
                else:
                    # callback button (max 64 chars)
                    row.append({"text": btn_label, "callback": btn_data[:64]})
            if row:
                button_rows.append(row)
            # Remove button syntax from line; keep any non-button text
            line_clean = btn_re.sub("", line).strip()
            if line_clean:
                clean_lines.append(line_clean)
        else:
            clean_lines.append(line)

    clean_text = "\n".join(clean_lines).strip()
    return clean_text, button_rows


def _build_markup(button_rows: list):
    """Convert button_rows list → InlineKeyboardMarkup (or None)."""
    if not button_rows:
        return None
    keyboard = []
    for row in button_rows:
        kb_row = []
        for btn in row:
            if "url" in btn:
                kb_row.append(InlineKeyboardButton(btn["text"], url=btn["url"]))
            else:
                cb = btn.get("callback", "filter_noop")
                kb_row.append(InlineKeyboardButton(btn["text"], callback_data=cb))
        if kb_row:
            keyboard.append(kb_row)
    return InlineKeyboardMarkup(keyboard) if keyboard else None


async def _send_filter_response(message: Message, response: dict):
    """Send one filter response object to the given message."""
    text       = response.get("text") or ""
    media_type = response.get("media_type")       # None | photo|sticker|document|video|audio|animation|voice
    file_id    = response.get("file_id")
    btn_rows   = response.get("buttons", [])
    markup     = _build_markup(btn_rows)

    try:
        if media_type == "photo":
            await message.reply_photo(
                photo=file_id,
                caption=text or None,
                parse_mode="HTML",
                reply_markup=markup,
            )
        elif media_type == "sticker":
            await message.reply_sticker(sticker=file_id)
            if text or markup:
                await message.reply_text(
                    text or "⬆️",
                    parse_mode="HTML",
                    reply_markup=markup,
                )
        elif media_type == "document":
            await message.reply_document(
                document=file_id,
                caption=text or None,
                parse_mode="HTML",
                reply_markup=markup,
            )
        elif media_type == "video":
            await message.reply_video(
                video=file_id,
                caption=text or None,
                parse_mode="HTML",
                reply_markup=markup,
            )
        elif media_type == "audio":
            await message.reply_audio(
                audio=file_id,
                caption=text or None,
                parse_mode="HTML",
                reply_markup=markup,
            )
        elif media_type == "animation":
            await message.reply_animation(
                animation=file_id,
                caption=text or None,
                parse_mode="HTML",
                reply_markup=markup,
            )
        elif media_type == "voice":
            await message.reply_voice(
                voice=file_id,
                caption=text or None,
                parse_mode="HTML",
                reply_markup=markup,
            )
        elif text:
            await message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )
    except Exception as e:
        print(f"[FILTER SEND ERROR] {e}")


# ══════════════════════════════════════════════════════════
# /filter  —  Add a filter
# ══════════════════════════════════════════════════════════

_FILTER_USAGE = (
    "❌ <b>Usage:</b>\n\n"
    "<b>Text filter:</b>\n"
    "<code>/filter 'keyword' jawab text yahan</code>\n\n"
    "<b>Multi-word keyword:</b>\n"
    "<code>/filter 'hello world' Namaste bhai!</code>\n\n"
    "<b>Media filter</b> (kisi photo/sticker/file ko reply karo):\n"
    "<code>/filter 'keyword'</code>  ← reply karke\n\n"
    "<b>Buttons add karne ke liye text mein likho:</b>\n"
    "<code>/filter 'hi' Namaste!\n"
    "[Channel](https://t.me/ch) [Website](https://example.com)\n"
    "[Help](https://t.me/bot)</code>\n\n"
    "<i>Ek keyword ke liye kai baar /filter lagao — random se reply ayega!</i>"
)


async def filter_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message

    if chat.type == "private":
        await message.reply_text("❌ Filters sirf groups mein use hote hain!")
        return

    if not await _is_user_admin(context, chat.id, user.id):
        await message.reply_text("❌ Sirf admins filter laga sakte hain!")
        return

    if not context.args:
        await message.reply_text(_FILTER_USAGE, parse_mode="HTML")
        return

    args_text = " ".join(context.args)
    keyword, rest = _extract_keyword(args_text)

    if not keyword:
        await message.reply_text(_FILTER_USAGE, parse_mode="HTML")
        return

    if len(keyword) > 100:
        await message.reply_text("❌ Keyword max 100 characters ka hona chahiye!")
        return

    # ── Determine media from replied message ─────────────
    reply_msg  = message.reply_to_message
    media_type = None
    file_id    = None
    text       = rest   # text from command args (may include button syntax)

    if reply_msg:
        if reply_msg.photo:
            media_type = "photo"
            file_id    = reply_msg.photo[-1].file_id
            text       = rest or reply_msg.caption or ""
        elif reply_msg.sticker:
            media_type = "sticker"
            file_id    = reply_msg.sticker.file_id
            text       = rest or ""
        elif reply_msg.document:
            media_type = "document"
            file_id    = reply_msg.document.file_id
            text       = rest or reply_msg.caption or ""
        elif reply_msg.video:
            media_type = "video"
            file_id    = reply_msg.video.file_id
            text       = rest or reply_msg.caption or ""
        elif reply_msg.audio:
            media_type = "audio"
            file_id    = reply_msg.audio.file_id
            text       = rest or reply_msg.caption or ""
        elif reply_msg.animation:
            media_type = "animation"
            file_id    = reply_msg.animation.file_id
            text       = rest or reply_msg.caption or ""
        elif reply_msg.voice:
            media_type = "voice"
            file_id    = reply_msg.voice.file_id
            text       = rest or reply_msg.caption or ""
        elif reply_msg.text and not rest:
            text = reply_msg.text   # fallback: use replied text

    if not media_type and not text:
        await message.reply_text(
            "❌ Response dena padega!\n"
            "Ya toh text likho ya kisi media ko reply karo.\n\n"
            + _FILTER_USAGE,
            parse_mode="HTML",
        )
        return

    # ── Parse inline buttons from text ───────────────────
    clean_text, button_rows = _parse_buttons(text)

    response = {
        "text":       clean_text,
        "media_type": media_type,
        "file_id":    file_id,
        "buttons":    button_rows,
        "added_by":   user.id,
        "added_at":   datetime.now().isoformat(),
    }

    save_filter(chat.id, keyword, response)

    # ── Confirmation message ──────────────────────────────
    type_icon = {
        "photo":     "🖼",
        "sticker":   "😄",
        "document":  "📄",
        "video":     "🎬",
        "audio":     "🎵",
        "animation": "🎞",
        "voice":     "🎤",
    }.get(media_type, "📝")

    btn_count = sum(len(r) for r in button_rows)
    existing  = get_filter(chat.id, keyword)
    resp_count = len(existing.get("responses", [])) if existing else 1

    await message.reply_text(
        f"✅ <b>Filter saved!</b>\n\n"
        f"🔑 Keyword: <code>{keyword}</code>\n"
        f"{type_icon} Type: <b>{media_type or 'text'}</b>\n"
        f"🔘 Buttons: <b>{btn_count}</b>\n"
        f"📦 Total responses: <b>{resp_count}</b>\n\n"
        f"<i>Ab jab koi group mein '<b>{keyword}</b>' likhe,\n"
        f"main automatically reply karunga! 🌸</i>",
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════════════════
# /filters  —  List all filters
# ══════════════════════════════════════════════════════════

async def filter_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message

    if chat.type == "private":
        await message.reply_text("❌ Groups mein use karo!")
        return

    all_filters = get_all_filters(chat.id)

    if not all_filters:
        await message.reply_text(
            "📭 <b>Koi bhi filter set nahi hai!</b>\n\n"
            "Pehla filter lagane ke liye:\n"
            "<code>/filter 'keyword' jawab text</code>",
            parse_mode="HTML",
        )
        return

    lines = [f"📋 <b>{chat.title} — Filters ({len(all_filters)})</b>\n"]
    for i, f in enumerate(all_filters, 1):
        kw        = f.get("keyword", "?")
        responses = f.get("responses", [])
        r_count   = len(responses)

        # Collect media types
        mtypes = set()
        has_btn = False
        for r in responses:
            mt = r.get("media_type")
            if mt:
                mtypes.add(mt)
            if r.get("buttons"):
                has_btn = True

        icons = []
        if not mtypes:
            icons.append("📝")
        for mt in sorted(mtypes):
            icons.append({"photo":"🖼","sticker":"😄","document":"📄",
                          "video":"🎬","audio":"🎵","animation":"🎞",
                          "voice":"🎤"}.get(mt, "📎"))
        if has_btn:
            icons.append("🔘")

        icon_str = " ".join(icons)
        r_str    = f"{r_count} resp{'onse' if r_count == 1 else 'onses'}"
        lines.append(f"<b>{i}.</b> <code>{kw}</code> {icon_str} — {r_str}")

    lines.append(
        "\n<i>➡ /stop 'keyword' — ek filter delete karo\n"
        "➡ /stopall — sab filters delete karo</i>"
    )

    await message.reply_text("\n".join(lines), parse_mode="HTML")


# ══════════════════════════════════════════════════════════
# /stop  —  Delete one filter
# ══════════════════════════════════════════════════════════

async def filter_stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message

    if chat.type == "private":
        return

    if not await _is_user_admin(context, chat.id, user.id):
        await message.reply_text("❌ Sirf admins filter delete kar sakte hain!")
        return

    if not context.args:
        await message.reply_text(
            "❌ Usage: <code>/stop 'keyword'</code>\n\n"
            "Example: <code>/stop 'hello'</code>",
            parse_mode="HTML",
        )
        return

    args_text = " ".join(context.args)
    keyword, _ = _extract_keyword(args_text)

    if not keyword:
        await message.reply_text("❌ Keyword dena padega!")
        return

    if not get_filter(chat.id, keyword):
        await message.reply_text(
            f"❌ <code>{keyword}</code> naam ka koi filter nahi mila!\n\n"
            f"Sab filters dekhne ke liye: /filters",
            parse_mode="HTML",
        )
        return

    delete_filter(chat.id, keyword)
    await message.reply_text(
        f"✅ Filter <code>{keyword}</code> delete kar diya! 🗑️",
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════════════════
# /stopall  —  Delete ALL filters for this group
# ══════════════════════════════════════════════════════════

async def filter_stopall_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message

    if chat.type == "private":
        return

    if not await _is_user_admin(context, chat.id, user.id):
        await message.reply_text("❌ Sirf admins sab filters delete kar sakte hain!")
        return

    current = get_all_filters(chat.id)
    if not current:
        await message.reply_text(
            "📭 Is group mein pehle se koi filter nahi hai.",
            parse_mode="HTML",
        )
        return

    count = delete_all_filters(chat.id)
    await message.reply_text(
        f"✅ Sab <b>{count}</b> filter(s) delete kar diye! 🗑️\n\n"
        f"Group ab filter-free hai.",
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════════════════
# MESSAGE CHECK  —  called from chat.py message_handler
# ══════════════════════════════════════════════════════════

async def check_and_reply_filter(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Check if the incoming group message matches any filter keyword.
    Returns True if a filter was triggered (so caller can stop further processing).
    """
    message = update.effective_message
    chat    = update.effective_chat

    if not message or not chat:
        return False
    if chat.type == "private":
        return False

    text = message.text or message.caption or ""
    if not text:
        return False

    matched = find_matching_filter(chat.id, text)
    if not matched:
        return False

    responses = matched.get("responses", [])
    if not responses:
        return False

    # Random response pick (multiple responses per keyword = variety!)
    response = random.choice(responses)
    await _send_filter_response(message, response)
    return True
