import logging
import asyncio 
import re 
import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler, ContextTypes
from telegram.helpers import escape_markdown 
from telegram.error import BadRequest
from functools import wraps
from collections import deque

# --- LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION & CONSTANTS ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "7692269177:AAGnz7egfTyoMwDY2y1px8Wmok-2W0BCecg")
ADMIN_IDS = [7428791161, 1993108159]  # ✅ LISTA CORRIGIDA
SUPPORT_USERNAME = "@koalamoney3"
PROMO_CODE = "MOB500RR"
REG_LINK = "https://1wbkpnt.com/?open=register&p=gv72"
CHANNEL_USERNAME = "@mgoldenmines"  # ✅ CORRIGIDO: canal em formato @username
MINI_APP_URL = "https://zenobioyenom.github.io/appmineswin/"
DB_FILE = 'bot_data.json'

# Modo temporário para capturar file_ids
GET_FILE_ID_MODE = False

# Dicionário de file_ids (preenchido após coleta)
PHOTO_IDS = {
    'privet': 'placeholder',
    'menu': 'placeholder',
    'instr': 'placeholder',
    'id_example': 'placeholder',
    'reg_RU': 'placeholder',
    'reg_EN': 'placeholder',
    'reg_ES': 'placeholder',
    'reg_PT': 'placeholder',
}

# --- CONVERSATION STATES ---
START_MENU, MAIN_MENU = range(2)
AWAITING_ID, AWAITING_CHANNEL_CHECK = range(2, 4)
ADMIN_MENU, ADMIN_BROADCAST_MENU = range(4, 6)
BROADCAST_NOW_MSG, BROADCAST_NOW_CONFIRM = range(6, 8)
BROADCAST_LATER_MSG, BROADCAST_LATER_TIME, BROADCAST_LATER_CONFIRM = range(8, 11)
PROCESSING_REQUESTS, PROCESS_REQUEST_COMMENT = range(11, 13)

# --- SIMULATION OF DATABASE (In-memory) ---
USER_DATA = {}
PENDING_QUEUE = deque([])
STATS = {
    'accepted': 0,
    'denied': 0,
    'corrected': 0,
    'total_handled': 0,
    'bot_status': '✅ Operating normally'
}

# --- MULTILINGUAL MESSAGES ---
base_english_messages = {
    'start_user': "🌐 Select your language / Elige tu idioma / Escolha o idioma 🌐",
    'start_admin': "Hi, Admin! I've recognized your ID — welcome back! 🤖",
    'language_set': "Language set to English.",
    'admin_access_denied': "Access denied. You are not an administrator.",
    
    'btn_instruction': "📖 Instruction",
    'btn_registration': "🔗 Registration",
    'btn_get_access': "🔑 Get Bot Access",
    'btn_change_lang': "🌍 Change Language",
    'btn_support': "💬 Contact Support",
    'btn_launch_app': "▶️ Launch Program",
    'btn_menu_back': "↩️ Back to Menu",
    'btn_get_promo': "💰 Get Promo Code",
    'btn_check_sub': "✅ Check Subscription",
    
    'menu_access_closed': "Access to the program: 🔴 Closed",
    'menu_access_granted': "Access to the program: 🟢 Granted",
    'menu_telegram_id': "Your Telegram ID: {id}",
    'menu_game_id_none': "Your Game ID: Not set",
    'menu_game_id_set': "Your Game ID: {game_id}",
    'menu_pending': "Your application is pending review. Please wait.",
    'access_granted_msg': "Congratulations! Access has been granted. You can now use the 'Launch Program' button.",
    'access_rejected_msg': "Access was denied. Please check the instructions and try again.",
    'access_rejected_with_comment_msg': "Access was denied. Reason: {comment}",
    'awaiting_id_prompt': "Please send your account ID or a screenshot showing the ID.",
    'application_received': "Information accepted. Verification process started. You will receive access notification shortly.",
    'promo_needed_note': "Please get your promo code first by clicking '💰 Get Promo Code' in the main menu.",
    
    'promo_check_prompt': "To receive the promo code, you must subscribe to our channel: {link}",
    'promo_not_subscribed': "You are not yet subscribed. Please subscribe and press the 'Check Subscription' button.",
    'promo_subscribed_success': "Subscription verified! Your exclusive promo code is: `{promo}`. Use it during registration.",
    'promo_code_already_sent': "You already have the promo code: `{promo}`. Use it for registration.",
    'promo_channel_error': "⚠️ Cannot verify subscription. Ensure the bot is **admin** in the channel: `{channel}` with **view members** permission.",
    
    'instr_text': (
        "INSTRUCTIONS FOR GETTING STARTED\n"
        "Follow these steps for correct connection:\n"
        "1) Get the exclusive promo code by pressing '💰 Get Promo Code'.\n"
        "2) Register using: {link}\n"
        "Use the promo code during registration.\n"
        "3) Click '🔑 Get Bot Access' in this chat.\n"
        "4) Send your 1win account ID (account number).\n"
        "5) Wait for connection. Access will be granted upon completion."
    ),
    
    # Admin Messages
    'btn_admin_apps': "🧾 Applications ({count})",
    'btn_admin_status': "🤖 Bot Status",
    'btn_admin_stats': "📊 Statistics",
    'btn_admin_broadcast': "💬 User Messages",
    'btn_accept': "✅ Accept",
    'btn_reject': "❌ Reject",
    'btn_reject_comment': "💬 Reject with comments",
    'btn_broadcast_now': "Send Now",
    'btn_broadcast_later': "Send Later",
    'btn_confirm': "✅ Confirm",
    'btn_cancel': "❌ Cancel",
    'btn_admin_back': "↩️ Admin Menu",
    
    'apps_pending_count': "Active requests pending review: {count}",
    'app_processing_info': "Processing request:\nUser: {id}\nGame ID: {game_id}",
    'app_processing_text': "Text: {text}",
    'app_processing_photo': "Photo attached.",
    'app_accepted': "Application ACCEPTED. User notified.",
    'app_rejected': "Application REJECTED. User notified.",
    'prompt_reject_comment': "Please send the rejection comment to send to the user.",
    'comment_sent': "Application REJECTED with comment. User notified.",
    'stats_text': "Statistics:\nAccepted: {a}\nDenied: {d}\nCorrected: {c}\nTotal Handled: {t}",
    'bot_status_text': "Current bot status: {status}",
    'prompt_broadcast_msg': "Please send the message (text and/or photo) for broadcast.",
    'confirm_broadcast_now': "CONFIRM: Send this message to all users NOW.",
    'broadcast_success': "Broadcast sent successfully to all active users.",
    'prompt_broadcast_time': "Specify time and date (e.g., 2025-10-25 14:30) for scheduled broadcast.",
    'confirm_broadcast_later': "CONFIRM: This message is scheduled for {time} UTC.",
    'broadcast_scheduled': "Broadcast scheduled for {time}.",
    'broadcast_cancelled': "Broadcast cancelled. Returning to Admin Menu.",
}

