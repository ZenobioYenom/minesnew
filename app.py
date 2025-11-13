# -*- coding: utf-8 -*-
import os
import re
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.error import BadRequest

# ===================== CONFIG =====================
load_dotenv()
BOT_ATIVO = os.getenv("BOT_ATIVO", "true").lower().strip() == "true"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN and BOT_ATIVO:
    raise RuntimeError("Defina BOT_TOKEN no Railway.")

ADMIN_IDS = {7428791161, 1993108159}
SUPPORT_USERNAME = "@koalamoney3"
PROMO_CODE = "MOB500RR"
REG_LINK = "https://1wtsks.com/v3/landing-fortune-wheel?p=gv72"
CHANNEL_USERNAME = "@mgoldenmines"
MINI_APP_URL = "https://zenobioyenom.github.io/appmineswin/"
GET_FILE_ID_MODE = False

# ===================== LOGGING =====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== ESTADOS =====================
START_MENU, MAIN_MENU, AWAITING_ID, AWAITING_CHANNEL_CHECK = range(4)
ADMIN_MENU, PROCESSING_REQUESTS, PROCESS_REQUEST_COMMENT = range(4, 7)
ADMIN_BROADCAST_MENU, BROADCAST_NOW_MSG, BROADCAST_NOW_CONFIRM = range(7, 10)
BROADCAST_LATER_MSG, BROADCAST_LATER_TIME, BROADCAST_LATER_CONFIRM = range(10, 13)

# ===================== DADOS =====================
USER_DATA = {}
PENDING_QUEUE = []
STATS = {"accepted": 0, "denied": 0, "corrected": 0, "total_handled": 0, "bot_status": "✅ Operating normally"}

PHOTO_IDS = {}

LANGS = ["PT", "ES", "RU", "EN"]

MESSAGES = {
    "EN": {
        "welcome": "Welcome! Choose your language:",
        "btn_instruction": "📖 Instruction",
        "btn_registration": "🔗 Registration",
        "btn_get_access": "🔑 Get Bot Access",
        "btn_change_lang": "🌍 Change Language",
        "btn_support": "💬 Contact Support",
        "btn_launch_app": "▶️ Launch Program",
        "btn_get_promo": "💰 Get Promo Code",
        "btn_check_sub": "✅ Check Subscription",
        "menu_access_closed": "Access to the program: 🔴 Closed",
        "menu_access_granted": "Access to the program: 🟢 Granted",
        "menu_pending": "Your application is pending review. Please wait.",
        "menu_telegram_id": "Your Telegram ID: {id}",
        "menu_game_id_none": "Your Game ID: Not set",
        "menu_game_id_set": "Your Game ID: {game_id}",
        "instr_text": (
            "INSTRUCTIONS\n"
            "1) Tap '💰 Get Promo Code' and subscribe to the channel.\n"
            "2) Register: {link} (use your code on registration).\n"
            "3) Tap '🔑 Get Bot Access' and send your 1win account ID.\n"
            "4) Wait for approval then '▶️ Launch Program'."
        ),
        "registration_text": "Register using the link and use code: MOB500RR\n{link}",
        "promo_check_prompt": "To receive the promo code, subscribe to our channel: {link}",
        "promo_not_subscribed": "You are not subscribed yet. Subscribe and press '✅ Check Subscription'.",
        "promo_subscribed_success": "Subscription verified! Your promo code: `MOB500RR`",
        "promo_code_already_sent": "You already have the promo code: `MOB500RR`",
        "promo_channel_error": "⚠️ Cannot verify subscription. Ensure the bot is admin in: {channel}.",
        "promo_needed_note": "Please get your promo code first by clicking '💰 Get Promo Code' in the main menu.",
        "awaiting_id_prompt": "Send your 1win account ID (text).",
        "application_received": "Received. Your request is in the queue. Wait for admin approval.",
        "access_granted_msg": "Access granted! You can now open the program.",
        "access_rejected_msg": "Access was denied. Please contact support if needed.",
        "access_rejected_with_comment_msg": "Access denied. Reason: {comment}",
        "launch_denied": "❌ Access denied. Submit or wait for approval.",
        "support_link_text": "Click for support: {username}",

        # Admin
        "btn_admin_apps": "🧾 Applications",
        "btn_admin_status": "🤖 Bot Status",
        "btn_admin_stats": "📊 Statistics",
        "btn_admin_broadcast": "💬 User Messages",
        "btn_start_processing": "🚀 Start Processing",
        "btn_accept": "✅ Accept",
        "btn_reject": "❌ Reject",
        "btn_reject_comment": "💬 Reject with comments",
        "btn_broadcast_now": "Send Now",
        "btn_broadcast_later": "Send Later",
        "btn_confirm": "✅ Confirm",
        "btn_cancel": "❌ Cancel",

        "apps_pending_count": "Active requests pending review: {count}",
        "app_processing_info": "Processing request:\nUser: {id}\nGame ID: {game_id}",
        "app_processing_text": "Text: {text}",
        "app_accepted": "Application ACCEPTED. User notified.",
        "app_rejected": "Application REJECTED. User notified.",
        "prompt_reject_comment": "Send the rejection comment.",
        "comment_sent": "Rejection with comment sent. User notified.",
        "bot_status_text": "Current bot status: {status}",
    },
    "PT": {}, "ES": {}, "RU": {}
}

