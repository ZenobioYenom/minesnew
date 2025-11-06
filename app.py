import logging
import asyncio 
import re 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler, ContextTypes
from functools import wraps
from collections import deque
import random 
from datetime import datetime
from telegram.helpers import escape_markdown 
from telegram.error import BadRequest # ДОБАВЛЕНО: Для обработки ошибки Chat_admin_required

# Установка уровня логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- КОНСТАНТЫ И КОНФИГУРАЦИЯ ---
# !!! ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ ЭТИ ЗНАЧЕНИЯ !!!
TOKEN = "7692269177:AAGnz7egfTyoMwDY2y1px8Wmok-2W0BCecg"  # Замените на ваш токен
ADMIN_ID = [7428791161, 1993108159]  # Замените на ваш фактический ID администратора
SUPPORT_USERNAME = "@koalamoney3" 
PROMO_CODE = "MOB500RR"
REG_LINK = "https://1wbkpnt.com/?open=register&p=gv72"
CHANNEL_LINK = "https://t.me/+dWqBt5Ix380zNjI5"
CHANNEL_USERNAME = "@mgoldenmines" # Имя канала с @
MINI_APP_URL = "https://zenobioyenom.github.io/appmineswin/"

# ШАГ 1: ВРЕМЕННЫЙ РЕЖИМ ДЛЯ ПОЛУЧЕНИЯ FILE ID
GET_FILE_ID_MODE = True  

# ШАГ 2: ВСТАВЬТЕ РЕАЛЬНЫЕ FILE ID СЮДА
# Если File ID является заглушкой ('placeholder'), код автоматически переключится на отправку текста.
PHOTO_IDS = {
    'privet': 'AgACAgQJcn_photo_id_privet_placeholder',
    'menu': 'AgACAgQJcn_photo_id_menu_placeholder',
    'instr': 'AgACAgQJcn_photo_id_instr_placeholder',
    'id_example': 'AgACAgQJcn_photo_id_id_placeholder',
    'reg_RU': 'AgACAgQJcn_photo_id_regRU_placeholder',
    'reg_EN': 'AgACAgQJcn_photo_id_regEN_placeholder',
    'reg_ES': 'AgACAgQJcn_photo_id_regES_placeholder',
    'reg_PT': 'AgACAgQJcn_photo_id_regPT_placeholder',
    'test1': 'AgACAgQJcn_photo_id_test1_placeholder', 
}

# Если включен режим получения ID
if GET_FILE_ID_MODE:
    print("\n\n#####################################################")
    print("## РЕЖИМ ПОЛУЧЕНИЯ FILE ID АКТИВИРОВАН! ##")
    print("#####################################################\n\n")


# Состояния для ConversationHandler 
START_MENU, MAIN_MENU = range(2)
AWAITING_APPLICATION, AWAITING_ID, AWAITING_CHANNEL_CHECK = range(2, 5)
ADMIN_MENU, ADMIN_BROADCAST_MENU = range(5, 7)
BROADCAST_NOW_MSG, BROADCAST_NOW_CONFIRM = range(7, 9)
BROADCAST_LATER_MSG, BROADCAST_LATER_TIME, BROADCAST_LATER_CONFIRM = range(9, 12)
PROCESSING_REQUESTS, PROCESS_REQUEST_COMMENT = range(12, 14)

# Имитация базы данных 
USER_DATA = {}
PENDING_QUEUE = deque([])
STATS = {
    'accepted': 0,
    'denied': 0,
    'corrected': 0,
    'total_handled': 0,
    'bot_status': '✅ Operating normally'
}

# --- ЛОКАЛИЗАЦИЯ (Обновлена) ---

# 1. Определяем базовый набор сообщений на английском (ИСПОЛЬЗУЕТСЯ АДМИНОМ)
base_english_messages = {
    # General & Core
    'admin_id': ADMIN_ID,
    'start_user': "🌐 Select your language / Elige tu idioma / Escolha o idioma 🌐",
    'start_admin': "Hi, Admin!\nI’ve recognized your ID — good to see you again! 🤖",
    'language_set': "Language set to English.",
    'admin_access_denied': "Access denied. You are not an administrator.",
    'language_select_prompt': "🌐 Select your language / Elige tu idioma / Escolha o idioma 🌐",
    'photo_placeholder': "[Image placeholder]", 
    'support_link_text': "Click the button below to contact support: {username}",

    # User Menu Buttons (ДОБАВЛЕНЫ ЭМОДЗИ)
    'btn_instruction': "📖 Instruction",
    'btn_registration': "🔗 Registration",
    'btn_get_access': "🔑 Get Bot Access",
    'btn_change_lang': "🌍 Change Language",
    'btn_support': "💬 Contact Support",
    'btn_launch_app': "▶️ Launch Program",
    'btn_menu_back': "↩️ Back to Menu",
    'btn_get_promo': "💰 Get Promo Code",
    'btn_check_sub': "✅ Check Subscription",

    # User Menu Content
    'menu_access_closed': "Access to the program: 🔴 Closed",
    'menu_access_granted': "Access to the program: 🟢 Granted",
    'menu_telegram_id': "Your Telegram ID: {id}",
    'menu_game_id_none': "Your Game ID: Not set",
    'menu_game_id_set': "Your Game ID: {game_id}",
    'menu_pending': "Your application is pending review. Please wait.",
    'access_denied_perm': "Access was denied by the administrator. Status: ❌ Denied",
    'access_granted_msg': "Congratulations! Access has been granted. You can now use the 'Launch Program' button.",
    'access_rejected_msg': "Access was denied. If you think this is an error, please check the instructions and try again.",
    'access_rejected_with_comment_msg': "Access was denied. Reason: {comment}\nPlease check the instructions and resend your application.",
    'launch_denied': "❌ Access denied. Please submit or wait for approval of your application.",
    'awaiting_id_prompt': "Please send your account ID or a screenshot showing the ID. (Photo 'ID' attached)",
    'application_received': "Information accepted. The verification and connection process has been launched. You will be sent access immediately after completion.",
    'reg_button_text': "Registration Link",
    
    # Promo Flow Messages
    'promo_check_prompt': "To receive the promo code, you must subscribe to our channel: {link}",
    'promo_not_subscribed': "You are not yet subscribed. Please subscribe and press the 'Check Subscription' button.",
    'promo_subscribed_success': "Subscription verified! Your exclusive promo code is: `{promo}`. Use it during registration.",
    'promo_code_already_sent': "You already have the promo code: `{promo}`. Use it for registration.",
    'promo_channel_error': "⚠️ I cannot verify your subscription. Please ensure the bot is an **administrator** in the channel: `{channel}` with permission to **view members**.",
    'promo_needed_note': "Please get your promo code first by clicking '💰 Get Promo Code' in the main menu.", # <-- НОВОЕ СООБЩЕНИЕ
    
    # Instruction Text
    'instr_text': (
        "INSTRUCTIONS FOR GETTING STARTED\n"
        "For correct connection, follow these steps:\n"
        "1) Get the exclusive promo code by pressing the '💰 Get Promo Code' button.\n"
        "2) Register using the exclusive link: {link}.\n"
        "When registering, be sure to use the promo code you received.\n"
        "(This will speed up the identification of your account and connection to the session.)\n"
        "3) Click the '🔑 Get Bot Access' button in our chat.\n"
        "4) Send the bot your registration ID (account number on 1win).\n"
        "(The ID is needed to match your active session with the server data, ensuring accurate forecasts.)\n"
        "5) Wait for the connection. As soon as the bot is connected, you will be granted access."
    ),

    # Admin Messages (REMAINS EN)
    'btn_admin_apps': "🧾 Applications ({count})",
    'btn_admin_status': "🤖 Bot Status",
    'btn_admin_stats': "📊 Statistics",
    'btn_admin_broadcast': "💬 User Messages",
    'btn_start_processing': "🚀 Start processing",
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
    'prompt_reject_comment': "Please send the rejection comment you want to send to the user.",
    'comment_sent': "Application REJECTED with comment. User notified.",
    'stats_text': "Statistics:\nAccepted users: {a}\nUsers denied access: {d}\nRequests sent for correction: {c}\nTotal requests handled: {t}",
    'bot_status_text': "Current bot status: {status}",
    'status_normal': "✅ Operating normally",
    'status_error': "❌ Bot is not working",
    'status_warning': "⚠️ There were errors",
    'prompt_broadcast_msg': "Please send the message (text and/or photo) you want to broadcast.",
    'confirm_broadcast_now': "CONFIRM: This message will be sent to all users NOW.",
    'broadcast_success': "Broadcast sent successfully to all active users.",
    'prompt_broadcast_time': "Please specify the time and date (e.g., 2025-10-25 14:30) for the scheduled broadcast.",
    'confirm_broadcast_later': "CONFIRM: This message is scheduled for {time} UTC.",
    'broadcast_scheduled': "Broadcast successfully scheduled for {time}.",
    'broadcast_cancelled': "Broadcast sending cancelled. Returning to Admin Menu.",
}

