import os
from datetime import datetime
from fastapi import FastAPI, Request, Header, HTTPException
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatMemberHandler, filters,
)

BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
WEBHOOK_URL  = os.environ.get("WEBHOOK_URL", "")
ADMIN_ID     = int(os.environ.get("ADMIN_ID", "0"))
CRON_SECRET  = os.environ.get("CRON_SECRET", "change_this_secret")
BOT_NAME_STR = "Cutie Pie Bot"

# Singleton — one app per Vercel instance
_bot_app: Application | None = None
_initialized: bool = False


def _import_handlers():
    from handlers.events import (
        start_handler, my_chat_member_handler,
        new_member_handler, left_member_handler,
        callback_handler, unlock_raid_handler,
    )
    from handlers.admin import (
        settings_handler,
        ban_handler, unban_handler,
        mute_handler, unmute_handler, kick_handler,
        warn_handler, warns_handler, resetwarn_handler,
        pin_handler, unpin_handler, del_handler, purge_handler,
        promote_handler, demote_handler,
        tagall_handler, stoptagall_handler,
        lock_handler, unlock_handler,
        setwelcome_handler, setgoodbye_handler, setrules_handler,
        save_note_handler, get_note_handler,
        notes_list_handler, delnote_handler,
        whois_handler, stats_handler, topusers_handler,
        premiumstats_handler,
        teach_handler, forget_handler, patterns_handler,
        blockuser_handler, unblockuser_handler,
        broadcast_handler, addprem_handler, remprem_handler,
        prem_start_handler, cancel_premium_handler,
        report_handler, id_handler,
        schedule_handler, unschedule_handler,
        slowmode_handler, floodlimit_handler,
        autodel_time_handler, warnlimit_handler,
        adminlist_handler,
    )
    from handlers.user import (
        help_handler, rules_handler,
        premium_handler, font_handler,
    )
    from handlers.chat import movie_file_handler, message_handler
    from handlers.filters import (
        filter_add_handler, filter_list_handler,
        filter_stop_handler, filter_stopall_handler,
    )
    return locals()


async def get_bot_app() -> Application:
    global _bot_app, _initialized

    # ══ FIX: Only initialize ONCE per Vercel instance ══════
    if _bot_app and _initialized:
        return _bot_app

    h = _import_handlers()
    application = Application.builder().token(BOT_TOKEN).build()

    # ── Bot status changes ───────────────────────────────────
    application.add_handler(ChatMemberHandler(
        h["my_chat_member_handler"],
        ChatMemberHandler.MY_CHAT_MEMBER,
    ))

    # ── Member join/leave ────────────────────────────────────
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, h["new_member_handler"],
    ))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER, h["left_member_handler"],
    ))

    # ── Owner commands ───────────────────────────────────────
    for cmd, fn in [
        ("broadcast",    h["broadcast_handler"]),
        ("addprem",      h["addprem_handler"]),
        ("remprem",      h["remprem_handler"]),
        ("premiumstats", h["premiumstats_handler"]),
        ("teach",        h["teach_handler"]),
        ("forget",       h["forget_handler"]),
        ("patterns",     h["patterns_handler"]),
        ("blockuser",    h["blockuser_handler"]),
        ("unblockuser",  h["unblockuser_handler"]),
    ]:
        application.add_handler(CommandHandler(cmd, fn))

    # ── Admin commands ───────────────────────────────────────
    for cmd, fn in [
        ("settings",    h["settings_handler"]),
        ("ban",         h["ban_handler"]),
        ("unban",       h["unban_handler"]),
        ("mute",        h["mute_handler"]),
        ("unmute",      h["unmute_handler"]),
        ("kick",        h["kick_handler"]),
        ("warn",        h["warn_handler"]),
        ("warns",       h["warns_handler"]),
        ("resetwarn",   h["resetwarn_handler"]),
        ("pin",         h["pin_handler"]),
        ("unpin",       h["unpin_handler"]),
        ("del",         h["del_handler"]),
        ("purge",       h["purge_handler"]),
        ("promote",     h["promote_handler"]),
        ("demote",      h["demote_handler"]),
        ("tagall",      h["tagall_handler"]),
        ("stoptagall",  h["stoptagall_handler"]),
        ("lock",        h["lock_handler"]),
        ("unlock",      h["unlock_handler"]),
        ("setwelcome",  h["setwelcome_handler"]),
        ("setgoodbye",  h["setgoodbye_handler"]),
        ("setrules",    h["setrules_handler"]),
        ("save",        h["save_note_handler"]),
        ("delnote",     h["delnote_handler"]),
        ("schedule",    h["schedule_handler"]),
        ("unschedule",  h["unschedule_handler"]),
        ("slowmode",    h["slowmode_handler"]),
        ("floodlimit",  h["floodlimit_handler"]),
        ("autodel",     h["autodel_time_handler"]),
        ("warnlimit",   h["warnlimit_handler"]),
        ("unlock_raid", h["unlock_raid_handler"]),
        ("adminlist",   h["adminlist_handler"]),
        ("report",      h["report_handler"]),
        # ── Filter commands ──────────────────────────────
        ("filter",      h["filter_add_handler"]),
        ("filters",     h["filter_list_handler"]),
        ("stop",        h["filter_stop_handler"]),
        ("stopall",     h["filter_stopall_handler"]),
    ]:
        application.add_handler(CommandHandler(cmd, fn))

    # ── User commands ────────────────────────────────────────
    for cmd, fn in [
        ("start",     h["start_handler"]),
        ("subscribe", h["prem_start_handler"]),
        ("help",      h["help_handler"]),
        ("rules",     h["rules_handler"]),
        ("premium",   h["premium_handler"]),
        ("font",      h["font_handler"]),
        ("id",        h["id_handler"]),
        ("whois",     h["whois_handler"]),
        ("stats",     h["stats_handler"]),
        ("topusers",  h["topusers_handler"]),
        ("get",       h["get_note_handler"]),
        ("notes",     h["notes_list_handler"]),
    ]:
        application.add_handler(CommandHandler(cmd, fn))

    application.add_handler(CommandHandler("cancel", h["cancel_premium_handler"]))

    # ── Callback buttons ─────────────────────────────────────
    application.add_handler(CallbackQueryHandler(h["callback_handler"]))

    # ── Movie file system (documents + videos in groups) ─────
    # Registered BEFORE message_handler so it takes priority
    application.add_handler(MessageHandler(
        (filters.Document.ALL | filters.VIDEO) & filters.ChatType.GROUPS,
        h["movie_file_handler"],
    ))

    # ── PHOTO in PM only (premium subscription screenshot) ────
    application.add_handler(MessageHandler(
        filters.PHOTO & filters.ChatType.PRIVATE,
        h["message_handler"],
    ))

    # ── Main message handler ─────────────────────────────────
    # FIX: Explicitly EXCLUDE documents/videos from this filter
    # so captions of files don't trigger chatbot in groups
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.CAPTION)
        & ~filters.COMMAND
        & ~filters.Document.ALL    # ← exclude documents
        & ~filters.VIDEO           # ← exclude videos
        & ~filters.AUDIO           # ← exclude audio
        & ~filters.VOICE           # ← exclude voice
        & ~filters.ANIMATION       # ← exclude GIFs
        & ~filters.Sticker.ALL,    # ← exclude stickers
        h["message_handler"],
    ))

    # Initialize the app once
    await application.initialize()

    _bot_app     = application
    _initialized = True
    return _bot_app