def user_lang(uid: int) -> str:
    return USER_DATA.get(uid, {}).get("lang", "EN")

def set_user_lang(uid: int, lang: str):
    USER_DATA.setdefault(uid, {"lang": "EN", "access": "NONE", "game_id": None})
    USER_DATA[uid]["lang"] = lang

def t(uid: int, key: str) -> str:
    lang = user_lang(uid)
    base = MESSAGES.get(lang) or MESSAGES["EN"]
    return base.get(key, MESSAGES["EN"].get(key, key))

def main_menu_kb(uid: int) -> ReplyKeyboardMarkup:
    b = MESSAGES[user_lang(uid)]
    rows = [
        [KeyboardButton(b["btn_instruction"]), KeyboardButton(b["btn_registration"])],
        [KeyboardButton(b["btn_get_promo"]), KeyboardButton(b["btn_get_access"])],
        [KeyboardButton(b["btn_support"]), KeyboardButton(b["btn_change_lang"])],
        [KeyboardButton(b["btn_launch_app"])],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def admin_kb(uid: int) -> ReplyKeyboardMarkup:
    b = MESSAGES["EN"]
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(b["btn_admin_apps"])],
            [KeyboardButton(b["btn_admin_status"]), KeyboardButton(b["btn_admin_stats"])],
            [KeyboardButton(b["btn_admin_broadcast"])],
        ],
        resize_keyboard=True,
    )

def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Português 🇧🇷", callback_data="set_lang_PT")],
            [InlineKeyboardButton("Español 🇪🇸", callback_data="set_lang_ES")],
            [InlineKeyboardButton("Русский 🇷🇺", callback_data="set_lang_RU")],
            [InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_EN")],
        ]
    )

# ===================== START / MENU =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    USER_DATA.setdefault(uid, {"lang": "EN", "access": "NONE", "game_id": None})
    if uid in ADMIN_IDS:
        return await admin_start(update, context)
    await update.message.reply_text(t(uid, "welcome"), reply_markup=lang_kb())
    return START_MENU

async def set_lang_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = q.data.split("_")[-1]
    if lang not in {"EN", "PT", "ES", "RU"}:
        lang = "EN"
    set_user_lang(uid, lang)
    try:
        await q.message.delete()
    except Exception:
        pass
    return await show_menu(update, context)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = (update.effective_user or update.callback_query.from_user).id
    status = USER_DATA.get(uid, {}).get("access", "NONE")
    gid = USER_DATA.get(uid, {}).get("game_id") or t(uid, "menu_game_id_none")
    if gid == t(uid, "menu_game_id_none"):
        gid_line = gid
    else:
        gid_line = t(uid, "menu_game_id_set").format(game_id=gid)
    status_line = {
        "GRANTED": t(uid, "menu_access_granted"),
        "PENDING": t(uid, "menu_pending"),
        "DENIED": t(uid, "access_rejected_msg"),
        "NONE": t(uid, "menu_access_closed"),
    }[status]
    text = f"{status_line}\n\n{t(uid, 'menu_telegram_id').format(id=uid)}\n{gid_line}"
    await context.bot.send_message(uid, text, reply_markup=main_menu_kb(uid))
    return MAIN_MENU