russian_overrides = {
    'language_set': "Язык установлен на Русский.",
    'btn_instruction': "📖 Инструкция",
    'btn_registration': "🔗 Регистрация",
    'btn_get_access': "🔑 Получить доступ к боту",
    'btn_change_lang': "🌍 Изменить язык",
    'btn_support': "💬 Обратиться в поддержку",
    'btn_launch_app': "▶️ Запустить программу",
    'btn_get_promo': "💰 Получить Промокод",
    'btn_check_sub': "✅ Проверить Подписку",
    'menu_access_closed': "Доступ к программе: 🔴 Закрыт",
    'menu_access_granted': "Доступ к программе: 🟢 Выдан",
    'menu_pending': "Ваша заявка на рассмотрении. Пожалуйста, подождите.",
    'promo_needed_note': "Пожалуйста, получите промокод, нажав '💰 Получить Промокод' в главном меню.",
    'promo_not_subscribed': "Вы еще не подписаны. Подпишитесь и нажмите '✅ Проверить Подписку'.",
    'promo_channel_error': "⚠️ Не удалось проверить подписку. Убедитесь, что бот **администратор** в канале: `{channel}` с правом **просмотра участников**.",
    'instr_text': (
        "ИНСТРУКЦИЯ ПО НАЧАЛУ РАБОТЫ\n"
        "Выполните следующие шаги для подключения:\n"
        "1) Получите промокод, нажав '💰 Получить Промокод'.\n"
        "2) Зарегистрируйтесь по ссылке: {link}\n"
        "При регистрации используйте полученный промокод.\n"
        "3) Нажмите '🔑 Получить доступ к боту' в этом чате.\n"
        "4) Отправьте ваш ID счета 1win.\n"
        "5) Ожидайте подключения. Доступ будет выдан после завершения."
    ),
}

spanish_overrides = {
    'language_set': "Idioma establecido a Español.",
    'btn_instruction': "📖 Instrucciones",
    'btn_registration': "🔗 Registro",
    'btn_get_access': "🔑 Obtener Acceso al Bot",
    'btn_change_lang': "🌍 Cambiar Idioma",
    'btn_support': "💬 Contactar Soporte",
    'btn_launch_app': "▶️ Iniciar Programa",
    'btn_get_promo': "💰 Obtener Código Promocional",
    'btn_check_sub': "✅ Verificar Suscripción",
    'promo_needed_note': "Por favor, obtenga su código promocional haciendo clic en '💰 Obtener Código Promocional'.",
    'instr_text': (
        "INSTRUCCIONES PARA EMPEZAR\n"
        "Siga estos pasos para la conexión correcta:\n"
        "1) Obtenga el código promocional exclusivo pulsando '💰 Obtener Código Promocional'.\n"
        "2) Regístrese usando: {link}\n"
        "Use el código promocional durante el registro.\n"
        "3) Haga clic en '🔑 Obtener Acceso al Bot' en este chat.\n"
        "4) Envíe su ID de cuenta 1win.\n"
        "5) Espere la conexión. El acceso será concedido al completarse."
    ),
}

