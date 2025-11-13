import os
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
    ReplyKeyboardMarkup,
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

# ----------------- CONFIG -----------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Defina a variável de ambiente BOT_TOKEN no Railway.")

# IDs dos administradores
ADMIN_IDS = {7428791161, 1993108159}

# Canal para verificação de assinatura
CHANNEL_USERNAME = "@mgoldenmines"

# URL do mini-app
MINI_APP_URL = "https://zenobioyenom.github.io/appmineswin/"

# Suporte
SUPPORT_LINK = "https://t.me/koalamoney3"

# ----------------- LOGGING -----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

# ----------------- ESTADOS -----------------
START_MENU, MAIN_MENU, AWAITING_GAME_ID, AWAITING_ADMIN_COMMENT = range(4)

# ----------------- DADOS EM MEMÓRIA -----------------
USER_DATA = {}
PENDING_QUEUE = []
STATS = {"accepted": 0, "rejected": 0}
# Estrutura USER_DATA[user_id] = {
#   "lang": "pt"|"es"|"ru"|"en",
#   "status": "NONE"|"PENDING"|"GRANTED"|"REJECTED",
#   "game_id": str|None,
# }

# ----------------- TEXTOS -----------------
# Mínimo necessário para roteamento multilíngue por palavras-chave
TXT = {
    "menu_buttons": {
        "instruction": {"pt": "📖 Instruções", "es": "📖 Instrucciones", "ru": "📖 Инструкция", "en": "📖 Instruction"},
        "registration": {"pt": "🔗 Registro", "es": "🔗 Registro", "ru": "🔗 Регистрация", "en": "🔗 Registration"},
        "promo": {"pt": "💰 Obter promo", "es": "💰 Obtener promo", "ru": "💰 Промокод", "en": "💰 Get Promo Code"},
        "check_sub": {"pt": "✅ Verificar inscrição", "es": "✅ Verificar suscripción", "ru": "✅ Проверить подписку", "en": "✅ Check Subscription"},
        "get_access": {"pt": "🔑 Acessar bot", "es": "🔑 Acceso al bot", "ru": "🔑 Доступ к боту", "en": "🔑 Get Bot Access"},
        "launch": {"pt": "▶️ Abrir programa", "es": "▶️ Abrir programa", "ru": "▶️ Открыть приложение", "en": "▶️ Launch Program"},
        "support": {"pt": "💬 Suporte", "es": "💬 Soporte", "ru": "💬 Поддержка", "en": "💬 Support"},
        "change_lang": {"pt": "🌍 Idioma", "es": "🌍 Idioma", "ru": "🌍 Язык", "en": "🌍 Language"},
    },
    "welcome": {
        "pt": "Bem-vindo! Escolha seu idioma:",
        "es": "¡Bienvenido! Elige tu idioma:",
        "ru": "Добро пожаловать! Выберите язык:",
        "en": "Welcome! Choose your language:",
    },
    "status_line": {
        "pt": "Acesso ao programa: {status}\nSeu Telegram ID: {tg_id}\nSeu Game ID: {game_id}",
        "es": "Acceso al programa: {status}\nTu Telegram ID: {tg_id}\nTu Game ID: {game_id}",
        "ru": "Доступ к программе: {status}\nВаш Telegram ID: {tg_id}\nВаш Game ID: {game_id}",
        "en": "Access to the program: {status}\nYour Telegram ID: {tg_id}\nYour Game ID: {game_id}",
    },
    "status_badge": {
        "GRANTED": {"pt": "🟢 Liberado", "es": "🟢 Permitido", "ru": "🟢 Разрешён", "en": "🟢 Granted"},
        "PENDING": {"pt": "🟡 Em análise", "es": "🟡 En revisión", "ru": "🟡 На проверке", "en": "🟡 Pending"},
        "REJECTED": {"pt": "🔴 Negado", "es": "🔴 Denegado", "ru": "🔴 Отклонён", "en": "🔴 Rejected"},
        "NONE": {"pt": "🔴 Fechado", "es": "🔴 Cerrado", "ru": "🔴 Закрыт", "en": "🔴 Closed"},
    },
    "instruction": {
        "pt": "Instruções de uso do bot e mini-app.",
        "es": "Instrucciones de uso del bot y mini-app.",
        "ru": "Инструкция по использованию бота и мини-приложения.",
        "en": "Instructions for using the bot and mini app.",
    },
    "registration": {
        "pt": "Registre-se pelo link e use o código: MOB500RR",
        "es": "Regístrate por el enlace y usa el código: MOB500RR",
        "ru": "Зарегистрируйтесь по ссылке и используйте код: MOB500RR",
        "en": "Register using the link and use code: MOB500RR",
    },
    "send_game_id": {
        "pt": "Envie seu Game ID (texto).",
        "es": "Envía tu Game ID (texto).",
        "ru": "Отправьте ваш Game ID (текст).",
        "en": "Send your Game ID (text).",
    },
    "pending_msg": {
        "pt": "Recebido. Sua solicitação entrou na fila. Aguarde aprovação do admin.",
        "es": "Recibido. Tu solicitud está en la cola. Espera la aprobación del admin.",
        "ru": "Принято. Ваша заявка в очереди. Ожидайте одобрения администратора.",
        "en": "Received. Your request is in the queue. Wait for admin approval.",
    },
    "granted_msg": {
        "pt": "Acesso concedido! Você já pode abrir o programa.",
        "es": "¡Acceso concedido! Ya puedes abrir el programa.",
        "ru": "Доступ предоставлен! Можете открыть приложение.",
        "en": "Access granted! You can now launch the program.",
    },
    "rejected_msg": {
        "pt": "Acesso negado. Entre em contato com o suporte.",
        "es": "Acceso denegado. Contacta con soporte.",
        "ru": "Доступ отклонён. Свяжитесь с поддержкой.",
        "en": "Access denied. Please contact support.",
    },
    "subscribe_first": {
        "pt": "Assine o canal @mgoldenmines e clique em '✅ Verificar inscrição'.",
        "es": "Suscríbete al canal @mgoldenmines y haz clic en '✅ Verificar suscripción'.",
        "ru": "Подпишитесь на канал @mgoldenmines и нажмите '✅ Проверить подписку'.",
        "en": "Subscribe to @mgoldenmines and click '✅ Check Subscription'.",
    },
    "promo_ok": {
        "pt": "Promo liberado: MOB500RR",
        "es": "Promo liberado: MOB500RR",
        "ru": "Промокод выдан: MOB500RR",
        "en": "Promo released: MOB500RR",
    },
}