# 2. Определяем переопределения для русского языка
russian_overrides = {
    'language_set': "Язык установлен на Русский.",
    'photo_placeholder': "[Здесь должна быть картинка]", 
    'btn_instruction': "📖 Инструкция",
    'btn_registration': "🔗 Регистрация",
    'btn_get_access': "🔑 Получить доступ к боту",
    'btn_change_lang': "🌍 Изменить язык",
    'btn_support': "💬 Обратиться в поддержку",
    'btn_launch_app': "▶️ Запустить программу",
    'btn_menu_back': "↩️ Назад в меню",
    'btn_get_promo': "💰 Получить Промокод",
    'btn_check_sub': "✅ Проверить Подписку",
    'support_link_text': "Нажмите кнопку ниже, чтобы связаться со службой поддержки: {username}",

    # Promo Flow Messages 
    'promo_not_subscribed': "Вы еще не подписаны. Пожалуйста, подпишитесь и нажмите кнопку '✅ Проверить Подписку'.",
    'promo_channel_error': "⚠️ Не удалось проверить подписку. Убедитесь, что бот является **администратором** в канале: `{channel}` с правом **просмотра участников**.",
    'promo_needed_note': "Пожалуйста, получите ваш промокод, нажав на '💰 Получить Промокод' в главном меню.", # <-- НОВОЕ СООБЩЕНИЕ
    
    # Instruction Text
    'instr_text': (
        "ИНСТРУКЦИЯ ПО НАЧАЛУ РАБОТЫ\n"
        "Для корректного подключения бота выполните следующие шаги:\n"
        "1) Получите эксклюзивный промокод, нажав кнопку '💰 Получить Промокод'.\n"
        "2) Зарегистрируйтесь по эксклюзивной ссылке: {link}.\n"
        "При регистрации обязательно укажите полученный промокод.\n"
        "(Это ускорит идентификацию вашего аккаунта и подключение к сессии.)\n"
        "3) Нажмите на кнопку «🔑 Получить доступ к боту» в нашем чате.\n"
        "4) Отправьте боту ваш регистрационный ID (номер счета на 1win).\n"
        "(ID нужен для сверки вашей активной сессии с данными на сервере, что обеспечивает точность прогнозов.)\n"
        "5) Ожидайте подключения. Как только бот будет подключен, вам будет выдан доступ."
    ),
}

# 3. Определяем переопределения для испанского (ES)
spanish_overrides = {
    'language_set': "Idioma establecido a Español.", 
    'photo_placeholder': "[Marcador de posición de imagen]", 
    'btn_instruction': "📖 Instrucciones", 
    'btn_registration': "🔗 Registro", 
    'btn_get_access': "🔑 Obtener Acceso al Bot", 
    'btn_change_lang': "🌍 Cambiar Idioma", 
    'btn_support': "💬 Contactar Soporte", 
    'btn_launch_app': "▶️ Iniciar Programa", 
    'btn_menu_back': "↩️ Volver al Menú",
    'btn_get_promo': "💰 Obtener Código Promocional",
    'btn_check_sub': "✅ Verificar Suscripción",
    'support_link_text': "Haga clic en el botón de abajo para contactar a soporte: {username}",
    'promo_needed_note': "Por favor, obtenga su código promocional haciendo clic en '💰 Obtener Código Promocional' en el menú principal.",
    
    # Instruction Text
    'instr_text': (
        "INSTRUCCIONES PARA EMPEZAR\n"
        "Para una conexión correcta, siga estos pasos:\n"
        "1) Obtenga el código promocional exclusivo pulsando el botón '💰 Obtener Código Promocional'.\n"
        "2) Regístrese utilizando el enlace exclusivo: {link}.\n"
        "Al registrarse, asegúrese de usar el código promocional que recibió.\n"
        "(Esto acelerará la identificación de su cuenta y la conexión a la sesión.)\n"
        "3) Haga clic en el botón '🔑 Obtener Acceso al Bot' en nuestro chat.\n"
        "4) Envíe al bot su ID de registro (número de cuenta en 1win).\n"
        "(El ID es necesario para cotejar su sesión activa con los datos del servidor, asegurando pronósticos precisos.)\n"
        "5) Espere la conexión. Tan pronto como el bot esté conectado, se le concederá el acceso."
    ),
}