def _txt(update: Update) -> str:
    return (update.message.text or "").strip()

# ===================== USER ROUTER =====================
async def route_main_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    text = _txt(update)
    b = MESSAGES[user_lang(uid)]
    mapping = {
        b["btn_instruction"]: handle_instruction,
        b["btn_registration"]: handle_registration,
        b["btn_get_promo"]: handle_get_promo,
        b["btn_get_access"]: handle_get_access,
        b["btn_support"]: handle_support,
        b["btn_change_lang"]: handle_change_lang,
        b["btn_launch_app"]: handle_launch,
    }
    func = mapping.get(text)
    if func:
        return await func(update, context)
    await update.message.reply_text("Toque em um botão do menu.")
    return MAIN_MENU

# ===================== USER ACTIONS =====================
async def handle_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    await update.message.reply_text(t(uid, "instr_text").format(link=REG_LINK))
    return MAIN_MENU

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    await update.message.reply_text(t(uid, "registration_text").format(link=REG_LINK))
    return MAIN_MENU

async def handle_get_promo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    if USER_DATA.get(uid, {}).get("has_promo"):
        await update.message.reply_text(t(uid, "promo_code_already_sent"), parse_mode="Markdown")
        return MAIN_MENU
    text = t(uid, "promo_check_prompt").format(link=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔗 Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(t(uid, "btn_check_sub"), callback_data="check_sub_now")],
        ]
    )
    await update.message.reply_text(text, reply_markup=kb)
    return AWAITING_CHANNEL_CHECK

async def handle_check_sub_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
        if getattr(member, "status", "") not in {"left", "kicked"}:
            USER_DATA.setdefault(uid, {})["has_promo"] = True
            await q.message.edit_text(t(uid, "promo_subscribed_success"), parse_mode="Markdown")
            return await show_menu(update, context)
        else:
            kb = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔗 Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
                    [InlineKeyboardButton(t(uid, "btn_check_sub"), callback_data="check_sub_now")],
                ]
            )
            await q.message.edit_text(t(uid, "promo_not_subscribed"), reply_markup=kb)
            return AWAITING_CHANNEL_CHECK
    except BadRequest:
        await q.message.reply_text(t(uid, "promo_channel_error").format(channel=CHANNEL_USERNAME))
        return await show_menu(update, context)

async def handle_get_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    if not USER_DATA.get(uid, {}).get("has_promo"):
        await update.message.reply_text(t(uid, "promo_needed_note"))
        return MAIN_MENU
    status = USER_DATA.get(uid, {}).get("access", "NONE")
    if status == "GRANTED":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(t(uid, "btn_launch_app"), web_app=WebAppInfo(url=MINI_APP_URL))]])
        await update.message.reply_text(t(uid, "access_granted_msg"), reply_markup=kb)
        return MAIN_MENU
    if status == "PENDING":
        await update.message.reply_text(t(uid, "menu_pending"))
        return MAIN_MENU
    await update.message.reply_text(t(uid, "awaiting_id_prompt"))
    return AWAITING_ID

async def handle_user_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    text = _txt(update)
    if not text or not re.match(r"^[A-Za-z0-9._-]{4,}$", text):
        await update.message.reply_text(t(uid, "awaiting_id_prompt"))
        return AWAITING_ID
    USER_DATA.setdefault(uid, {"lang": user_lang(uid), "access": "NONE", "game_id": None})
    USER_DATA[uid]["game_id"] = text
    USER_DATA[uid]["access"] = "PENDING"
    if uid not in PENDING_QUEUE:
        PENDING_QUEUE.append(uid)
    for aid in ADMIN_IDS:
        try:
            await context.bot.send_message(aid, f"🆕 New application:\nUser: {uid}\nGame ID: {text}\nQueue: {len(PENDING_QUEUE)}")
        except Exception:
            pass
    await update.message.reply_text(t(uid, "application_received"))
    return await show_menu(update, context)

