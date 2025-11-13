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

# ===================== CONFIG / AMBIENTE =====================
load_dotenv()

BOT_ATIVO = os.getenv("BOT_ATIVO", "true").lower().strip() == "true"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN and BOT_ATIVO:
    raise RuntimeError("Defina BOT_TOKEN no Railway/GitHub Secrets.")

# Admins (lista!)
ADMIN_IDS = {7428791161, 1993108159}

# URLs e integrações
SUPPORT_USERNAME = "@koalamoney3"
PROMO_CODE = "MOB500RR"
REG_LINK = "https://1wtsks.com/v3/landing-fortune-wheel?p=gv72"
CHANNEL_USERNAME = "@mgoldenmines"
MINI_APP_URL = "https://zenobioyenom.github.io/appmineswin/"

# GET_FILE_ID_MODE (modo coleta de file_id)
GET_FILE_ID_MODE = False  # defina True para coletar file_ids temporariamente

PHOTO_IDS = {
    "privet": "placeholder",
    "menu": "placeholder",
    "instr": "placeholder",
    "id_example": "placeholder",
    "reg_RU": "placeholder",
    "reg_EN": "placeholder",
    "reg_ES": "placeholder",
    "reg_PT": "placeholder",
}

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

# ===================== DADOS EM MEMÓRIA =====================
USER_DATA = {}
PENDING_QUEUE = []
STATS = {"accepted": 0, "denied": 0, "corrected": 0, "total_handled": 0, "bot_status": "✅ Operating normally"}

# ===================== TEXTOS =====================
LANGS = ["PT", "ES", "RU", "EN"]

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
    "btn_admin_apps": "🧾 Applications ({count})",
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
    "btn_admin_back": "↩️ Admin Menu",
    "menu_access_closed": "Access to the program: 🔴 Closed",
    "menu_access_granted": "Access to the program: 🟢 Granted",
    "menu_pending": "Your application is pending review. Please wait.",
    "menu_telegram_id": "Your Telegram ID: {id}",
    "menu_game_id_none": "Your Game ID: Not set",
    "menu_game_id_set": "Your Game ID: {game_id}",
    "instr_text": (
        "INSTRUCTIONS FOR GETTING STARTED\n"
        "1) Press '💰 Get Promo Code' and subscribe to the channel.\n"
        "2) Register via the exclusive link: {link} (use your promo code during registration).\n"
        "3) Press '🔑 Get Bot Access' and send your 1win account ID.\n"
        "4) Wait for admin approval, then '▶️ Launch Program'."
    ),
    "registration_text": "Register using the link below. Use code: MOB500RR\n{link}",
    "promo_check_prompt": "To receive the promo code, subscribe to our channel: {link}",
    "promo_not_subscribed": "You are not subscribed yet. Subscribe and press '✅ Check Subscription'.",
    "promo_subscribed_success": "Subscription verified! Your promo code: `MOB500RR`",
    "promo_code_already_sent": "You already have the promo code: `MOB500RR`",
    "promo_channel_error": "⚠️ Cannot verify subscription. Ensure the bot is admin in: {channel} with 'view members'.",
    "promo_needed_note": "Please get your promo code first by clicking '💰 Get Promo Code' in the main menu.",
    "awaiting_id_prompt": "Send your 1win account ID (text) or a screenshot showing it.",
    "application_received": "Received. Your request is in the queue. Wait for admin approval.",
    "access_granted_msg": "Access granted! You can now open the program.",
    "access_rejected_msg": "Access was denied. If this is a mistake, please review instructions and reapply.",
    "access_rejected_with_comment_msg": "Access denied. Reason: {comment}",
    "launch_denied": "❌ Access denied. Please submit or wait for approval.",
    "support_link_text": "Click to contact support: {username}",
    "bot_status_text": "Current bot status: {status}",
    "apps_pending_count": "Active requests pending review: {count}",
    "app_processing_info": "Processing request:\nUser: {id}\nGame ID: {game_id}",
    "app_processing_text": "Text: {text}",
    "app_processing_photo": "Photo attached.",
    "app_accepted": "Application ACCEPTED. User notified.",
    "app_rejected": "Application REJECTED. User notified.",
    "prompt_reject_comment": "Send the rejection comment for the user.",
    "comment_sent": "Rejection with comment sent. User notified.",
}