# 4. Определяем переопределения для португальского (PT)
portuguese_overrides = {
    'language_set': "Idioma definido para Português.", 
    'photo_placeholder': "[Espaço reservado para imagem]", 
    'btn_instruction': "📖 Instruções", 
    'btn_registration': "🔗 Registro", 
    'btn_get_access': "🔑 Obter Acesso ao Bot", 
    'btn_change_lang': "🌍 Mudar Idioma", 
    'btn_support': "💬 Contatar Suporte", 
    'btn_launch_app': "▶️ Lançar Programa", 
    'btn_menu_back': "↩️ Voltar ao Menu",
    'btn_get_promo': "💰 Obter Código Promocional",
    'btn_check_sub': "✅ Verificar Assinatura",
    'support_link_text': "Clique no botão abaixo para entrar em contato com o suporte: {username}",
    'promo_needed_note': "Por favor, obtenha seu código promocional clicando em '💰 Obter Código Promocional' no menu principal.",

    # Instruction Text
    'instr_text': (
        "INSTRUÇÕES PARA COMEÇAR\n"
        "Para a conexão correta, siga estas etapas:\n"
        "1) Obtenha o código promocional exclusivo pressionando o botão '💰 Obter Código Promocional'.\n"
        "2) Registre-se usando o link exclusivo: {link}.\n"
        "Ao se registrar, certifique-se de usar o código promocional que você recebeu.\n"
        "(Isso acelerará a identificação de sua conta e a conexão com a sessão.)\n"
        "3) Clique no botão '🔑 Obter Acesso ao Bot' em nosso chat.\n"
        "4) Envie ao bot sua ID de registro (número da conta no 1win).\n"
        "(O ID é necessário para verificar sua sessão ativa com os dados do servidor, garantindo previsões precisas.)\n"
        "5) Aguarde a conexão. Assim que o bot estiver conectado, o acesso será concedido."
    ),
}

# 5. Собираем финальный словарь MESSAGES
MESSAGES = {
    'EN': base_english_messages,
    'RU': {**base_english_messages, **russian_overrides},
    'ES': {**base_english_messages, **spanish_overrides},
    'PT': {**base_english_messages, **portuguese_overrides},
}

# --- УТИЛИТАРНЫЕ ФУНКЦИИ ---

def get_message(user_id, key):
    """Получает сообщение на языке пользователя. Использует 'RU' как запасной вариант для пользователей."""
    if user_id == ADMIN_ID:
        lang = 'EN'
    else:
        lang = USER_DATA.get(user_id, {}).get('lang', 'RU') 
        
    if lang in MESSAGES and key in MESSAGES[lang]:
        return MESSAGES[lang][key]
    return MESSAGES['EN'].get(key, f"MISSING_KEY:{key}")

def get_photo_id(key):
    """Получает File ID фотографии. Возвращает None, если это заглушка."""
    file_id = PHOTO_IDS.get(key, None)
    if not file_id or (not GET_FILE_ID_MODE and 'placeholder' in file_id):
        return None
    return file_id

# Декоратор admin_only остается без изменений

def admin_only(func):
    """Декоратор для ограничения доступа к функциям только для админа."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id == ADMIN_ID:
            return await func(update, context, *args, **kwargs)
        else:
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(get_message(user_id, 'admin_access_denied'))
            elif update.message:
                await update.message.reply_text(get_message(user_id, 'admin_access_denied'))
            return MAIN_MENU
    return wrapper

def get_user_status(user_id):
    """Возвращает статус пользователя: PENDING, GRANTED, DENIED или NONE."""
    return USER_DATA.get(user_id, {}).get('access', 'NONE')

def get_user_game_id(user_id):
    """Возвращает игровой ID пользователя или None."""
    return USER_DATA.get(user_id, {}).get('game_id', None)

def has_promo_code(user_id):
    """Проверяет, был ли пользователю выдан промокод."""
    return USER_DATA.get(user_id, {}).get('has_promo', False)

# --- ФУНКЦИИ КЛАВИАТУР ---

def get_lang_keyboard():
    """Клавиатура для выбора языка (только EN, ES, PT)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("English", callback_data='set_lang_EN')],
        [InlineKeyboardButton("Español", callback_data='set_lang_ES')],
        [InlineKeyboardButton("Português", callback_data='set_lang_PT')],
    ])

def get_main_menu_keyboard(user_id):
    """Основная клавиатура пользователя."""
    
    # 1. Первая строка: Инструкция, Регистрация
    row1 = [KeyboardButton(get_message(user_id, 'btn_instruction')), KeyboardButton(get_message(user_id, 'btn_registration'))]
    
    # 2. Вторая строка: Основное действие (Получить Промокод ИЛИ Получить Доступ)
    if not has_promo_code(user_id):
        # Если промокод не получен, предлагаем получить его
        row2 = [KeyboardButton(get_message(user_id, 'btn_get_promo')), KeyboardButton(get_message(user_id, 'btn_change_lang'))]
    else:
        # Если промокод получен, предлагаем подать заявку
        row2 = [KeyboardButton(get_message(user_id, 'btn_get_access')), KeyboardButton(get_message(user_id, 'btn_change_lang'))]
        
    # 3. Третья строка: Поддержка, Запуск
    row3 = [KeyboardButton(get_message(user_id, 'btn_support')), KeyboardButton(get_message(user_id, 'btn_launch_app'))]
    
    buttons = [row1, row2, row3]

    # Добавляем кнопки админа, если это админ
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(get_message(user_id, 'btn_menu_back'))])
        
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# Административные клавиатуры остаются без изменений
def get_admin_main_keyboard(admin_id):
    """Главная клавиатура админа."""
    count = len(PENDING_QUEUE)
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_admin_apps').format(count=count))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_status')), KeyboardButton(get_message(admin_id, 'btn_admin_stats'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_broadcast'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_back'))], 
    ], resize_keyboard=True)

def get_admin_processing_keyboard(admin_id):
    """Клавиатура для обработки заявки."""
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_accept'))],
        [KeyboardButton(get_message(admin_id, 'btn_reject')), KeyboardButton(get_message(admin_id, 'btn_reject_comment'))],
        [KeyboardButton(get_message(admin_id, 'btn_menu_back'))],
    ], resize_keyboard=True)

def get_admin_apps_menu(admin_id):
    """Клавиатура после показа количества заявок."""
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_start_processing'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_back'))],
    ], resize_keyboard=True)

def get_admin_broadcast_keyboard(admin_id):
    """Клавиатура для выбора типа рассылки."""
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_broadcast_now')), KeyboardButton(get_message(admin_id, 'btn_broadcast_later'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_back'))],
    ], resize_keyboard=True)

def get_confirm_keyboard(admin_id):
    """Клавиатура подтверждения/отмены."""
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_confirm')), KeyboardButton(get_message(admin_id, 'btn_cancel'))],
    ], resize_keyboard=True)