async def handle_launch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    if USER_DATA.get(uid, {}).get("access") != "GRANTED":
        await update.message.reply_text(t(uid, "launch_denied"))
        return MAIN_MENU
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(t(uid, "btn_launch_app"), web_app=WebAppInfo(url=MINI_APP_URL))]])
    await update.message.reply_text(t(uid, "access_granted_msg"), reply_markup=kb)
    return MAIN_MENU

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    await update.message.reply_text(t(uid, "support_link_text").format(username=SUPPORT_USERNAME))
    return MAIN_MENU

async def handle_change_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Select language:", reply_markup=InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Português 🇧🇷", callback_data="set_lang_PT")],
            [InlineKeyboardButton("Español 🇪🇸", callback_data="set_lang_ES")],
            [InlineKeyboardButton("Русский 🇷🇺", callback_data="set_lang_RU")],
            [InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_EN")],
        ]
    ))
    return START_MENU

# ===================== ADMIN =====================
def _is_btn(text: str, label: str) -> bool:
    return text == label

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    await update.message.reply_text("Welcome to Admin Panel.", reply_markup=admin_kb(uid))
    return ADMIN_MENU

async def admin_apps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    count = len(PENDING_QUEUE)
    await update.message.reply_text(MESSAGES["EN"]["apps_pending_count"].format(count=count), reply_markup=admin_kb(uid))
    if count == 0:
        return ADMIN_MENU
    kb = ReplyKeyboardMarkup([[KeyboardButton(MESSAGES["EN"]["btn_start_processing"])]], resize_keyboard=True)
    await update.message.reply_text("Select:", reply_markup=kb)
    return ADMIN_MENU

async def admin_start_processing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    if not PENDING_QUEUE:
        await update.message.reply_text("The application queue is empty.", reply_markup=admin_kb(uid))
        return ADMIN_MENU
    target = PENDING_QUEUE.pop(0)
    context.user_data["target_user_id"] = target
    u = USER_DATA.get(target, {})
    text = MESSAGES["EN"]["app_processing_info"].format(id=target, game_id=u.get("game_id", "N/A"))
    if u.get("game_id"):
        text += f"\n{MESSAGES['EN']['app_processing_text'].format(text=u['game_id'])}"
    kb = ReplyKeyboardMarkup(
        [
            [KeyboardButton(MESSAGES["EN"]["btn_accept"])],
            [KeyboardButton(MESSAGES["EN"]["btn_reject"]), KeyboardButton(MESSAGES["EN"]["btn_reject_comment"])],
        ],
        resize_keyboard=True,
    )
    await update.message.reply_text(text, reply_markup=kb)
    return PROCESSING_REQUESTS

async def admin_process_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    action = _txt(update)
    target = context.user_data.get("target_user_id")
    if not target:
        await update.message.reply_text("No target in context.", reply_markup=admin_kb(uid))
        return ADMIN_MENU

    if _is_btn(action, MESSAGES["EN"]["btn_accept"]):
        USER_DATA[target]["access"] = "GRANTED"
        STATS["accepted"] += 1
        STATS["total_handled"] += 1
        try:
            await context.bot.send_message(target, t(target, "access_granted_msg"))
        except Exception:
            pass
        await update.message.reply_text(MESSAGES["EN"]["app_accepted"])
        context.user_data.clear()
        return await admin_start(update, context)

    if _is_btn(action, MESSAGES["EN"]["btn_reject"]):
        USER_DATA[target]["access"] = "DENIED"
        STATS["denied"] += 1
        STATS["total_handled"] += 1
        try:
            await context.bot.send_message(target, t(target, "access_rejected_msg"))
        except Exception:
            pass
        await update.message.reply_text(MESSAGES["EN"]["app_rejected"])
        context.user_data.clear()
        return await admin_start(update, context)

    if _is_btn(action, MESSAGES["EN"]["btn_reject_comment"]):
        await update.message.reply_text(MESSAGES["EN"]["prompt_reject_comment"], reply_markup=ReplyKeyboardRemove())
        return PROCESS_REQUEST_COMMENT

    await update.message.reply_text("Unknown action.", reply_markup=admin_kb(uid))
    return ADMIN_MENU