LANGS = ["pt", "es", "ru", "en"]


def get_lang(user_id: int) -> str:
    ud = USER_DATA.setdefault(user_id, {"lang": "pt", "status": "NONE", "game_id": None})
    return ud.get("lang", "pt")


def set_lang(user_id: int, lang: str) -> None:
    ud = USER_DATA.setdefault(user_id, {"lang": "pt", "status": "NONE", "game_id": None})
    ud["lang"] = lang


def get_status_badge(lang: str, status: str) -> str:
    return TXT["status_badge"].get(status, TXT["status_badge"]["NONE"]).get(lang, "🔴")


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    b = TXT["menu_buttons"]
    rows = [
        [
            KeyboardButton(b["instruction"][lang]),
            KeyboardButton(b["registration"][lang]),
        ],
        [
            KeyboardButton(b["promo"][lang]),
            KeyboardButton(b["check_sub"][lang]),
        ],
        [
            KeyboardButton(b["get_access"][lang]),
            KeyboardButton(b["launch"][lang]),
        ],
        [
            KeyboardButton(b["support"][lang]),
            KeyboardButton(b["change_lang"][lang]),
        ],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def show_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    uid = user.id
    lang = get_lang(uid)
    ud = USER_DATA.get(uid, {"status": "NONE", "game_id": None})
    status_badge = get_status_badge(lang, ud.get("status", "NONE"))
    line = TXT["status_line"][lang].format(
        status=status_badge,
        tg_id=uid,
        game_id=ud.get("game_id") or "Not set",
    )
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=line,
            reply_markup=main_menu_keyboard(lang),
        )
    except Exception as e:
        logger.exception("Erro ao enviar menu: %s", e)
    return MAIN_MENU