# --- НОВЫЙ ХЕНДЛЕР: ВРЕМЕННЫЙ ДЛЯ ПОЛУЧЕНИЯ FILE ID ---
async def get_file_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Временный хендлер для получения file ID загруженных фотографий/документов."""
    if update.message.photo:
        # Берем самый большой размер фотографии
        file_id = update.message.photo[-1].file_id
        await update.message.reply_text(
            f"✅ PHOTO FILE ID: `{file_id}`\n\n**Скопируйте этот ID** и вставьте его в словарь PHOTO_IDS, затем установите `GET_FILE_ID_MODE = False`.", 
            parse_mode='Markdown'
        )
        logger.info(f"PHOTO FILE ID: {file_id}")
    elif update.message.document:
        file_id = update.message.document.file_id
        await update.message.reply_text(
            f"✅ DOCUMENT FILE ID: `{file_id}`\n\n**Скопируйте этот ID** и вставьте его в словарь PHOTO_IDS, затем установите `GET_FILE_ID_MODE = False`.", 
            parse_mode='Markdown'
        )
        logger.info(f"DOCUMENT FILE ID: {file_id}")
    else:
        await update.message.reply_text("Пожалуйста, отправьте фотографию или документ, чтобы получить его ID.")


# --- ХЕНДЛЕРЫ: СТАРТ И ЯЗЫК ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает команду /start и направляет админа/пользователя."""
    user_id = update.effective_user.id
    
    if user_id not in USER_DATA:
        # Устанавливаем язык по умолчанию для пользователя (например, RU)
        lang_code = update.effective_user.language_code
        USER_DATA[user_id] = {'lang': lang_code.upper() if lang_code and lang_code.upper() in MESSAGES else 'RU', 
                              'access': 'NONE', 'game_id': None, 'application_info': None, 'has_promo': False}
    
    if user_id == ADMIN_ID:
        # Для админа сразу ставим EN для сообщений
        USER_DATA[user_id]['lang'] = 'EN'
        await update.message.reply_text(
            get_message(user_id, 'start_admin'),
            reply_markup=get_admin_main_keyboard(user_id)
        )
        return ADMIN_MENU
    else:
        photo_id = get_photo_id('privet')
        caption = get_message(user_id, 'start_user')
        
        if photo_id:
            await update.message.reply_photo(
                photo=photo_id, 
                caption=caption,
                reply_markup=get_lang_keyboard()
            )
        else:
             # Fallback to text + placeholder note
             caption += f"\n\n{get_message(user_id, 'photo_placeholder')}"
             await update.message.reply_text(
                caption,
                reply_markup=get_lang_keyboard()
            )
        return START_MENU

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Устанавливает язык для пользователя."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = query.data.split('_')[2]
    
    USER_DATA[user_id]['lang'] = lang_code
    logger.info(f"User {user_id} set language to {lang_code}")

    await query.message.delete()
    
    await show_user_main_menu(update, context) # Передаем полный объект update
    return MAIN_MENU

async def go_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Общий хендлер для возврата в главное меню."""
    user_id = update.effective_user.id
    # Проверяем, если админ нажал на кнопку "Назад в меню админа", то показываем админское меню.
    if user_id == ADMIN_ID and update.message.text == get_message(user_id, 'btn_admin_back'):
        return await admin_start_menu(update, context)
    
    await show_user_main_menu(update, context)
    return MAIN_MENU

# --- ХЕНДЛЕРЫ: ПОЛЬЗОВАТЕЛЬСКОЕ МЕНЮ ---

async def show_user_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает главное меню пользователю с его статусом.
    Универсальная функция, которая может быть вызвана из Message, CallbackQuery или напрямую.
    """
    user_id = None
    
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        source_message = update.callback_query.message
    elif update.message:
        user_id = update.message.from_user.id
        source_message = update.message
    # Это для случая, когда вызывается из другого места, где update.effective_user доступен
    elif hasattr(update, 'effective_user'):
        user_id = update.effective_user.id
        source_message = update.effective_message
    
    if user_id is None:
        logger.error("Could not determine user ID in show_user_main_menu.")
        return

    status = get_user_status(user_id)
    game_id = get_user_game_id(user_id)
    
    if status == 'GRANTED':
        status_line = get_message(user_id, 'menu_access_granted')
    elif status == 'DENIED':
        status_line = get_message(user_id, 'access_denied_perm')
    elif status == 'PENDING':
        status_line = get_message(user_id, 'menu_pending')
    else:
        status_line = get_message(user_id, 'menu_access_closed')
        
    game_id_line = get_message(user_id, 'menu_game_id_none')
    if game_id:
        game_id_line = get_message(user_id, 'menu_game_id_set').format(game_id=game_id)
        
    text = (
        f"{status_line}\n\n"
        f"{get_message(user_id, 'menu_telegram_id').format(id=user_id)}\n"
        f"{game_id_line}"
    )
    
    photo_id = get_photo_id('menu')

    # Пытаемся удалить/отредактировать предыдущее сообщение (если это callback)
    if update.callback_query and source_message:
        try:
             await source_message.delete()
        except:
             # Если не удалось удалить, просто отправляем новое
             pass
    
    # Отправка фото или текста
    if photo_id:
        await context.bot.send_photo(
            chat_id=user_id,
            photo=photo_id, 
            caption=text,
            reply_markup=get_main_menu_keyboard(user_id)
        )
    else:
        # Fallback на текст + заглушка
        text += f"\n\n{get_message(user_id, 'photo_placeholder')}"
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=get_main_menu_keyboard(user_id))


async def handle_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает кнопку 'Инструкция'."""
    user_id = update.effective_user.id
    # Инструкция теперь несет промокод, но он форматируется только в тексте.
    text = get_message(user_id, 'instr_text').format(link=REG_LINK) 
    photo_id = get_photo_id('instr')
    
    if photo_id:
        await update.message.reply_photo(
            photo=photo_id, 
            caption=text,
            reply_markup=get_main_menu_keyboard(user_id)
        )
    else:
         text += f"\n\n{get_message(user_id, 'photo_placeholder')}"
         await update.message.reply_text(text, reply_markup=get_main_menu_keyboard(user_id))

    return MAIN_MENU

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает кнопку 'Регистрация'."""
    user_id = update.effective_user.id
    lang = USER_DATA.get(user_id, {}).get('lang', 'RU')
    
    photo_id_key = f'reg_{lang}'
    photo_id = get_photo_id(photo_id_key)
    
    # --- ИСПРАВЛЕНИЕ: ПРОМОКОД ТОЛЬКО ПОСЛЕ ПОЛУЧЕНИЯ ---
    if has_promo_code(user_id):
        promo_note = f"Ваш промокод: `{PROMO_CODE}`." 
    else:
        promo_note = get_message(user_id, 'promo_needed_note')
    
    text = f"Register using the exclusive link: {REG_LINK}\n{promo_note}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_message(user_id, 'reg_button_text'), url=REG_LINK)],
    ])
    
    if photo_id:
        await update.message.reply_photo(
            photo=photo_id, 
            caption=text,
            reply_markup=keyboard
        )
    else:
        text += f"\n\n{get_message(user_id, 'photo_placeholder')}"
        await update.message.reply_text(text, reply_markup=keyboard)

    return MAIN_MENU
    