async def admin_process_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    comment = _txt(update)
    target = context.user_data.get("target_user_id")
    if not target:
        await update.message.reply_text("No target in context.", reply_markup=admin_kb(uid))
        return ADMIN_MENU
    USER_DATA[target]["access"] = "DENIED"
    STATS["corrected"] += 1
    STATS["total_handled"] += 1
    try:
        await context.bot.send_message(target, t(target, "access_rejected_with_comment_msg").format(comment=comment))
    except Exception:
        pass
    await update.message.reply_text(MESSAGES["EN"]["comment_sent"])
    context.user_data.clear()
    return await admin_start(update, context)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    s = STATS
    text = f"Statistics:\nAccepted: {s['accepted']}\nDenied: {s['denied']}\nCorrected: {s['corrected']}\nTotal: {s['total_handled']}"
    await update.message.reply_text(text, reply_markup=admin_kb(uid))
    return ADMIN_MENU

async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    await update.message.reply_text(MESSAGES["EN"]["bot_status_text"].format(status=STATS["bot_status"]), reply_markup=admin_kb(uid))
    return ADMIN_MENU

async def admin_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton(MESSAGES["EN"]["btn_broadcast_now"]), KeyboardButton(MESSAGES["EN"]["btn_broadcast_later"])]],
        resize_keyboard=True,
    )
    await update.message.reply_text("Choose broadcast type:", reply_markup=kb)
    return ADMIN_BROADCAST_MENU

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    action = _txt(update)
    if _is_btn(action, MESSAGES["EN"]["btn_broadcast_now"]):
        context.user_data["broadcast_type"] = "now"
        await update.message.reply_text("Send your message (text or photo):", reply_markup=ReplyKeyboardRemove())
        return BROADCAST_NOW_MSG
    if _is_btn(action, MESSAGES["EN"]["btn_broadcast_later"]):
        context.user_data["broadcast_type"] = "later"
        await update.message.reply_text("Send your message (text or photo):", reply_markup=ReplyKeyboardRemove())
        return BROADCAST_LATER_MSG
    await update.message.reply_text("Back.", reply_markup=admin_kb(uid))
    return ADMIN_MENU

async def save_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    if update.message.text:
        context.user_data["broadcast_text"] = update.message.text
    if update.message.photo:
        context.user_data["broadcast_photo_id"] = update.message.photo[-1].file_id

    kb = ReplyKeyboardMarkup([[KeyboardButton(MESSAGES["EN"]["btn_confirm"]), KeyboardButton(MESSAGES["EN"]["btn_cancel"])]], resize_keyboard=True)

    if context.user_data.get("broadcast_type") == "now":
        await update.message.reply_text("Confirm send now?", reply_markup=kb)
        return BROADCAST_NOW_CONFIRM

    if context.user_data.get("broadcast_type") == "later":
        await update.message.reply_text("Enter time (YYYY-MM-DD HH:MM UTC):", reply_markup=ReplyKeyboardRemove())
        return BROADCAST_LATER_TIME

    await update.message.reply_text("Unknown broadcast state.", reply_markup=admin_kb(uid))
    return ADMIN_MENU

async def broadcast_confirm_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    action = _txt(update)
    if _is_btn(action, MESSAGES["EN"]["btn_confirm"]):
        text = context.user_data.get("broadcast_text")
        photo_id = context.user_data.get("broadcast_photo_id")
        user_ids = [u for u in USER_DATA if u not in ADMIN_IDS]
        sent = 0
        for target in user_ids:
            try:
                if photo_id:
                    await context.bot.send_photo(target, photo_id, caption=text or "")
                else:
                    await context.bot.send_message(target, text or "")
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
        await update.message.reply_text(f"Broadcast sent to {sent}/{len(user_ids)} users.", reply_markup=admin_kb(uid))
        context.user_data.clear()
        return ADMIN_MENU
    await update.message.reply_text("Cancelled.", reply_markup=admin_kb(uid))
    context.user_data.clear()
    return ADMIN_MENU

