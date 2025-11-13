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

# ===================== TEXTOS =====================
base_english_messages = {
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
}

# Overrides (exemplos resumidos)
russian_overrides = {
    "welcome": "Добро пожаловать! Выберите язык:",
    "btn_instruction": "📖 Инструкция",
    "btn_registration": "🔗 Регистрация",
    "btn_get_access": "🔑 Доступ к боту",
    "btn_change_lang": "🌍 Язык",
    "btn_support": "💬 Поддержка",
    "btn_launch_app": "▶️ Запуск программы",
    "btn_get_promo": "💰 Промокод",
    "btn_check_sub": "✅ Проверить подписку",
    "menu_access_closed": "Доступ к программе: 🔴 Закрыт",
    "menu_access_granted": "Доступ к программе: 🟢 Выдан",
    "menu_pending": "Заявка на рассмотрении. Подождите.",
    "menu_telegram_id": "Ваш Telegram ID: {id}",
    "menu_game_id_none": "Ваш Game ID: не указан",
    "menu_game_id_set": "Ваш Game ID: {game_id}",
    "instr_text": (
        "ИНСТРУКЦИЯ\n"
        "1) Нажмите '💰 Промокод' и подпишитесь на канал.\n"
        "2) Регистрация: {link} (укажите промокод при регистрации).\n"
        "3) Нажмите '🔑 Доступ к боту' и пришлите ID 1win.\n"
        "4) Ожидайте одобрения и затем '▶️ Запуск программы'."
    ),
    "registration_text": "Регистрация по ссылке, код: MOB500RR\n{link}",
}

spanish_overrides = {
    "welcome": "¡Bienvenido! Elige tu idioma:",
    "btn_instruction": "📖 Instrucciones",
    "btn_registration": "🔗 Registro",
    "btn_get_access": "🔑 Acceso al bot",
    "btn_change_lang": "🌍 Idioma",
    "btn_support": "💬 Soporte",
    "btn_launch_app": "▶️ Iniciar programa",
    "btn_get_promo": "💰 Código promocional",
    "btn_check_sub": "✅ Verificar suscripción",
    "menu_access_closed": "Acceso al programa: 🔴 Cerrado",
    "menu_access_granted": "Acceso al programa: 🟢 Permitido",
    "menu_pending": "Tu solicitud está en revisión. Espera.",
    "menu_telegram_id": "Tu Telegram ID: {id}",
    "menu_game_id_none": "Tu Game ID: no definido",
    "menu_game_id_set": "Tu Game ID: {game_id}",
    "instr_text": (
        "INSTRUCCIONES\n"
        "1) Pulsa '💰 Código promocional' y suscríbete al canal.\n"
        "2) Regístrate: {link} (usa el código en el registro).\n"
        "3) Pulsa '🔑 Acceso al bot' y envía tu ID de 1win.\n"
        "4) Espera la aprobación y luego '▶️ Iniciar programa'."
    ),
    "registration_text": "Regístrate con el enlace. Código: MOB500RR\n{link}",
}

portuguese_overrides = {
    "welcome": "Bem-vindo! Escolha seu idioma:",
    "btn_instruction": "📖 Instruções",
    "btn_registration": "🔗 Registro",
    "btn_get_access": "🔑 Acesso ao bot",
    "btn_change_lang": "🌍 Idioma",
    "btn_support": "💬 Suporte",
    "btn_launch_app": "▶️ Abrir programa",
    "btn_get_promo": "💰 Obter código",
    "btn_check_sub": "✅ Verificar assinatura",
    "menu_access_closed": "Acesso ao programa: 🔴 Fechado",
    "menu_access_granted": "Acesso ao programa: 🟢 Liberado",
    "menu_pending": "Sua solicitação está em análise. Aguarde.",
    "menu_telegram_id": "Seu Telegram ID: {id}",
    "menu_game_id_none": "Seu Game ID: não definido",
    "menu_game_id_set": "Seu Game ID: {game_id}",
    "instr_text": (
        "INSTRUÇÕES\n"
        "1) Toque em '💰 Obter código' e assine o canal.\n"
        "2) Registre-se: {link} (use o código no cadastro).\n"
        "3) Toque em '🔑 Acesso ao bot' e envie seu ID 1win.\n"
        "4) Aguarde a aprovação e depois '▶️ Abrir programa'."
    ),
    "registration_text": "Registre-se pelo link. Código: MOB500RR\n{link}",
}