russian_overrides = {
    "welcome": "Добро пожаловать! Выберите язык:",
    "btn_instruction": "📖 Инструкция",
    "btn_registration": "🔗 Регистрация",
    "btn_get_access": "🔑 Получить доступ к боту",
    "btn_change_lang": "🌍 Изменить язык",
    "btn_support": "💬 Поддержка",
    "btn_launch_app": "▶️ Запустить программу",
    "btn_get_promo": "💰 Получить Промокод",
    "btn_check_sub": "✅ Проверить Подписку",
    "menu_access_closed": "Доступ к программе: 🔴 Закрыт",
    "menu_access_granted": "Доступ к программе: 🟢 Выдан",
    "menu_pending": "Ваша заявка на рассмотрении. Пожалуйста, подождите.",
    "menu_telegram_id": "Ваш Telegram ID: {id}",
    "menu_game_id_none": "Ваш Game ID: не указан",
    "menu_game_id_set": "Ваш Game ID: {game_id}",
    "instr_text": (
        "ИНСТРУКЦИЯ\n"
        "1) Нажмите '💰 Получить Промокод' и подпишитесь на канал.\n"
        "2) Зарегистрируйтесь по ссылке: {link} (укажите промокод при регистрации).\n"
        "3) Нажмите '🔑 Получить доступ к боту' и отправьте ID аккаунта 1win.\n"
        "4) Ожидайте одобрения. Затем '▶️ Запустить программу'."
    ),
    "registration_text": "Зарегистрируйтесь по ссылке и используйте код: MOB500RR\n{link}",
    "promo_check_prompt": "Чтобы получить промокод, подпишитесь на канал: {link}",
    "promo_not_subscribed": "Вы еще не подписаны. Подпишитесь и нажмите '✅ Проверить Подписку'.",
    "promo_subscribed_success": "Подписка подтверждена! Ваш промокод: `MOB500RR`",
    "promo_code_already_sent": "У вас уже есть промокод: `MOB500RR`",
    "promo_channel_error": "⚠️ Не удалось проверить подписку. Убедитесь, что бот — админ в канале: {channel} с правом 'просмотра участников'.",
    "promo_needed_note": "Пожалуйста, получите промокод ('💰 Получить Промокод') в главном меню.",
    "awaiting_id_prompt": "Отправьте ваш ID 1win (текстом) или скриншот, где он виден.",
    "application_received": "Принято. Ваша заявка в очереди. Ожидайте одобрения.",
    "access_granted_msg": "Доступ выдан! Теперь вы можете открыть программу.",
    "access_rejected_msg": "Доступ отклонен. Если это ошибка, изучите инструкцию и подайте снова.",
    "access_rejected_with_comment_msg": "Доступ отклонен. Причина: {comment}",
    "launch_denied": "❌ Доступ запрещен. Подайте заявку или дождитесь решения.",
    "support_link_text": "Нажмите для связи с поддержкой: {username}",
    "bot_status_text": "Текущий статус бота: {status}",
    "apps_pending_count": "Заявок в очереди: {count}",
    "app_processing_info": "Обработка заявки:\nПользователь: {id}\nGame ID: {game_id}",
    "app_processing_text": "Текст: {text}",
    "app_processing_photo": "Фото приложено.",
    "app_accepted": "Заявка ПРИНЯТА. Пользователь уведомлен.",
    "app_rejected": "Заявка ОТКЛОНЕНА. Пользователь уведомлен.",
    "prompt_reject_comment": "Отправьте текст причины отказа.",
    "comment_sent": "Отказ с комментарием отправлен. Пользователь уведомлен.",
}