# --- ХЕНДЛЕРЫ ДЛЯ ПРОМОКОДА И ПРОВЕРКИ ПОДПИСКИ ---

async def handle_get_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса получения промокода - отправка ссылки на канал."""
    user_id = update.effective_user.id

    if has_promo_code(user_id):
        text = get_message(user_id, 'promo_code_already_sent').format(promo=PROMO_CODE)
        await update.message.reply_text(text, reply_markup=get_main_menu_keyboard(user_id), parse_mode='Markdown')
        return MAIN_MENU
        
    text = get_message(user_id, 'promo_check_prompt').format(link=CHANNEL_LINK)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Telegram Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton(get_message(user_id, 'btn_check_sub'), callback_data='check_sub_now')],
    ])
    
    await update.message.reply_text(text, reply_markup=keyboard)
    
    # Переходим в состояние ожидания проверки подписки
    return AWAITING_CHANNEL_CHECK

async def handle_check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Проверяет подписку пользователя на канал."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if has_promo_code(user_id):
        # Если промокод уже есть, просто возвращаемся в меню
        await show_user_main_menu(update, context)
        return MAIN_MENU

    try:
        # Проверяем статус пользователя в канале
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        # is_chat_member() возвращает true для 'member', 'creator', 'administrator'. 
        # get_chat_member() возвращает объект ChatMember, у которого статус - не 'left' и не 'kicked'
        if member.status not in ['left', 'kicked', 'banned']:
            # Подписка подтверждена
            USER_DATA[user_id]['has_promo'] = True
            
            # Отправляем промокод и возвращаемся в главное меню (клавиатура обновится)
            text = get_message(user_id, 'promo_subscribed_success').format(promo=PROMO_CODE)
            await query.message.edit_text(text, parse_mode='Markdown')
            
            # ИСПРАВЛЕНИЕ: Передаем полный update, чтобы show_user_main_menu корректно определила ID и тип обновления
            await show_user_main_menu(update, context) 
            return MAIN_MENU
        else:
            # Подписки нет
            text = get_message(user_id, 'promo_not_subscribed')
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Telegram Channel", url=CHANNEL_LINK)],
                [InlineKeyboardButton(get_message(user_id, 'btn_check_sub'), callback_data='check_sub_now')],
            ])
            await query.message.edit_text(text, reply_markup=keyboard)
            return AWAITING_CHANNEL_CHECK
            
    except BadRequest as e:
        logger.error(f"Error checking subscription for {user_id}: {e}")
        # Ошибка, если бот не админ или канал не найден
        error_text = get_message(user_id, 'promo_channel_error').format(channel=CHANNEL_USERNAME)
        await query.message.reply_text(error_text, parse_mode='Markdown')
        
        # Возвращаемся в главное меню, чтобы пользователь мог продолжить
        await show_user_main_menu(update, context) 
        return MAIN_MENU
    except Exception as e:
        logger.error(f"An unexpected error occurred during subscription check for {user_id}: {e}")
        await query.message.reply_text("An unexpected error occurred. Please try again later.")
        
        # Возвращаемся в главное меню
        await show_user_main_menu(update, context)
        return MAIN_MENU

async def handle_get_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс подачи заявки (получения ID)."""
    user_id = update.effective_user.id
    status = get_user_status(user_id)
    
    # 1. Проверка, есть ли промокод
    if not has_promo_code(user_id):
        await update.message.reply_text(get_message(user_id, 'promo_needed_note'))
        return MAIN_MENU
        
    # 2. Если уже одобрен, показываем сообщение с кнопкой Mini App
    if status == 'GRANTED':
        from telegram import WebAppInfo  # <- adiciona suporte ao botão web_app

        keyboard = [
            [
                InlineKeyboardButton("📲 Abrir aplicativo", web_app=WebAppInfo(url=MINI_APP_URL))
            ],
            [
                InlineKeyboardButton("🆘 Suporte", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            get_message(user_id, 'access_granted_msg'),
            reply_markup=reply_markup
        )

        return MAIN_MENU
        
    # 3. Если уже в ожидании, сообщаем
    if status == 'PENDING':
        await update.message.reply_text(get_message(user_id, 'menu_pending'))
        return MAIN_MENU
    
    # 4. Начинаем процесс подачи ID
    USER_DATA[user_id]['application_info'] = {'text': None, 'photo_id': None, 'timestamp': None}
    
    text = get_message(user_id, 'awaiting_id_prompt')
    photo_id = get_photo_id('id_example')
    
    if photo_id:
        await update.message.reply_photo(
            photo=photo_id, 
            caption=text
        )
    else:
        text += f"\n\n{get_message(user_id, 'photo_placeholder')}"
        await update.message.reply_text(text)
        
    return AWAITING_ID

async def handle_user_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод ID или скриншота."""
    user_id = update.effective_user.id
    application_info = USER_DATA[user_id].get('application_info')

    if update.message.text:
        # Это текст (ID)
        game_id = update.message.text.strip()
        # Простая проверка, что ID похож на номер
        if not re.match(r'^\d{4,}$', game_id):
            await update.message.reply_text(
                get_message(user_id, 'awaiting_id_prompt')
            )
            return AWAITING_ID

        application_info['text'] = game_id
        application_info['game_id'] = game_id  # Сохраняем ID в application_info
        USER_DATA[user_id]['game_id'] = game_id # Обновляем основной game_id
        
    elif update.message.photo:
        # Это фото (скриншот)
        photo_id = update.message.photo[-1].file_id # Берем самое большое фото
        application_info['photo_id'] = photo_id
        
        # Если фото пришло без текста, просим ввести ID текстом
        if not application_info.get('text'):
            await update.message.reply_text("Спасибо за скриншот. Теперь, пожалуйста, **введите ваш ID счета** текстом, чтобы мы могли его скопировать и обработать.")
            return AWAITING_ID
        
    else:
        # Неподдерживаемый тип сообщения
        await update.message.reply_text(
            get_message(user_id, 'awaiting_id_prompt')
        )
        return AWAITING_ID

    # Если мы здесь, значит, у нас есть либо ID (текст), либо фото + ID (текст)
    if application_info.get('game_id') or application_info.get('text'):
        # Финальная обработка заявки
        USER_DATA[user_id]['access'] = 'PENDING'
        application_info['timestamp'] = datetime.now()
        
        # Добавляем в очередь
        PENDING_QUEUE.append(user_id)
        
        # Отправляем подтверждение пользователю
        await update.message.reply_text(
            get_message(user_id, 'application_received')
        )
        
        # Уведомляем администратора о новой заявке
        await context.bot.send_message(
            ADMIN_ID, 
            f"🔔 НОВАЯ ЗАЯВКА (PENDING) от User ID: {user_id}. Очередь: {len(PENDING_QUEUE)}"
        )
        
        return MAIN_MENU
    else:
        # Если не было текста, но было фото, мы уже попросили текст выше.
        # Если не было ни того, ни другого, это не должно случиться, но на всякий случай
        await update.message.reply_text(
            get_message(user_id, 'awaiting_id_prompt')
        )
        return AWAITING_ID

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает кнопку 'Обратиться в поддержку'."""
    user_id = update.effective_user.id
    text = get_message(user_id, 'support_link_text').format(username=SUPPORT_USERNAME)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Support", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
    ])
    
    await update.message.reply_text(text, reply_markup=keyboard)
    return MAIN_MENU