portuguese_overrides = {
    'language_set': "Idioma definido para Português.",
    'btn_instruction': "📖 Instruções",
    'btn_registration': "🔗 Registro",
    'btn_get_access': "🔑 Obter Acesso ao Bot",
    'btn_change_lang': "🌍 Mudar Idioma",
    'btn_support': "💬 Contatar Suporte",
    'btn_launch_app': "▶️ Lançar Programa",
    'btn_get_promo': "💰 Obter Código Promocional",
    'btn_check_sub': "✅ Verificar Assinatura",
    'promo_needed_note': "Por favor, obtenha seu código promocional clicando em '💰 Obter Código Promocional'.",
    'instr_text': (
        "INSTRUÇÕES PARA COMEÇAR\n"
        "Siga estas etapas para a conexão correta:\n"
        "1) Obtenha o código promocional exclusivo pressionando '💰 Obter Código Promocional'.\n"
        "2) Registre-se usando: {link}\n"
        "Use o código promocional durante o registro.\n"
        "3) Clique em '🔑 Obter Acesso ao Bot' neste chat.\n"
        "4) Envie seu ID de conta 1win.\n"
        "5) Aguarde a conexão. O acesso será concedido ao concluir."
    ),
}

MESSAGES = {
    'EN': base_english_messages,
    'RU': {**base_english_messages, **russian_overrides},
    'ES': {**base_english_messages, **spanish_overrides},
    'PT': {**base_english_messages, **portuguese_overrides},
}

# --- PERSISTENCE FUNCTIONS ---

def load_db():
    """Load data from JSON file."""
    global USER_DATA, PENDING_QUEUE, STATS
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                USER_DATA = data.get('user_data', {})
                PENDING_QUEUE = deque(data.get('pending_queue', []))
                STATS = data.get('stats', STATS)
                logger.info("Database loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading database: {e}")
    else:
        logger.info("No database file found. Starting with empty data.")

def save_db():
    """Save data to JSON file."""
    try:
        data = {
            'user_data': USER_DATA,
            'pending_queue': list(PENDING_QUEUE),
            'stats': STATS
        }
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info("Database saved successfully.")
    except Exception as e:
        logger.error(f"Error saving database: {e}")

# Load database on startup
load_db()

# --- UTILITY FUNCTIONS ---

def get_message(user_id, key, **kwargs):
    """Get message in user's language."""
    if user_id in ADMIN_IDS:  # ✅ CORRIGIDO: usar 'in' em vez de '=='
        lang = 'EN'
    else:
        lang = USER_DATA.get(str(user_id), {}).get('lang', 'EN')
    
    text = MESSAGES.get(lang, MESSAGES['EN']).get(key, f"MISSING_KEY:{key}")
    return text.format(**kwargs) if kwargs else text

def get_photo_id(key):
    """Get photo file ID or None if placeholder."""
    file_id = PHOTO_IDS.get(key, None)
    if not file_id or (not GET_FILE_ID_MODE and 'placeholder' in file_id):
        return None
    return file_id

def admin_only(func):
    """Decorator to restrict access to admin functions."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id in ADMIN_IDS:  # ✅ CORRIGIDO: usar 'in' em vez de '=='
            return await func(update, context, *args, **kwargs)
        else:
            if update.message:
                await update.message.reply_text("❌ Access denied. Admin only.")
            return MAIN_MENU
    return wrapper

def get_user_status(user_id):
    """Get user access status: PENDING, GRANTED, DENIED or NONE."""
    return USER_DATA.get(str(user_id), {}).get('access', 'NONE')

def get_user_game_id(user_id):
    """Get user's game ID."""
    return USER_DATA.get(str(user_id), {}).get('game_id', None)

def has_promo_code(user_id):
    """Check if user has received promo code."""
    return USER_DATA.get(str(user_id), {}).get('has_promo', False)

# --- KEYBOARD FUNCTIONS ---