spanish_overrides = {
    "welcome": "¡Bienvenido! Elige tu idioma:",
    "btn_instruction": "📖 Instrucciones",
    "btn_registration": "🔗 Registro",
    "btn_get_access": "🔑 Obtener Acceso al Bot",
    "btn_change_lang": "🌍 Cambiar Idioma",
    "btn_support": "💬 Soporte",
    "btn_launch_app": "▶️ Iniciar Programa",
    "btn_get_promo": "💰 Obtener Código Promocional",
    "btn_check_sub": "✅ Verificar Suscripción",
    "menu_access_closed": "Acceso al programa: 🔴 Cerrado",
    "menu_access_granted": "Acceso al programa: 🟢 Permitido",
    "menu_pending": "Tu solicitud está en revisión. Por favor espera.",
    "menu_telegram_id": "Tu Telegram ID: {id}",
    "menu_game_id_none": "Tu Game ID: no definido",
    "menu_game_id_set": "Tu Game ID: {game_id}",
    "instr_text": (
        "INSTRUCCIONES\n"
        "1) Presiona '💰 Obtener Código Promocional' y suscríbete al canal.\n"
        "2) Regístrate: {link} (usa tu código en el registro).\n"
        "3) Presiona '🔑 Obtener Acceso al Bot' y envía tu ID de 1win.\n"
        "4) Espera la aprobación y luego '▶️ Iniciar Programa'."
    ),
    "registration_text": "Regístrate con el enlace y usa el código: MOB500RR\n{link}",
    "promo_check_prompt": "Para recibir el código promocional, suscríbete al canal: {link}",
    "promo_not_subscribed": "Aún no estás suscrito. Suscríbete y pulsa '✅ Verificar Suscripción'.",
    "promo_subscribed_success": "¡Suscripción verificada! Tu código: `MOB500RR`",
    "promo_code_already_sent": "Ya tienes el código: `MOB500RR`",
    "promo_channel_error": "⚠️ No puedo verificar tu suscripción. Asegúrate de que el bot sea admin en: {channel}.",
    "promo_needed_note": "Por favor, obtén tu código promocional ('💰 Obtener Código Promocional') en el menú principal.",
    "awaiting_id_prompt": "Envía tu ID de 1win (texto) o una captura donde sea visible.",
    "application_received": "Recibido. Tu solicitud está en la cola. Espera la aprobación.",
    "access_granted_msg": "¡Acceso concedido! Ya puedes abrir el programa.",
    "access_rejected_msg": "Acceso denegado. Si es un error, revisa las instrucciones y reenvía.",
    "access_rejected_with_comment_msg": "Acceso denegado. Motivo: {comment}",
    "launch_denied": "❌ Acceso denegado. Envía o espera aprobación.",
    "support_link_text": "Haz clic para soporte: {username}",
    "bot_status_text": "Estado actual del bot: {status}",
    "apps_pending_count": "Solicitudes en revisión: {count}",
    "app_processing_info": "Procesando solicitud:\nUsuario: {id}\nGame ID: {game_id}",
    "app_processing_text": "Texto: {text}",
    "app_processing_photo": "Foto adjunta.",
    "app_accepted": "Solicitud ACEPTADA. Usuario notificado.",
    "app_rejected": "Solicitud RECHAZADA. Usuario notificado.",
    "prompt_reject_comment": "Envía el motivo de rechazo.",
    "comment_sent": "Rechazo con comentario enviado. Usuario notificado.",
}