# ----------------- HANDLERS: INÍCIO -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    # Admins: manter fluxo do admin separado (se você já tem outro ConversationHandler para admin)
    if uid in ADMIN_IDS:
        # Você pode redirecionar para show_main também, ou chamar um admin_start personalizado
        return await show_main(update, context)

    # Usuário comum: mostrar seleção de idioma via inline
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Português 🇧🇷", callback_data="set_lang_pt"),
                InlineKeyboardButton("Español 🇪🇸", callback_data="set_lang_es"),
            ],
            [
                InlineKeyboardButton("Русский 🇷🇺", callback_data="set_lang_ru"),
                InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_en"),
            ],
        ]
    )
    try:
        await update.message.reply_text(TXT["welcome"]["pt"], reply_markup=kb)
    except Exception as e:
        logger.exception("Erro ao enviar welcome: %s", e)
    return START_MENU


async def set_language_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    try:
        _, _, lang = data.split("_", 2)  # set_lang_pt
    except Exception:
        lang = "pt"
    if lang not in LANGS:
        lang = "pt"
    set_lang(query.from_user.id, lang)
    # Tenta apagar a mensagem de seleção
    try:
        await query.message.delete()
    except Exception:
        pass
    # Vai para o menu principal
    fake_update = Update(
        update.update_id,
        message=query.message  # reusa chat para enviar menu
    )
    return await show_main(fake_update, context)


# ----------------- ROTEADOR DE BOTÕES (MAIN_MENU) -----------------
def _text(update: Update) -> str:
    if update.message and update.message.text:
        return update.message.text.strip()
    return ""


async def route_main_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    lang = get_lang(uid)
    text = _text(update)

    b = TXT["menu_buttons"]
    # Mapeamento por presença de rótulos por idioma; evita regex com emoji
    if text in {b["instruction"][l] for l in LANGS}:
        return await handle_instruction(update, context)
    if text in {b["registration"][l] for l in LANGS}:
        return await handle_registration(update, context)
    if text in {b["promo"][l] for l in LANGS}:
        return await handle_get_promo(update, context)
    if text in {b["check_sub"][l] for l in LANGS}:
        return await handle_check_subscription_button(update, context)
    if text in {b["get_access"][l] for l in LANGS}:
        return await handle_get_access(update, context)
    if text in {b["launch"][l] for l in LANGS}:
        return await handle_launch(update, context)
    if text in {b["support"][l] for l in LANGS}:
        return await handle_support(update, context)
    if text in {b["change_lang"][l] for l in LANGS}:
        return await handle_change_lang(update, context)

    # Fallback de depuração
    logger.debug("MAIN_MENU sem match. Texto recebido: %r", text)
    try:
        await update.message.reply_text("Não entendi. Toque em um botão do menu.")
    except Exception:
        pass
    return MAIN_MENU


# ----------------- HANDLERS DE AÇÃO -----------------
async def handle_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    lang = get_lang(uid)
    await update.message.reply_text(TXT["instruction"][lang])
    return MAIN_MENU


async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    lang = get_lang(uid)
    reg_text = TXT["registration"][lang] + "\n\nhttps://1wtsks.com/v3/landing-fortune-wheel?p=gv72\nCódigo: MOB500RR"
    await update.message.reply_text(reg_text)
    return MAIN_MENU


async def handle_get_promo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    lang = get_lang(uid)
    # Envia instrução com botão para verificar assinatura (callback)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(TXT["menu_buttons"]["check_sub"][lang], callback_data="check_sub_now")]]
    )
    await update.message.reply_text(TXT["subscribe_first"][lang], reply_markup=kb)
    return MAIN_MENU


async def handle_check_subscription_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Caso o usuário aperte o botão de texto “✅ Verificar inscrição” do teclado (não inline),
    # apenas reenvie a instrução com o botão inline correto.
    uid = update.effective_user.id
    lang = get_lang(uid)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(TXT["menu_buttons"]["check_sub"][lang], callback_data="check_sub_now")]]
    )
    await update.message.reply_text(TXT["subscribe_first"][lang], reply_markup=kb)
    return MAIN_MENU


async def check_subscription_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # CallbackQueryHandler para "check_sub_now"
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    lang = get_lang(uid)
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
        status = getattr(member, "status", "")
        ok = status in {"member", "administrator", "creator"}
    except Exception as e:
        logger.warning("Falha ao verificar assinatura: %s", e)
        ok = False

    if ok:
        await query.edit_message_text(TXT["promo_ok"][lang])
    else:
        await query.edit_message_text(TXT["subscribe_first"][lang])
    return MAIN_MENU