async def broadcast_set_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    time_str = _txt(update)
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text("Invalid format. Use YYYY-MM-DD HH:MM (UTC).")
        return BROADCAST_LATER_TIME
    context.user_data["scheduled_time"] = dt
    kb = ReplyKeyboardMarkup([[KeyboardButton(MESSAGES["EN"]["btn_confirm"]), KeyboardButton(MESSAGES["EN"]["btn_cancel"])]], resize_keyboard=True)
    await update.message.reply_text(f"Confirm schedule for {dt} UTC?", reply_markup=kb)
    return BROADCAST_LATER_CONFIRM

async def broadcast_confirm_later(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    action = _txt(update)
    if _is_btn(action, MESSAGES["EN"]["btn_confirm"]):
        dt = context.user_data.get("scheduled_time")
        if not dt:
            await update.message.reply_text("No time set.", reply_markup=admin_kb(uid))
            return ADMIN_MENU
        context.job_queue.run_once(send_scheduled_broadcast, when=dt, data={
            "text": context.user_data.get("broadcast_text"),
            "photo_id": context.user_data.get("broadcast_photo_id"),
            "admin_id": uid,
        })
        await update.message.reply_text(f"Scheduled for {dt} UTC.", reply_markup=admin_kb(uid))
        context.user_data.clear()
        return ADMIN_MENU
    await update.message.reply_text("Cancelled.", reply_markup=admin_kb(uid))
    context.user_data.clear()
    return ADMIN_MENU

async def send_scheduled_broadcast(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    text = data.get("text")
    photo_id = data.get("photo_id")
    admin_id = data.get("admin_id")
    user_ids = [u for u in USER_DATA if u not in ADMIN_IDS]
    sent = 0
    for target in user_ids:
        try:
            if photo_id:
                await context.bot.send_photo(target, photo_id, caption=text or "")
            else:
                await context.bot.send_message(target, text or "")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await context.bot.send_message(admin_id, f"✅ Scheduled broadcast completed: {sent}/{len(user_ids)} sent.")

# ===================== BUILD / MAIN =====================
def build_application() -> Application:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers de ADMIN primeiro (prioridade)
    app.add_handler(MessageHandler(filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(r"^🧾 Applications"), admin_apps))
    app.add_handler(MessageHandler(filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(r"^🚀 Start Processing$"), admin_start_processing))
    app.add_handler(MessageHandler(filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(r"^🤖 Bot Status$"), admin_status))
    app.add_handler(MessageHandler(filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(r"^📊 Statistics$"), admin_stats))
    app.add_handler(MessageHandler(filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(r"^💬 User Messages$"), admin_broadcast_menu))
    app.add_handler(MessageHandler(filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(r"^Send Now$"), admin_broadcast_start))
    app.add_handler(MessageHandler(filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(r"^Send Later$"), admin_broadcast_start))
    app.add_handler(MessageHandler(filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(r"^✅ Confirm$"), broadcast_confirm_now))
    app.add_handler(MessageHandler(filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(r"^❌ Cancel$"), broadcast_confirm_now))
    app.add_handler(MessageHandler(filters.User(user_id=list(ADMIN_IDS)) & ~filters.COMMAND & filters.TEXT, admin_process_action))
    app.add_handler(MessageHandler(filters.User(user_id=list(ADMIN_IDS)) & ~filters.COMMAND & filters.TEXT, admin_process_comment))

    # Conversation do USUÁRIO
    user_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_MENU: [CallbackQueryHandler(set_lang_cb, pattern=r"^set_lang_")],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, route_main_buttons)],
            AWAITING_CHANNEL_CHECK: [
                CallbackQueryHandler(handle_check_sub_cb, pattern=r"^check_sub_now$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, route_main_buttons),
            ],
            AWAITING_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_id_input)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )
    app.add_handler(user_conv)

    return app

def main():
    if not BOT_ATIVO:
        print("🚫 Bot desativado (BOT_ATIVO=false). Encerrando.")
        return
    app = build_application()
    logger.info("🤖 Bot iniciado. Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, poll_interval=1)

if __name__ == "__main__":
    main()