async def handle_launch_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает кнопку 'Запустить программу'."""
    user_id = update.effective_user.id
    status = get_user_status(user_id)
    
    if status == 'GRANTED':
        # Здесь будет реальный код запуска программы
        await update.message.reply_text(f"✅ Программа запущена для {get_user_game_id(user_id)}!")
    else:
        await update.message.reply_text(get_message(user_id, 'launch_denied'))
        
    return MAIN_MENU

async def handle_change_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает кнопку 'Изменить язык'."""
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        get_message(user_id, 'language_select_prompt'),
        reply_markup=get_lang_keyboard()
    )
    # Переходим в состояние START_MENU для выбора языка через callback
    return START_MENU 


# --- ХЕНДЛЕРЫ: АДМИН ПАНЕЛЬ ---

@admin_only
async def admin_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает главное меню админа."""
    admin_id = update.effective_user.id
    await update.message.reply_text(
        "Welcome to Admin Panel.",
        reply_markup=get_admin_main_keyboard(admin_id)
    )
    return ADMIN_MENU

@admin_only
async def admin_apps_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает количество ожидающих заявок и предлагает начать обработку."""
    admin_id = update.effective_user.id
    count = len(PENDING_QUEUE)
    
    text = get_message(admin_id, 'apps_pending_count').format(count=count)
    
    if count > 0:
        await update.message.reply_text(
            text,
            reply_markup=get_admin_apps_menu(admin_id)
        )
        return ADMIN_MENU
    else:
        await update.message.reply_text(
            text + "\n(No pending requests.)",
            reply_markup=get_admin_main_keyboard(admin_id)
        )
        return ADMIN_MENU