async def handle_get_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    lang = get_lang(uid)
    USER_DATA.setdefault(uid, {"lang": lang, "status": "NONE", "game_id": None})
    await update.message.reply_text(TXT["send_game_id"][lang])
    return AWAITING_GAME_ID


async def handle_game_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    lang = get_lang(uid)
    game_id = _text(update)
    if not game_id or game_id.startswith("/"):
        await update.message.reply_text(TXT["send_game_id"][lang])
        return AWAITING_GAME_ID

    USER_DATA.setdefault(uid, {"lang": lang, "status": "NONE", "game_id": None})
    USER_DATA[uid]["game_id"] = game_id
    USER_DATA[uid]["status"] = "PENDING"

    if uid not in PENDING_QUEUE:
        PENDING_QUEUE.append(uid)

    # Notifica admins
    for aid in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=aid,
                text=f"🆕 Nova solicitação\nUser: {uid}\nGame ID: {game_id}\nNa fila: {len(PENDING_QUEUE)}",
            )
        except Exception:
            pass

    await update.message.reply_text(TXT["pending_msg"][lang])
    # volta ao menu
    return await show_main(update, context)


async def handle_launch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    lang = get_lang(uid)
    status = USER_DATA.get(uid, {}).get("status", "NONE")
    if status != "GRANTED":
        await update.message.reply_text(TXT["status_line"][lang].format(
            status=get_status_badge(lang, status),
            tg_id=uid,
            game_id=USER_DATA.get(uid, {}).get("game_id") or "Not set",
        ))
        return MAIN_MENU

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=TXT["menu_buttons"]["launch"][lang],
                    web_app=WebAppInfo(MINI_APP_URL),
                )
            ]
        ]
    )
    await update.message.reply_text(TXT["granted_msg"][lang], reply_markup=kb)
    return MAIN_MENU


async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(f"Suporte: {SUPPORT_LINK}")
    return MAIN_MENU


async def handle_change_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Português 🇧🇷", callback_data="set_lang_pt"),
                InlineKeyboardButton("Español 🇪🇸", callback_data="set_lang_es"),
            ],
            [
                InlineKeyboardButton("Русский 🇷🇺", callback_data="set_lang_ru"),
                InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_en"),
            ],
        ]
    )
    await update.message.reply_text("Idioma / Language / Язык / Idioma:", reply_markup=kb)
    return START_MENU


# ----------------- DEBUG FALLBACK -----------------
async def debug_echo_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Captura tudo que não casou no MAIN_MENU
    logger.debug("DEBUG ECHO MAIN | Texto recebido: %r", _text(update))
    return MAIN_MENU


# ----------------- ADMIN APROVAÇÃO (EXEMPLO SIMPLES) -----------------
# Aqui deixamos um comando simples para conceder acesso manualmente:
# /grant <user_id>
async def grant_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Uso: /grant <user_id>")
        return
    try:
        target = int(args[0])
    except Exception:
        await update.message.reply_text("ID inválido.")
        return
    USER_DATA.setdefault(target, {"lang": "pt", "status": "NONE", "game_id": None})
    USER_DATA[target]["status"] = "GRANTED"
    if target in PENDING_QUEUE:
        PENDING_QUEUE.remove(target)
    lang = get_lang(target)
    try:
        await context.bot.send_message(chat_id=target, text=TXT["granted_msg"][lang])
    except Exception:
        pass
    await update.message.reply_text(f"Acesso concedido para {target}.")


# ----------------- APLICAÇÃO -----------------
def build_application():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation do usuário
    user_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_MENU: [
                CallbackQueryHandler(set_language_cb, pattern=r"^set_lang_"),
            ],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, route_main_buttons),
                MessageHandler(filters.ALL & ~filters.COMMAND, debug_echo_main),  # fallback de debug
            ],
            AWAITING_GAME_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_game_id_input),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )
    app.add_handler(user_conv)

    # Callback de verificação de assinatura (inline), disponível globalmente
    app.add_handler(CallbackQueryHandler(check_subscription_cb, pattern=r"^check_sub_now$"))

    # Comando admin simples para conceder acesso
    app.add_handler(CommandHandler("grant", grant_cmd))

    return app


def main():
    app = build_application()
    logger.info("Bot iniciado. Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