portuguese_overrides = {
    "welcome": "Bem-vindo! Escolha seu idioma:",
    "btn_instruction": "📖 Instruções",
    "btn_registration": "🔗 Registro",
    "btn_get_access": "🔑 Obter Acesso ao Bot",
    "btn_change_lang": "🌍 Mudar Idioma",
    "btn_support": "💬 Suporte",
    "btn_launch_app": "▶️ Abrir Programa",
    "btn_get_promo": "💰 Obter Código Promocional",
    "btn_check_sub": "✅ Verificar Assinatura",
    "menu_access_closed": "Acesso ao programa: 🔴 Fechado",
    "menu_access_granted": "Acesso ao programa: 🟢 Liberado",
    "menu_pending": "Sua solicitação está em análise. Aguarde.",
    "menu_telegram_id": "Seu Telegram ID: {id}",
    "menu_game_id_none": "Seu Game ID: não definido",
    "menu_game_id_set": "Seu Game ID: {game_id}",
    "instr_text": (
        "INSTRUÇÕES\n"
        "1) Toque em '💰 Obter Código Promocional' e assine o canal.\n"
        "2) Registre-se: {link} (use o código no cadastro).\n"
        "3) Toque em '🔑 Obter Acesso ao Bot' e envie seu ID 1win.\n"
        "4) Aguarde a aprovação e depois '▶️ Abrir Programa'."
    ),
    "registration_text": "Registre-se usando o link e use o código: MOB500RR\n{link}",
    "promo_check_prompt": "Para receber o código promocional, assine nosso canal: {link}",
    "promo_not_subscribed": "Você ainda não assinou. Assine e toque em '✅ Verificar Assinatura'.",
    "promo_subscribed_success": "Assinatura verificada! Seu código: `MOB500RR`",
    "promo_code_already_sent": "Você já tem o código: `MOB500RR`",
    "promo_channel_error": "⚠️ Não é possível verificar a assinatura. Garanta que o bot é admin em: {channel}.",
    "promo_needed_note": "Por favor, obtenha o seu código ('💰 Obter Código Promocional') no menu principal.",
    "awaiting_id_prompt": "Envie seu ID 1win (texto) ou um print mostrando ele.",
    "application_received": "Recebido. Sua solicitação foi para a fila. Aguarde aprovação.",
    "access_granted_msg": "Acesso concedido! Você já pode abrir o programa.",
    "access_rejected_msg": "Acesso negado. Se for engano, revise as instruções e reenvie.",
    "access_rejected_with_comment_msg": "Acesso negado. Motivo: {comment}",
    "launch_denied": "❌ Acesso negado. Envie ou aguarde aprovação.",
    "support_link_text": "Clique para falar com o suporte: {username}",
    "bot_status_text": "Status atual do bot: {status}",
    "apps_pending_count": "Solicitações aguardando revisão: {count}",
    "app_processing_info": "Processando solicitação:\nUsuário: {id}\nGame ID: {game_id}",
    "app_processing_text": "Texto: {text}",
    "app_processing_photo": "Foto anexada.",
    "app_accepted": "Solicitação ACEITA. Usuário notificado.",
    "app_rejected": "Solicitação RECUSADA. Usuário notificado.",
    "prompt_reject_comment": "Envie o motivo de rejeição.",
    "comment_sent": "Rejeição com comentário enviada. Usuário notificado.",
}

MESSAGES = {
    "EN": base_english_messages,
    "RU": {**base_english_messages, **russian_overrides},
    "ES": {**base_english_messages, **spanish_overrides},
    "PT": {**base_english_messages, **portuguese_overrides},
}

# ===================== HELPERS =====================
def user_lang(user_id: int) -> str:
    return USER_DATA.get(user_id, {}).get("lang", "PT")


def set_user_lang(user_id: int, lang: str) -> None:
    USER_DATA.setdefault(user_id, {"lang": "PT", "access": "NONE", "game_id": None})
    USER_DATA[user_id]["lang"] = lang


def t(user_id: int, key: str) -> str:
    lang = user_lang(user_id)
    return MESSAGES.get(lang, MESSAGES["EN"]).get(key, MESSAGES["EN"].get(key, key))


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def get_status(user_id: int) -> str:
    return USER_DATA.get(user_id, {}).get("access", "NONE")


def get_game_id(user_id: int):
    return USER_DATA.get(user_id, {}).get("game_id", None)


def has_promo(user_id: int) -> bool:
    return USER_DATA.get(user_id, {}).get("has_promo", False)


def main_menu_kb(user_id: int) -> ReplyKeyboardMarkup:
    lang = user_lang(user_id)
    b = MESSAGES[lang]
    row1 = [KeyboardButton(b["btn_instruction"]), KeyboardButton(b["btn_registration"])]
    if not has_promo(user_id):
        row2 = [KeyboardButton(b["btn_get_promo"]), KeyboardButton(b["btn_change_lang"])]
    else:
        row2 = [KeyboardButton(b["btn_get_access"]), KeyboardButton(b["btn_change_lang"])]
    row3 = [KeyboardButton(b["btn_support"]), KeyboardButton(b["btn_launch_app"])]
    return ReplyKeyboardMarkup([row1, row2, row3], resize_keyboard=True)


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Português 🇧🇷", callback_data="set_lang_PT")],
            [InlineKeyboardButton("Español 🇪🇸", callback_data="set_lang_ES")],
            [InlineKeyboardButton("Русский 🇷🇺", callback_data="set_lang_RU")],
            [InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_EN")],
        ]
    )