def get_lang_keyboard():
    """Language selection keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("English", callback_data='set_lang_EN')],
        [InlineKeyboardButton("Русский", callback_data='set_lang_RU')],
        [InlineKeyboardButton("Español", callback_data='set_lang_ES')],
        [InlineKeyboardButton("Português", callback_data='set_lang_PT')],
    ])

def get_main_menu_keyboard(user_id):
    """Main menu keyboard for user."""
    user_id_str = str(user_id)
    row1 = [
        KeyboardButton(get_message(user_id, 'btn_instruction')),
        KeyboardButton(get_message(user_id, 'btn_registration'))
    ]
    
    if not has_promo_code(user_id):
        row2 = [
            KeyboardButton(get_message(user_id, 'btn_get_promo')),
            KeyboardButton(get_message(user_id, 'btn_change_lang'))
        ]
    else:
        row2 = [
            KeyboardButton(get_message(user_id, 'btn_get_access')),
            KeyboardButton(get_message(user_id, 'btn_change_lang'))
        ]
    
    row3 = [
        KeyboardButton(get_message(user_id, 'btn_support')),
        KeyboardButton(get_message(user_id, 'btn_launch_app'))
    ]
    
    buttons = [row1, row2, row3]
    
    if user_id in ADMIN_IDS:  # ✅ CORRIGIDO: usar 'in' em vez de '=='
        buttons.append([KeyboardButton(get_message(user_id, 'btn_admin_back'))])
    
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_admin_main_keyboard(admin_id):
    """Admin main menu keyboard."""
    count = len(PENDING_QUEUE)
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_admin_apps').format(count=count))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_status')), 
         KeyboardButton(get_message(admin_id, 'btn_admin_stats'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_broadcast'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_back'))],
    ], resize_keyboard=True)

def get_admin_processing_keyboard(admin_id):
    """Admin processing keyboard."""
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_accept'))],
        [KeyboardButton(get_message(admin_id, 'btn_reject')), 
         KeyboardButton(get_message(admin_id, 'btn_reject_comment'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_back'))],
    ], resize_keyboard=True)

def get_confirm_keyboard(admin_id):
    """Confirmation keyboard."""
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_confirm')), 
         KeyboardButton(get_message(admin_id, 'btn_cancel'))],
    ], resize_keyboard=True)

def get_admin_broadcast_keyboard(admin_id):
    """Broadcast type selection keyboard."""
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_broadcast_now')), 
         KeyboardButton(get_message(admin_id, 'btn_broadcast_later'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_back'))],
    ], resize_keyboard=True)

# --- USER HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command."""
    user_id = update.effective_user.id
    user_id_str = str(user_id)
    
    if user_id_str not in USER_DATA:
        lang_code = update.effective_user.language_code
        USER_DATA[user_id_str] = {
            'lang': lang_code.upper() if lang_code and lang_code.upper() in MESSAGES else 'EN',
            'access': 'NONE',
            'game_id': None,
            'application_info': None,
            'has_promo': False
        }
        save_db()
    
    if user_id in ADMIN_IDS:  # ✅ CORRIGIDO: usar 'in' em vez de '=='
        await update.message.reply_text(
            get_message(user_id, 'start_admin'),
            reply_markup=get_admin_main_keyboard(user_id)
        )
        return ADMIN_MENU
    else:
        await update.message.reply_text(
            get_message(user_id, 'start_user'),
            reply_markup=get_lang_keyboard()
        )
        return START_MENU

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Set user language."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_id_str = str(user_id)
    lang_code = query.data.split('_')[2]
    
    USER_DATA[user_id_str]['lang'] = lang_code
    save_db()
    logger.info(f"User {user_id} set language to {lang_code}")
    
    await query.message.delete()
    await show_user_main_menu(update, context)
    return MAIN_MENU

async def show_user_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main user menu."""
    if update.callback_query:
        user_id = update.callback_query.from_user.id
    else:
        user_id = update.message.from_user.id
    
    status = get_user_status(user_id)
    game_id = get_user_game_id(user_id)
    
    status_line = {
        'GRANTED': get_message(user_id, 'menu_access_granted'),
        'DENIED': 'Access: ❌ Denied',
        'PENDING': get_message(user_id, 'menu_pending'),
    }.get(status, get_message(user_id, 'menu_access_closed'))
    
    game_id_line = get_message(user_id, 'menu_game_id_none')
    if game_id:
        game_id_line = get_message(user_id, 'menu_game_id_set', game_id=game_id)
    
    text = (
        f"{status_line}\n\n"
        f"{get_message(user_id, 'menu_telegram_id', id=user_id)}\n"
        f"{game_id_line}"
    )
    
    await context.bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=get_main_menu_keyboard(user_id)
    )

async def handle_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle instruction button."""
    user_id = update.effective_user.id
    text = get_message(user_id, 'instr_text', link=REG_LINK)
    
    await update.message.reply_text(text, reply_markup=get_main_menu_keyboard(user_id))
    return MAIN_MENU

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle registration button."""
    user_id = update.effective_user.id
    
    if has_promo_code(user_id):
        promo_note = f"Promo code: `{PROMO_CODE}`"
    else:
        promo_note = get_message(user_id, 'promo_needed_note')
    
    text = f"Register using the exclusive link: {REG_LINK}\n{promo_note}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Register", url=REG_LINK)],
    ])
    
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    return MAIN_MENU

async def handle_get_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start promo code process."""
    user_id = update.effective_user.id
    
    if has_promo_code(user_id):
        text = get_message(user_id, 'promo_code_already_sent', promo=PROMO_CODE)
        await update.message.reply_text(text, reply_markup=get_main_menu_keyboard(user_id), parse_mode='Markdown')
        return MAIN_MENU
    
    text = get_message(user_id, 'promo_check_prompt', link=CHANNEL_USERNAME)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(get_message(user_id, 'btn_check_sub'), callback_data='check_sub_now')],
    ])
    
    await update.message.reply_text(text, reply_markup=keyboard)
    return AWAITING_CHANNEL_CHECK