@admin_only
async def start_processing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает обработку следующей заявки из очереди."""
    admin_id = update.effective_user.id
    
    if not PENDING_QUEUE:
        await update.message.reply_text("The application queue is empty.", reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU
    
    # Извлекаем ID следующего пользователя
    target_user_id = PENDING_QUEUE.popleft()
    context.user_data['target_user_id'] = target_user_id
    
    user_data = USER_DATA.get(target_user_id, {})
    app_info = user_data.get('application_info', {})
    
    # Формируем сообщение
    info_text = get_message(admin_id, 'app_processing_info').format(
        id=target_user_id,
        game_id=user_data.get('game_id', 'N/A')
    )
    
    message_parts = [info_text]
    
    if app_info.get('text'):
        message_parts.append(get_message(admin_id, 'app_processing_text').format(text=app_info['text']))
        
    if app_info.get('photo_id'):
        message_parts.append(get_message(admin_id, 'app_processing_photo'))
        
    final_text = "\n".join(message_parts)

    # Отправка фото, если есть
    if app_info.get('photo_id'):
        await update.message.reply_photo(
            photo=app_info['photo_id'],
            caption=final_text,
            reply_markup=get_admin_processing_keyboard(admin_id)
        )
    else:
        await update.message.reply_text(
            final_text,
            reply_markup=get_admin_processing_keyboard(admin_id)
        )
        
    return PROCESSING_REQUESTS

@admin_only
async def process_request_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает действия: Принять, Отклонить, Отклонить с комментарием."""
    admin_id = update.effective_user.id
    action = update.message.text
    target_user_id = context.user_data.get('target_user_id')
    
    if not target_user_id or target_user_id not in USER_DATA:
        await update.message.reply_text("Error: No user ID found for processing.", reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU

    # Принять
    if action == get_message(admin_id, 'btn_accept'):
        USER_DATA[target_user_id]['access'] = 'GRANTED'
        STATS['accepted'] += 1
        STATS['total_handled'] += 1
        
        await context.bot.send_message(target_user_id, get_message(target_user_id, 'access_granted_msg'))
        await update.message.reply_text(get_message(admin_id, 'app_accepted'), reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU

    # Отклонить с комментарием
    elif action == get_message(admin_id, 'btn_reject_comment'):
        await update.message.reply_text(get_message(admin_id, 'prompt_reject_comment'), reply_markup=ReplyKeyboardRemove())
        return PROCESS_REQUEST_COMMENT

    # Отклонить (без комментария)
    elif action == get_message(admin_id, 'btn_reject'):
        USER_DATA[target_user_id]['access'] = 'DENIED'
        STATS['denied'] += 1
        STATS['total_handled'] += 1
        
        await context.bot.send_message(target_user_id, get_message(target_user_id, 'access_rejected_msg'))
        await update.message.reply_text(get_message(admin_id, 'app_rejected'), reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU
        
    # Назад в меню
    elif action == get_message(admin_id, 'btn_menu_back'):
        # Возвращаем заявку в очередь
        PENDING_QUEUE.appendleft(target_user_id) 
        del context.user_data['target_user_id']
        await update.message.reply_text("Request deferred. Returning to Admin Menu.", reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU

    return PROCESSING_REQUESTS # Остаемся в состоянии, если не распознано

@admin_only
async def process_request_comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод комментария для отклонения."""
    admin_id = update.effective_user.id
    comment = update.message.text
    target_user_id = context.user_data.get('target_user_id')
    
    if not target_user_id:
        await update.message.reply_text("Error: No user ID found for processing.", reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU

    # Обновляем статус и статистику
    USER_DATA[target_user_id]['access'] = 'DENIED'
    STATS['corrected'] += 1
    STATS['total_handled'] += 1
    
    # Отправляем пользователю сообщение с комментарием
    user_msg = get_message(target_user_id, 'access_rejected_with_comment_msg').format(comment=comment)
    await context.bot.send_message(target_user_id, user_msg)
    
    # Отправляем подтверждение админу
    await update.message.reply_text(get_message(admin_id, 'comment_sent'), reply_markup=get_admin_main_keyboard(admin_id))

    del context.user_data['target_user_id']
    return ADMIN_MENU

@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает статистику."""
    admin_id = update.effective_user.id
    
    stats_text = get_message(admin_id, 'stats_text').format(
        a=STATS['accepted'], 
        d=STATS['denied'], 
        c=STATS['corrected'], 
        t=STATS['total_handled']
    )
    
    await update.message.reply_text(stats_text, reply_markup=get_admin_main_keyboard(admin_id))
    return ADMIN_MENU

@admin_only
async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает статус бота."""
    admin_id = update.effective_user.id
    
    status_text = get_message(admin_id, 'bot_status_text').format(status=STATS['bot_status'])
    
    await update.message.reply_text(status_text, reply_markup=get_admin_main_keyboard(admin_id))
    return ADMIN_MENU

@admin_only
async def admin_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает меню рассылки."""
    admin_id = update.effective_user.id
    await update.message.reply_text(
        "Choose broadcast type:",
        reply_markup=get_admin_broadcast_keyboard(admin_id)
    )
    return ADMIN_BROADCAST_MENU

@admin_only
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает начало рассылки (сейчас или позже)."""
    admin_id = update.effective_user.id
    action = update.message.text
    
    if action == get_message(admin_id, 'btn_broadcast_now'):
        context.user_data['broadcast_type'] = 'now'
        await update.message.reply_text(
            get_message(admin_id, 'prompt_broadcast_msg'), 
            reply_markup=ReplyKeyboardRemove()
        )
        return BROADCAST_NOW_MSG
        
    elif action == get_message(admin_id, 'btn_broadcast_later'):
        context.user_data['broadcast_type'] = 'later'
        await update.message.reply_text(
            get_message(admin_id, 'prompt_broadcast_msg'), 
            reply_markup=ReplyKeyboardRemove()
        )
        return BROADCAST_LATER_MSG
    
    elif action == get_message(admin_id, 'btn_admin_back'):
        return await admin_start_menu(update, context)

    return ADMIN_BROADCAST_MENU

async def save_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет контент рассылки (текст и/или фото)."""
    admin_id = update.effective_user.id
    
    if update.message.text:
        context.user_data['broadcast_text'] = update.message.text
    if update.message.photo:
        context.user_data['broadcast_photo_id'] = update.message.photo[-1].file_id

    # Проверка на наличие контента
    if not context.user_data.get('broadcast_text') and not context.user_data.get('broadcast_photo_id'):
        await update.message.reply_text("Please provide text or a photo for the broadcast.")
        return context.user_data.get('broadcast_state') # Возвращаемся в текущее состояние
    
    # Продолжаем, в зависимости от типа рассылки
    if context.user_data.get('broadcast_type') == 'now':
        preview_text = f"Text: {context.user_data.get('broadcast_text', 'No text')}\nPhoto: {context.user_data.get('broadcast_photo_id', 'No photo')}"
        
        await update.message.reply_text(
            get_message(admin_id, 'confirm_broadcast_now') + "\n\n" + preview_text,
            reply_markup=get_confirm_keyboard(admin_id)
        )
        return BROADCAST_NOW_CONFIRM
        
    elif context.user_data.get('broadcast_type') == 'later':
        await update.message.reply_text(
            get_message(admin_id, 'prompt_broadcast_time'),
            reply_markup=ReplyKeyboardRemove()
        )
        return BROADCAST_LATER_TIME

@admin_only
async def broadcast_confirm_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение и немедленная отправка рассылки."""
    admin_id = update.effective_user.id
    action = update.message.text
    
    if action == get_message(admin_id, 'btn_confirm'):
        text = context.user_data.get('broadcast_text')
        photo_id = context.user_data.get('broadcast_photo_id')
        
        # Фильтрация только активных пользователей (исключая админа)
        user_ids = [uid for uid in USER_DATA if uid != ADMIN_ID]
        
        # Логика рассылки
        success_count = 0
        for user_id in user_ids:
            try:
                if photo_id:
                    await context.bot.send_photo(user_id, photo_id, caption=text)
                else:
                    await context.bot.send_message(user_id, text)
                success_count += 1
                # Небольшая задержка, чтобы избежать лимитов
                await asyncio.sleep(0.05) 
            except Exception as e:
                logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
                
        await update.message.reply_text(
            get_message(admin_id, 'broadcast_success') + f" (Sent to {success_count}/{len(user_ids)} users).",
            reply_markup=get_admin_main_keyboard(admin_id)
        )
        context.user_data.clear()
        return ADMIN_MENU

    elif action == get_message(admin_id, 'btn_cancel'):
        await update.message.reply_text(
            get_message(admin_id, 'broadcast_cancelled'),
            reply_markup=get_admin_main_keyboard(admin_id)
        )
        context.user_data.clear()
        return ADMIN_MENU

    return BROADCAST_NOW_CONFIRM

@admin_only
async def broadcast_set_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод времени для отложенной рассылки."""
    admin_id = update.effective_user.id
    time_str = update.message.text
    
    try:
        # Пытаемся распарсить дату и время
        scheduled_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        
        context.user_data['scheduled_time'] = scheduled_time
        
        await update.message.reply_text(
            get_message(admin_id, 'confirm_broadcast_later').format(time=scheduled_time.strftime('%Y-%m-%d %H:%M')),
            reply_markup=get_confirm_keyboard(admin_id)
        )
        return BROADCAST_LATER_CONFIRM
        
    except ValueError:
        await update.message.reply_text("Invalid format. Please use YYYY-MM-DD HH:MM (e.g., 2025-10-25 14:30).")
        return BROADCAST_LATER_TIME

@admin_only
async def broadcast_confirm_later(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение и планирование отложенной рассылки."""
    admin_id = update.effective_user.id
    action = update.message.text
    
    if action == get_message(admin_id, 'btn_confirm'):
        scheduled_time = context.user_data['scheduled_time']
        
        # Здесь должна быть логика планировщика. 
        # В рамках этого кода мы просто ставим задачу в очередь.
        
        # Формируем задачу и сохраняем ее
        job_name = f"broadcast_{scheduled_time.timestamp()}"
        
        context.job_queue.run_once(
            send_scheduled_broadcast, 
            scheduled_time, 
            data={
                'text': context.user_data.get('broadcast_text'),
                'photo_id': context.user_data.get('broadcast_photo_id'),
                'admin_id': admin_id
            },
            name=job_name
        )
        
        await update.message.reply_text(
            get_message(admin_id, 'broadcast_scheduled').format(time=scheduled_time.strftime('%Y-%m-%d %H:%M')),
            reply_markup=get_admin_main_keyboard(admin_id)
        )
        context.user_data.clear()
        return ADMIN_MENU

    elif action == get_message(admin_id, 'btn_cancel'):
        await update.message.reply_text(
            get_message(admin_id, 'broadcast_cancelled'),
            reply_markup=get_admin_main_keyboard(admin_id)
        )
        context.user_data.clear()
        return ADMIN_MENU

    return BROADCAST_LATER_CONFIRM

async def send_scheduled_broadcast(context: ContextTypes.DEFAULT_TYPE):
    """Функция, которая выполняется по расписанию для отправки рассылки."""
    data = context.job.data
    text = data.get('text')
    photo_id = data.get('photo_id')
    admin_id = data.get('admin_id')
    
    user_ids = [uid for uid in USER_DATA if uid != ADMIN_ID]
    success_count = 0
    
    for user_id in user_ids:
        try:
            if photo_id:
                await context.bot.send_photo(user_id, photo_id, caption=text)
            else:
                await context.bot.send_message(user_id, text)
            success_count += 1
            await asyncio.sleep(0.05) 
        except Exception as e:
            logger.warning(f"Scheduled broadcast failed for user {user_id}: {e}")
            
    # Уведомление админа о завершении рассылки
    await context.bot.send_message(
        admin_id, 
        f"✅ Scheduled broadcast completed! Sent to {success_count}/{len(user_ids)} users."
    )

# --- ОСНОВНАЯ ФУНКЦИЯ БОТА ---

def main() -> None:
    """Запускает бота."""
    application = Application.builder().token(TOKEN).build()

    # ВРЕМЕННЫЙ ХЕНДЛЕР ДЛЯ ПОЛУЧЕНИЯ FILE ID
    if GET_FILE_ID_MODE:
        application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT, get_file_id_handler))
        logger.info("Bot started in GET_FILE_ID_MODE. Send files to get their IDs.")
        application.run_polling(poll_interval=1)
        return

    # --- Conversation Handler для Пользователя ---
    user_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("menu", go_to_main_menu)],
        
        states={
            START_MENU: [
                CallbackQueryHandler(set_language, pattern='^set_lang_'),
            ],
            MAIN_MENU: [
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_instruction'])}") | filters.Regex(f"^{re.escape(MESSAGES['RU']['btn_instruction'])}") | filters.Regex(f"^{re.escape(MESSAGES['ES']['btn_instruction'])}") | filters.Regex(f"^{re.escape(MESSAGES['PT']['btn_instruction'])}"), handle_instruction),
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_registration'])}") | filters.Regex(f"^{re.escape(MESSAGES['RU']['btn_registration'])}") | filters.Regex(f"^{re.escape(MESSAGES['ES']['btn_registration'])}") | filters.Regex(f"^{re.escape(MESSAGES['PT']['btn_registration'])}"), handle_registration),
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_get_access'])}") | filters.Regex(f"^{re.escape(MESSAGES['RU']['btn_get_access'])}") | filters.Regex(f"^{re.escape(MESSAGES['ES']['btn_get_access'])}") | filters.Regex(f"^{re.escape(MESSAGES['PT']['btn_get_access'])}"), handle_get_access),
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_get_promo'])}") | filters.Regex(f"^{re.escape(MESSAGES['RU']['btn_get_promo'])}") | filters.Regex(f"^{re.escape(MESSAGES['ES']['btn_get_promo'])}") | filters.Regex(f"^{re.escape(MESSAGES['PT']['btn_get_promo'])}"), handle_get_promo_code),
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_change_lang'])}") | filters.Regex(f"^{re.escape(MESSAGES['RU']['btn_change_lang'])}") | filters.Regex(f"^{re.escape(MESSAGES['ES']['btn_change_lang'])}") | filters.Regex(f"^{re.escape(MESSAGES['PT']['btn_change_lang'])}"), handle_change_lang),
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_support'])}") | filters.Regex(f"^{re.escape(MESSAGES['RU']['btn_support'])}") | filters.Regex(f"^{re.escape(MESSAGES['ES']['btn_support'])}") | filters.Regex(f"^{re.escape(MESSAGES['PT']['btn_support'])}"), handle_support),
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_launch_app'])}") | filters.Regex(f"^{re.escape(MESSAGES['RU']['btn_launch_app'])}") | filters.Regex(f"^{re.escape(MESSAGES['ES']['btn_launch_app'])}") | filters.Regex(f"^{re.escape(MESSAGES['PT']['btn_launch_app'])}"), handle_launch_app),
                
                # Хендлер для возврата админа в админ-меню
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_menu_back'])}"), admin_start_menu),
            ],
            AWAITING_ID: [
                MessageHandler(filters.PHOTO | filters.TEXT, handle_user_id_input),
            ],
            AWAITING_CHANNEL_CHECK: [
                CallbackQueryHandler(handle_check_subscription, pattern='^check_sub_now$'),
                # Добавляем хендлер для возврата в меню из Promo-flow, если пользователь нажмет кнопку-текст
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_menu_back'])}") | filters.Regex(f"^{re.escape(MESSAGES['RU']['btn_menu_back'])}"), go_to_main_menu),
            ],
            # --- Админские состояния ---
            ADMIN_MENU: [
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_admin_apps'].split('(')[0].strip())}"), admin_apps_menu),
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_admin_status'])}"), admin_status),
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_admin_stats'])}"), admin_stats),
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_admin_broadcast'])}"), admin_broadcast_menu),
                # Меню заявок
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_start_processing'])}"), start_processing),
                # Выход из админ-меню в пользовательское
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_admin_back'])}"), go_to_main_menu),
            ],
            PROCESSING_REQUESTS: [
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_accept'])}") | filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_reject'])}") | filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_reject_comment'])}") | filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_menu_back'])}"), process_request_action),
            ],
            PROCESS_REQUEST_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_request_comment_input),
            ],
            ADMIN_BROADCAST_MENU: [
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_broadcast_now'])}") | filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_broadcast_later'])}") | filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_admin_back'])}"), start_broadcast),
            ],
            BROADCAST_NOW_MSG: [
                MessageHandler(filters.ALL & ~filters.COMMAND, save_broadcast_content),
            ],
            BROADCAST_NOW_CONFIRM: [
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_confirm'])}") | filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_cancel'])}"), broadcast_confirm_now),
            ],
            BROADCAST_LATER_MSG: [
                MessageHandler(filters.ALL & ~filters.COMMAND, save_broadcast_content),
            ],
            BROADCAST_LATER_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_set_time),
            ],
            BROADCAST_LATER_CONFIRM: [
                MessageHandler(filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_confirm'])}") | filters.Regex(f"^{re.escape(MESSAGES['EN']['btn_cancel'])}"), broadcast_confirm_later),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(user_conv_handler)
    
    logger.info("Bot started successfully. Polling for updates...")
    application.run_polling(poll_interval=1)

if __name__ == '__main__':
    main()