def get_photo_id(key: str):
    fid = PHOTO_IDS.get(key)
    if not fid or (fid and "placeholder" in fid and not GET_FILE_ID_MODE):
        return None
    return fid

# ===================== MODO FILE_ID =====================
async def get_file_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        await update.message.reply_text(f"PHOTO FILE ID: `{file_id}`", parse_mode="Markdown")
        return
    if update.message.document:
        file_id = update.message.document.file_id
        await update.message.reply_text(f"DOCUMENT FILE ID: `{file_id}`", parse_mode="Markdown")
        return
    await update.message.reply_text("Envie uma foto ou documento para obter o file_id.")

# ===================== USUÁRIO: START / IDIOMA / MENU =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    if uid not in USER_DATA:
        lang_code = update.effective_user.language_code
        lang = str(lang_code).upper() if lang_code else "PT"
        if lang not in MESSAGES:
            lang = "PT"
        USER_DATA[uid] = {"lang": lang, "access": "NONE", "game_id": None}
    if is_admin(uid):
        return await admin_start(update, context)
    await update.message.reply_text(t(uid, "welcome"), reply_markup=lang_kb())
    return START_MENU


async def set_lang_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = q.data.split("_")[-1]
    if lang not in MESSAGES:
        lang = "PT"
    set_user_lang(uid, lang)
    try:
        await q.message.delete()
    except Exception:
        pass
    return await show_menu(update, context)


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id if update.effective_user else None
    if update.callback_query:
        uid = update.callback_query.from_user.id
    if not uid:
        return MAIN_MENU
    status = get_status(uid)
    game_id = get_game_id(uid)
    status_text = {
        "GRANTED": t(uid, "menu_access_granted"),
        "PENDING": t(uid, "menu_pending"),
        "DENIED": t(uid, "access_rejected_msg"),
        "NONE": t(uid, "menu_access_closed"),
    }[status]
    gid_line = t(uid, "menu_game_id_set").format(game_id=game_id) if game_id else t(uid, "menu_game_id_none")
    text = f"{status_text}\n\n{t(uid, 'menu_telegram_id').format(id=uid)}\n{gid_line}"
    photo_id = get_photo_id("menu")
    if photo_id:
        await context.bot.send_photo(chat_id=uid, photo=photo_id, caption=text, reply_markup=main_menu_kb(uid))
    else:
        await context.bot.send_message(chat_id=uid, text=text, reply_markup=main_menu_kb(uid))
    return MAIN_MENU


def _txt(update: Update) -> str:
    return (update.message.text or "").strip() if update.message and update.message.text else ""


async def route_main_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    text = _txt(update)
    b = MESSAGES[user_lang(uid)]
    mapping = {
        b["btn_instruction"]: handle_instruction,
        b["btn_registration"]: handle_registration,
        b["btn_get_promo"]: handle_get_promo,
        b["btn_check_sub"]: handle_check_sub_button,
        b["btn_get_access"]: handle_get_access,
        b["btn_launch_app"]: handle_launch,
        b["btn_support"]: handle_support,
        b["btn_change_lang"]: handle_change_lang,
    }
    func = mapping.get(text)
    if func:
        return await func(update, context)
    # fallback
    await update.message.reply_text("Toque em um botão do menu.")
    return MAIN_MENU

# ===================== USUÁRIO: AÇÕES =====================
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
    if has_promo(uid):
        await update.message.reply_text(t(uid, "promo_code_already_sent"), parse_mode="Markdown")
        return MAIN_MENU
    text = t(uid, "promo_check_prompt").format(link=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔗 Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(t(uid, "btn_check_sub"), callback_data="check_sub_now")],
        ]
    )
    await update.message.reply_text(text, reply_markup=kb)
    return AWAITING_CHANNEL_CHECK