async def handle_check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check channel subscription."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_id_str = str(user_id)
    
    if has_promo_code(user_id):
        await show_user_main_menu(update, context)
        return MAIN_MENU
    
    try:
        # ✅ CORRIGIDO: usar CHANNEL_USERNAME corretamente
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        if member.status not in ['left', 'kicked']:
            USER_DATA[user_id_str]['has_promo'] = True
            save_db()
            
            text = get_message(user_id, 'promo_subscribed_success', promo=PROMO_CODE)
            await query.message.edit_text(text, parse_mode='Markdown')
            await show_user_main_menu(update, context)
            return MAIN_MENU
        else:
            text = get_message(user_id, 'promo_not_subscribed')
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
                [InlineKeyboardButton(get_message(user_id, 'btn_check_sub'), callback_data='check_sub_now')],
            ])
            await query.message.edit_text(text, reply_markup=keyboard)
            return AWAITING_CHANNEL_CHECK
            
    except BadRequest as e:
        logger.error(f"Subscription check error for {user_id}: {e}")
        error_text = get_message(user_id, 'promo_channel_error', channel=CHANNEL_USERNAME)
        await query.message.reply_text(error_text, parse_mode='Markdown')
        await show_user_main_menu(update, context)
        return MAIN_MENU

async def handle_get_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start access request process."""
    user_id = update.effective_user.id
    user_id_str = str(user_id)
    status = get_user_status(user_id)
    
    if not has_promo_code(user_id):
        await update.message.reply_text(get_message(user_id, 'promo_needed_note'))
        return MAIN_MENU
    
    if status == 'GRANTED':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(get_message(user_id, 'btn_launch_app'), 
                                 web_app=WebAppInfo(url=MINI_APP_URL))],
            [InlineKeyboardButton("🆘 Support", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
        ])
        await update.message.reply_text(
            get_message(user_id, 'access_granted_msg'),
            reply_markup=keyboard
        )
        return MAIN_MENU
    
    if status == 'PENDING':
        await update.message.reply_text(get_message(user_id, 'menu_pending'))
        return MAIN_MENU
    
    USER_DATA[user_id_str]['application_info'] = {'text': None, 'photo_id': None}
    save_db()
    
    text = get_message(user_id, 'awaiting_id_prompt')
    await update.message.reply_text(text)
    return AWAITING_ID

async def handle_user_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user ID or screenshot submission."""
    user_id = update.effective_user.id
    user_id_str = str(user_id)
    app_info = USER_DATA[user_id_str].get('application_info', {})
    
    if update.message.text:
        game_id = update.message.text.strip()
        if not re.match(r'^\d{4,}$', game_id):
            await update.message.reply_text(get_message(user_id, 'awaiting_id_prompt'))
            return AWAITING_ID
        
        app_info['text'] = game_id
        USER_DATA[user_id_str]['game_id'] = game_id
        
    elif update.message.photo:
        photo_id = update.message.photo[-1].file_id
        app_info['photo_id'] = photo_id
    
    if app_info.get('text'):
        USER_DATA[user_id_str]['access'] = 'PENDING'
        PENDING_QUEUE.append(user_id)
        save_db()
        
        await update.message.reply_text(get_message(user_id, 'application_received'))
        
        # ✅ CORRIGIDO: notificar todos os admins
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"🔔 NEW APPLICATION from User ID: {user_id}\n"
                    f"Queue length: {len(PENDING_QUEUE)}"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
        
        return MAIN_MENU
    
    return AWAITING_ID

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle support button."""
    user_id = update.effective_user.id
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Support", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
    ])
    
    await update.message.reply_text("Click to contact support:", reply_markup=keyboard)
    return MAIN_MENU

async def handle_launch_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle launch app button."""
    user_id = update.effective_user.id
    status = get_user_status(user_id)
    
    if status == 'GRANTED':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(get_message(user_id, 'btn_launch_app'), 
                                 web_app=WebAppInfo(url=MINI_APP_URL))],
        ])
        await update.message.reply_text("✅ Access granted. Click to launch:", reply_markup=keyboard)
    else:
        await update.message.reply_text("❌ Access not granted. Please complete the application process.")
    
    return MAIN_MENU