# ════════════════════════════════════════════════════════
# FastAPI
# ════════════════════════════════════════════════════════

app = FastAPI()


@app.get("/")
async def root():
    return {"status": f"{BOT_NAME_STR} is running 💘", "token_ok": bool(BOT_TOKEN)}


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.post("/webhook")
async def webhook(request: Request):
    """
    Process each Telegram update.
    FIX: No 'async with bot_app' — that re-initializes+shuts-down every request.
    Just call process_update() on the already-initialized singleton.
    """
    try:
        data    = await request.json()
        bot_app = await get_bot_app()
        update  = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}")
        return {"ok": False, "error": str(e)}


@app.get("/set_webhook")
async def set_webhook():
    if not WEBHOOK_URL or not BOT_TOKEN:
        return {"error": "WEBHOOK_URL or BOT_TOKEN not set"}
    bot_app = await get_bot_app()
    result  = await bot_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
    return {"ok": result, "webhook_url": f"{WEBHOOK_URL}/webhook"}


@app.get("/cron")
async def cron_runner(x_cron_secret: str = Header(default="")):
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    bot_app = await get_bot_app()
    now     = datetime.now()
    results = {"scheduled_sent": 0, "auto_deleted": 0, "errors": []}

    # 1. Scheduled messages
    try:
        from core.db import get_all_scheduled
        for s in get_all_scheduled():
            if s.get("hour") == now.hour and s.get("minute") == now.minute:
                try:
                    await bot_app.bot.send_message(
                        chat_id=s["chat_id"], text=s["text"],
                        parse_mode="HTML", disable_web_page_preview=True,
                    )
                    results["scheduled_sent"] += 1
                except Exception as e:
                    results["errors"].append(f"sched:{str(e)[:50]}")
    except Exception as e:
        results["errors"].append(f"sched_block:{str(e)[:50]}")

    # 2. Auto-delete
    try:
        from core.db import get_pending_deletes, remove_pending_delete
        for item in get_pending_deletes():
            try:
                await bot_app.bot.delete_message(
                    chat_id=item["chat_id"], message_id=item["msg_id"],
                )
                results["auto_deleted"] += 1
            except Exception:
                pass
            remove_pending_delete(item["chat_id"], item["msg_id"])
    except Exception as e:
        results["errors"].append(f"del_block:{str(e)[:50]}")

    return {"ok": True, "time": now.strftime("%H:%M"), **results}


@app.get("/me")
async def get_me():
    bot_app = await get_bot_app()
    me = await bot_app.bot.get_me()
    return {"username": me.username, "name": me.full_name, "id": me.id}


@app.get("/debug")
async def debug():
    return {
        "token_set":   bool(BOT_TOKEN),
        "webhook_set": bool(WEBHOOK_URL),
        "admin_id":    ADMIN_ID,
        "initialized": _initialized,
        "cron_secret": "SET ✅" if CRON_SECRET != "change_this_secret" else "⚠️ NOT SET",
    }