async def handle_check_sub_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if has_promo(uid):
        return await show_menu(update, context)
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
        if getattr(member, "status", "") not in {"left", "kicked"}:
            USER_DATA.setdefault(uid, {})["has_promo"] = True
            await q.message.edit_text(t(uid, "promo_subscribed_success"), parse_mode="Markdown")
            return await show_menu(update, context)
        else:
            kb = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔗 Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
                    [InlineKeyboardButton(t(uid, "btn_check_sub"), callback_data="check_sub_now")],
                ]
            )
            await q.message.edit_text(t(uid, "promo_not_subscribed"), reply_markup=kb)
            return AWAITING_CHANNEL_CHECK
    except BadRequest:
        await q.message.reply_text(t(uid, "promo_channel_error").format(channel=CHANNEL_USERNAME))
        return await show_menu(update, context)


async def handle_check_sub_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Se usuário tocar no botão de texto "Check Subscription", reenviamos o inline correto
    uid = update.effective_user.id
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔗 Telegram Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(t(uid, "btn_check_sub"), callback_data="check_sub_now")],
        ]
    )
    await update.message.reply_text(t(uid, "promo_check_prompt").format(link=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"), reply_markup=kb)
    return AWAITING_CHANNEL_CHECK


async def handle_get_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    if not has_promo(uid):
        await update.message.reply_text(t(uid, "promo_needed_note"))
        return MAIN_MENU

    status = get_status(uid)
    if status == "GRANTED":
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton(t(uid, "btn_launch_app"), web_app=WebAppInfo(url=MINI_APP_URL))],
             [InlineKeyboardButton("🆘 Support", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")]]
        )
        await update.message.reply_text(t(uid, "access_granted_msg"), reply_markup=kb)
        return MAIN_MENU
    if status == "PENDING":
        await update.message.reply_text(t(uid, "menu_pending"))
        return MAIN_MENU

    USER_DATA.setdefault(uid, {"lang": user_lang(uid), "access": "NONE", "game_id": None})
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
    # Notifica admins
    for aid in ADMIN_IDS:
        try:
            await context.bot.send_message(aid, f"🆕 New application:\nUser: {uid}\nGame ID: {text}\nQueue: {len(PENDING_QUEUE)}")
        except Exception:
            pass
    await update.message.reply_text(t(uid, "application_received"))
    return await show_menu(update, context)


async def handle_launch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    if get_status(uid) != "GRANTED":
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

# ===================== ADMIN =====================
def admin_kb(uid: int) -> ReplyKeyboardMarkup:
    count = len(PENDING_QUEUE)
    b = MESSAGES["EN"]
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(b["btn_admin_apps"].format(count=count))],
            [KeyboardButton(b["btn_admin_status"]), KeyboardButton(b["btn_admin_stats"])],
            [KeyboardButton(b["btn_admin_broadcast"])],
        ],
        resize_keyboard=True,
    )


async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    await update.message.reply_text("Welcome to Admin Panel.", reply_markup=admin_kb(uid))
    return ADMIN_MENU


def _is_btn(text: str, label: str) -> bool:
    return text == label