async def handle_change_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language change."""
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        get_message(user_id, 'start_user'),
        reply_markup=get_lang_keyboard()
    )
    return START_MENU

async def go_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to main menu."""
    await show_user_main_menu(update, context)
    return MAIN_MENU

# --- ADMIN HANDLERS ---

@admin_only
async def admin_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show admin menu."""
    admin_id = update.effective_user.id
    await update.message.reply_text(
        "Welcome to Admin Panel.",
        reply_markup=get_admin_main_keyboard(admin_id)
    )
    return ADMIN_MENU

@admin_only
async def admin_apps_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show applications count."""
    admin_id = update.effective_user.id
    count = len(PENDING_QUEUE)
    
    text = f"Pending applications: {count}"
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("🚀 Start Processing")],
        [KeyboardButton("↩️ Back")],
    ], resize_keyboard=True)
    
    await update.message.reply_text(text, reply_markup=keyboard)
    return ADMIN_MENU

@admin_only
async def start_processing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start processing applications."""
    admin_id = update.effective_user.id
    
    if not PENDING_QUEUE:
        await update.message.reply_text(
            "No pending requests.",
            reply_markup=get_admin_main_keyboard(admin_id)
        )
        return ADMIN_MENU
    
    target_user_id = PENDING_QUEUE.popleft()
    context.user_data['target_user_id'] = target_user_id
    save_db()
    
    user_data = USER_DATA.get(str(target_user_id), {})
    app_info = user_data.get('application_info', {})
    
    text = f"Processing user: {target_user_id}\nGame ID: {user_data.get('game_id', 'N/A')}"
    
    if app_info.get('text'):
        text += f"\nSubmitted ID: {app_info['text']}"
    
    await update.message.reply_text(
        text,
        reply_markup=get_admin_processing_keyboard(admin_id)
    )
    
    return PROCESSING_REQUESTS

@admin_only
async def process_request_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle application actions."""
    admin_id = update.effective_user.id
    action = update.message.text
    target_user_id = context.user_data.get('target_user_id')
    
    if not target_user_id:
        return ADMIN_MENU
    
    target_user_id_str = str(target_user_id)
    
    if action == "✅ Accept":
        USER_DATA[target_user_id_str]['access'] = 'GRANTED'
        STATS['accepted'] += 1
        STATS['total_handled'] += 1
        save_db()
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(get_message(target_user_id, 'btn_launch_app'),
                                 web_app=WebAppInfo(url=MINI_APP_URL))],
        ])
        await context.bot.send_message(target_user_id, "✅ Access Granted!", reply_markup=keyboard)
        await update.message.reply_text("✅ Application accepted.", reply_markup=get_admin_main_keyboard(admin_id))
        
    elif action == "❌ Reject":
        USER_DATA[target_user_id_str]['access'] = 'DENIED'
        STATS['denied'] += 1
        STATS['total_handled'] += 1
        save_db()
        
        await context.bot.send_message(target_user_id, "❌ Application rejected.")
        await update.message.reply_text("❌ Application rejected.", reply_markup=get_admin_main_keyboard(admin_id))
        
    elif action == "💬 Reject with comments":
        await update.message.reply_text(
            "Send rejection comment:",
            reply_markup=ReplyKeyboardRemove()
        )
        return PROCESS_REQUEST_COMMENT
    
    elif action == "↩️ Back":
        PENDING_QUEUE.appendleft(target_user_id)
        save_db()
        return ADMIN_MENU
    
    return ADMIN_MENU

@admin_only
async def process_request_comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle rejection comment."""
    admin_id = update.effective_user.id
    comment = update.message.text
    target_user_id = context.user_data.get('target_user_id')
    target_user_id_str = str(target_user_id)
    
    USER_DATA[target_user_id_str]['access'] = 'DENIED'
    STATS['corrected'] += 1
    STATS['total_handled'] += 1
    save_db()
    
    msg = f"❌ Application rejected.\nReason: {comment}"
    await context.bot.send_message(target_user_id, msg)
    await update.message.reply_text(
        "✅ Rejection sent.",
        reply_markup=get_admin_main_keyboard(admin_id)
    )
    
    return ADMIN_MENU

@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show statistics."""
    admin_id = update.effective_user.id
    
    text = (
        f"Accepted: {STATS['accepted']}\n"
        f"Denied: {STATS['denied']}\n"
        f"Corrected: {STATS['corrected']}\n"
        f"Total: {STATS['total_handled']}"
    )
    
    await update.message.reply_text(text, reply_markup=get_admin_main_keyboard(admin_id))
    return ADMIN_MENU