# HERANÇA COMPLETA: PT/ES/RU recebem todas as chaves de EN
MESSAGES = {
    "EN": base_english_messages,
    "RU": {**base_english_messages, **russian_overrides},
    "ES": {**base_english_messages, **spanish_overrides},
    "PT": {**base_english_messages, **portuguese_overrides},
}

# ===================== HELPERS =====================
def user_lang(uid: int) -> str:
    return USER_DATA.get(uid, {}).get("lang", "EN")

def set_user_lang(uid: int, lang: str):
    USER_DATA.setdefault(uid, {"lang": "EN", "access": "NONE", "game_id": None})
    USER_DATA[uid]["lang"] = lang

def t(uid: int, key: str) -> str:
    lang = user_lang(uid)
    base = MESSAGES.get(lang, {})
    if key in base:
        return base[key]
    return MESSAGES["EN"].get(key, key)

# Fallback defensivo: se faltar qualquer label, usa EN
def main_menu_kb(uid: int) -> ReplyKeyboardMarkup:
    lang = user_lang(uid)
    b = MESSAGES.get(lang, {}) or MESSAGES["EN"]

    instr = b.get("btn_instruction", MESSAGES["EN"]["btn_instruction"])
    reg = b.get("btn_registration", MESSAGES["EN"]["btn_registration"])
    promo = b.get("btn_get_promo", MESSAGES["EN"]["btn_get_promo"])
    get_access = b.get("btn_get_access", MESSAGES["EN"]["btn_get_access"])
    support = b.get("btn_support", MESSAGES["EN"]["btn_support"])
    change_lang = b.get("btn_change_lang", MESSAGES["EN"]["btn_change_lang"])
    launch = b.get("btn_launch_app", MESSAGES["EN"]["btn_launch_app"])

    rows = [
        [KeyboardButton(instr), KeyboardButton(reg)],
        [KeyboardButton(promo), KeyboardButton(get_access)],
        [KeyboardButton(support), KeyboardButton(change_lang)],
        [KeyboardButton(launch)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Português 🇧🇷", callback_data="set_lang_PT")],
            [InlineKeyboardButton("Español 🇪🇸", callback_data="set_lang_ES")],
            [InlineKeyboardButton("Русский 🇷🇺", callback_data="set_lang_RU")],
            [InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_EN")],
        ]
    )

def _txt(update: Update) -> str:
    return (update.message.text or "").strip() if update.message and update.message.text else ""

# ===================== USER START / MENU =====================
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
    USER_DATA.setdefault(uid, {"lang": lang, "access": "NONE", "game_id": None})
    try:
        await q.message.delete()
    except Exception:
        pass
    return await show_menu(update, context)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = (update.effective_user or update.callback_query.from_user).id
    status = USER_DATA.get(uid, {}).get("access", "NONE")
    game_id = USER_DATA.get(uid, {}).get("game_id")
    status_text = {"GRANTED": t(uid, "menu_access_granted"), "PENDING": t(uid, "menu_pending"),
                   "DENIED": t(uid, "access_rejected_msg"), "NONE": t(uid, "menu_access_closed")}[status]
    gid_line = t(uid, "menu_game_id_set").format(game_id=game_id) if game_id else t(uid, "menu_game_id_none")
    text = f"{status_text}\n\n{t(uid, 'menu_telegram_id').format(id=uid)}\n{gid_line}"
    try:
        await context.bot.send_message(uid, text, reply_markup=main_menu_kb(uid))
    except Exception as e:
        logger.exception("Erro ao montar/enviar menu: %s", e)
        await context.bot.send_message(uid, "Menu temporariamente indisponível. Envie /start para tentar novamente.")
    return MAIN_MENU

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
        ok = getattr(member, "status", "") not in {"left", "kicked"}
    except BadRequest:
        ok = False
    if ok:
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
    await update.message.reply_text("Select language:", reply_markup=lang_kb())
    return START_MENU

# ===================== ADMIN (mesmo conjunto do fix anterior) =====================
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

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    await update.message.reply_text("Welcome to Admin Panel.", reply_markup=admin_kb(uid))
    return ADMIN_MENU

# ... (mantenha daqui para baixo os seus handlers de admin já corrigidos)
# Se precisar, cole aqui os mesmos handlers admin do arquivo anterior (admin fix),
# pois a mudança para multilíngue não afeta o painel admin que usa EN.

# ===================== BUILD / MAIN =====================
def build_application():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers de admin primeiro (como no fix anterior) ...

    # Conversation do usuário
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