async def admin_apps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    count = len(PENDING_QUEUE)
    await update.message.reply_text(MESSAGES["EN"]["apps_pending_count"].format(count=count), reply_markup=admin_kb(uid))
    if count == 0:
        return ADMIN_MENU
    # oferece botão de processar
    kb = ReplyKeyboardMarkup([[KeyboardButton(MESSAGES["EN"]["btn_start_processing"])], [KeyboardButton(MESSAGES["EN"]["btn_admin_back"])]], resize_keyboard=True)
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
    app_text = MESSAGES["EN"]["app_processing_info"].format(id=target, game_id=u.get("game_id", "N/A"))
    parts = [app_text]
    if u.get("game_id"):
        parts.append(MESSAGES["EN"]["app_processing_text"].format(text=u["game_id"]))
    final = "\n".join(parts)
    kb = ReplyKeyboardMarkup(
        [
            [KeyboardButton(MESSAGES["EN"]["btn_accept"])],
            [KeyboardButton(MESSAGES["EN"]["btn_reject"]), KeyboardButton(MESSAGES["EN"]["btn_reject_comment"])],
        ],
        resize_keyboard=True,
    )
    await update.message.reply_text(final, reply_markup=kb)
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
        await context.bot.send_message(target, t(target, "access_granted_msg"))
        await update.message.reply_text(MESSAGES["EN"]["app_accepted"], reply_markup=admin_kb(uid))
        return ADMIN_MENU

    if _is_btn(action, MESSAGES["EN"]["btn_reject"]):
        USER_DATA[target]["access"] = "DENIED"
        STATS["denied"] += 1
        STATS["total_handled"] += 1
        await context.bot.send_message(target, t(target, "access_rejected_msg"))
        await update.message.reply_text(MESSAGES["EN"]["app_rejected"], reply_markup=admin_kb(uid))
        return ADMIN_MENU

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
    await context.bot.send_message(target, t(target, "access_rejected_with_comment_msg").format(comment=comment))
    await update.message.reply_text(MESSAGES["EN"]["comment_sent"], reply_markup=admin_kb(uid))
    return ADMIN_MENU


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
        context.user_data["broadcast_state"] = BROADCAST_NOW_MSG
        await update.message.reply_text("Send your message (text or photo):", reply_markup=ReplyKeyboardRemove())
        return BROADCAST_NOW_MSG
    if _is_btn(action, MESSAGES["EN"]["btn_broadcast_later"]):
        context.user_data["broadcast_type"] = "later"
        context.user_data["broadcast_state"] = BROADCAST_LATER_MSG
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

    if context.user_data.get("broadcast_type") == "now":
        kb = ReplyKeyboardMarkup([[KeyboardButton(MESSAGES["EN"]["btn_confirm"]), KeyboardButton(MESSAGES["EN"]["btn_cancel"])]], resize_keyboard=True)
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
        user_ids = [u for u in USER_DATA.keys() if u not in ADMIN_IDS]
        sent = 0
        for target in user_ids:
            try:
                if photo_id:
                    await context.bot.send_photo(target, photo_id, caption=text or "")
                else:
                    await context.bot.send_message(target, text or "")
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.warning("Broadcast fail to %s: %s", target, e)
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
    user_ids = [u for u in USER_DATA.keys() if u not in ADMIN_IDS]
    sent = 0
    for target in user_ids:
        try:
            if photo_id:
                await context.bot.send_photo(target, photo_id, caption=text or "")
            else:
                await context.bot.send_message(target, text or "")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning("Scheduled broadcast fail to %s: %s", target, e)
    await context.bot.send_message(admin_id, f"✅ Scheduled broadcast completed: {sent}/{len(user_ids)} sent.")

# ===================== BUILD / MAIN =====================
def build_application() -> Application:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    if GET_FILE_ID_MODE:
        app.add_handler(MessageHandler(filters.PHOTO | filters.DOCUMENT | filters.TEXT, get_file_id_handler))
        return app

    user_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_MENU: [CallbackQueryHandler(set_lang_cb, pattern=r"^set_lang_")],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, route_main_buttons),
            ],
            AWAITING_CHANNEL_CHECK: [
                CallbackQueryHandler(handle_check_sub_cb, pattern=r"^check_sub_now$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, route_main_buttons),
            ],
            AWAITING_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_id_input),
            ],
            ADMIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, route_main_buttons),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )
    app.add_handler(user_conv)

    # Admin handlers diretos (usam EN fixo no layout)
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_admin_apps'].split('(')[0])}"), admin_apps))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_start_processing'])}$"), admin_start_processing))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_admin_status'])}$"), admin_status))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_admin_stats'])}$"), admin_stats))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_admin_broadcast'])}$"), admin_broadcast_menu))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_broadcast_now'])}$"), admin_broadcast_start))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_broadcast_later'])}$"), admin_broadcast_start))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_confirm'])}$"), broadcast_confirm_now))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=list(ADMIN_IDS)) & filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_cancel'])}$"), broadcast_confirm_now))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=list(ADMIN_IDS)), admin_process_action))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=list(ADMIN_IDS)) & ~filters.COMMAND, admin_process_comment))
    return app


def main():
    if not BOT_ATIVO:
        print("🚫 Bot desativado pelo admin (BOT_ATIVO=false). Encerrando.")
        return
    app = build_application()
    if GET_FILE_ID_MODE:
        logger.info("GET_FILE_ID_MODE ativo. Envie fotos/documentos para obter file_id.")
    logger.info("🤖 Bot iniciado. Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, poll_interval=1)


if __name__ == "__main__":
    main()