@admin_only
async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show bot status."""
    admin_id = update.effective_user.id
    await update.message.reply_text(STATS['bot_status'], reply_markup=get_admin_main_keyboard(admin_id))
    return ADMIN_MENU

@admin_only
async def admin_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show broadcast menu."""
    admin_id = update.effective_user.id
    await update.message.reply_text(
        "Choose broadcast type:",
        reply_markup=get_admin_broadcast_keyboard(admin_id)
    )
    return ADMIN_BROADCAST_MENU

@admin_only
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start broadcast process."""
    admin_id = update.effective_user.id
    action = update.message.text
    
    if action == "Send Now":
        context.user_data['broadcast_type'] = 'now'
        await update.message.reply_text("Send your message (text or photo):", reply_markup=ReplyKeyboardRemove())
        return BROADCAST_NOW_MSG
    
    elif action == "Send Later":
        context.user_data['broadcast_type'] = 'later'
        await update.message.reply_text("Send your message (text or photo):", reply_markup=ReplyKeyboardRemove())
        return BROADCAST_LATER_MSG
    
    elif action == "↩️ Admin Menu":
        return await admin_start_menu(update, context)
    
    return ADMIN_BROADCAST_MENU

async def save_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save broadcast content."""
    admin_id = update.effective_user.id
    
    if update.message.text:
        context.user_data['broadcast_text'] = update.message.text
    if update.message.photo:
        context.user_data['broadcast_photo_id'] = update.message.photo[-1].file_id
    
    if context.user_data.get('broadcast_type') == 'now':
        await update.message.reply_text(
            "Confirm broadcast?",
            reply_markup=get_confirm_keyboard(admin_id)
        )
        return BROADCAST_NOW_CONFIRM
    
    elif context.user_data.get('broadcast_type') == 'later':
        await update.message.reply_text(
            "Enter time (YYYY-MM-DD HH:MM):",
            reply_markup=ReplyKeyboardRemove()
        )
        return BROADCAST_LATER_TIME

@admin_only
async def broadcast_confirm_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm and send broadcast now."""
    admin_id = update.effective_user.id
    action = update.message.text
    
    if action == "✅ Confirm":
        text = context.user_data.get('broadcast_text')
        photo_id = context.user_data.get('broadcast_photo_id')
        
        # ✅ CORRIGIDO: excluir todos os admins
        user_ids = [uid for uid in USER_DATA if int(uid) not in ADMIN_IDS]
        
        success_count = 0
        for user_id_str in user_ids:
            try:
                if photo_id:
                    await context.bot.send_photo(int(user_id_str), photo_id, caption=text)
                else:
                    await context.bot.send_message(int(user_id_str), text)
                success_count += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.warning(f"Broadcast failed for {user_id_str}: {e}")
        
        await update.message.reply_text(
            f"✅ Broadcast sent to {success_count} users.",
            reply_markup=get_admin_main_keyboard(admin_id)
        )
        context.user_data.clear()
        return ADMIN_MENU
    
    elif action == "❌ Cancel":
        await update.message.reply_text("Cancelled.", reply_markup=get_admin_main_keyboard(admin_id))
        context.user_data.clear()
        return ADMIN_MENU
    
    return BROADCAST_NOW_CONFIRM

@admin_only
async def broadcast_set_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Set broadcast time."""
    admin_id = update.effective_user.id
    time_str = update.message.text
    
    try:
        scheduled_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        context.user_data['scheduled_time'] = scheduled_time
        
        await update.message.reply_text(
            f"Scheduled for {scheduled_time}. Confirm?",
            reply_markup=get_confirm_keyboard(admin_id)
        )
        return BROADCAST_LATER_CONFIRM
    except ValueError:
        await update.message.reply_text("Invalid format. Use: 2025-10-25 14:30")
        return BROADCAST_LATER_TIME

@admin_only
async def broadcast_confirm_later(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm scheduled broadcast."""
    admin_id = update.effective_user.id
    action = update.message.text
    
    if action == "✅ Confirm":
        scheduled_time = context.user_data['scheduled_time']
        
        context.job_queue.run_once(
            send_scheduled_broadcast,
            scheduled_time,
            data={
                'text': context.user_data.get('broadcast_text'),
                'photo_id': context.user_data.get('broadcast_photo_id'),
                'admin_id': admin_id,
                'context': context
            },
            name=f"broadcast_{scheduled_time.timestamp()}"
        )
        
        await update.message.reply_text(
            f"✅ Scheduled for {scheduled_time}.",
            reply_markup=get_admin_main_keyboard(admin_id)
        )
        context.user_data.clear()
        return ADMIN_MENU
    
    elif action == "❌ Cancel":
        await update.message.reply_text("Cancelled.", reply_markup=get_admin_main_keyboard(admin_id))
        context.user_data.clear()
        return ADMIN_MENU
    
    return BROADCAST_LATER_CONFIRM

async def send_scheduled_broadcast(context: ContextTypes.DEFAULT_TYPE):
    """Send scheduled broadcast."""
    data = context.job.data
    text = data.get('text')
    photo_id = data.get('photo_id')
    admin_id = data.get('admin_id')
    
    # ✅ CORRIGIDO: excluir todos os admins
    user_ids = [uid for uid in USER_DATA if int(uid) not in ADMIN_IDS]
    
    success_count = 0
    for user_id_str in user_ids:
        try:
            if photo_id:
                await context.bot.send_photo(int(user_id_str), photo_id, caption=text)
            else:
                await context.bot.send_message(int(user_id_str), text)
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Scheduled broadcast failed for {user_id_str}: {e}")
    
    await context.bot.send_message(
        admin_id,
        f"✅ Scheduled broadcast completed! Sent to {success_count}/{len(user_ids)} users."
    )

# --- MAIN APPLICATION ---

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler for users
    user_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("menu", go_to_main_menu)
        ],
        states={
            START_MENU: [
                CallbackQueryHandler(set_language, pattern='^set_lang_'),
            ],
            MAIN_MENU: [
                MessageHandler(filters.TEXT, lambda u, c: handle_instruction(u, c) if u.message.text and 'Instruction' in u.message.text or 'Инструкция' in u.message.text else None),
                MessageHandler(filters.Regex(r'(Instruction|Инструкция|Instrucciones|Instruções)'), handle_instruction),
                MessageHandler(filters.Regex(r'(Registration|Регистрация|Registro)'), handle_registration),
                MessageHandler(filters.Regex(r'(Get Bot Access|Получить доступ|Obtener Acceso|Obter Acesso)'), handle_get_access),
                MessageHandler(filters.Regex(r'(Get Promo Code|Получить Промокод|Código Promocional|Código Promocional)'), handle_get_promo_code),
                MessageHandler(filters.Regex(r'(Change Language|Изменить язык|Cambiar Idioma|Mudar Idioma)'), handle_change_lang),
                MessageHandler(filters.Regex(r'(Contact Support|Обратиться|Contactar|Contatar)'), handle_support),
                MessageHandler(filters.Regex(r'(Launch Program|Запустить|Iniciar|Lançar)'), handle_launch_app),
                MessageHandler(filters.Regex(r'(Back to Menu|Назад|Atrás|Voltar)'), admin_start_menu),
            ],
            AWAITING_ID: [
                MessageHandler(filters.TEXT | filters.PHOTO, handle_user_id_input),
            ],
            AWAITING_CHANNEL_CHECK: [
                CallbackQueryHandler(handle_check_subscription, pattern='^check_sub_now$'),
            ],
            ADMIN_MENU: [
                MessageHandler(filters.Regex(r'Applications'), admin_apps_menu),
                MessageHandler(filters.Regex(r'Bot Status'), admin_status),
                MessageHandler(filters.Regex(r'Statistics'), admin_stats),
                MessageHandler(filters.Regex(r'User Messages'), admin_broadcast_menu),
                MessageHandler(filters.Regex(r'Start Processing'), start_processing),
                MessageHandler(filters.Regex(r'Admin Menu'), admin_start_menu),
            ],
            PROCESSING_REQUESTS: [
                MessageHandler(filters.Regex(r'(Accept|Reject|comments|Back)'), process_request_action),
            ],
            PROCESS_REQUEST_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_request_comment_input),
            ],
            ADMIN_BROADCAST_MENU: [
                MessageHandler(filters.Regex(r'(Send Now|Send Later|Admin Menu)'), start_broadcast),
            ],
            BROADCAST_NOW_MSG: [
                MessageHandler(filters.ALL & ~filters.COMMAND, save_broadcast_content),
            ],
            BROADCAST_NOW_CONFIRM: [
                MessageHandler(filters.Regex(r'(Confirm|Cancel)'), broadcast_confirm_now),
            ],
            BROADCAST_LATER_MSG: [
                MessageHandler(filters.ALL & ~filters.COMMAND, save_broadcast_content),
            ],
            BROADCAST_LATER_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_set_time),
            ],
            BROADCAST_LATER_CONFIRM: [
                MessageHandler(filters.Regex(r'(Confirm|Cancel)'), broadcast_confirm_later),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    application.add_handler(user_conv_handler)
    
    logger.info("🤖 Bot started successfully. Polling for updates...")
    application.run_polling(poll_interval=1, allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
