import logging
import asyncio 
import re 
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler, ContextTypes
from functools import wraps
from collections import deque
from datetime import datetime
from telegram.error import BadRequest

# --- CONFIGURAÇÃO ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurações CORRIGIDAS
TOKEN = "7692269177:AAGnz7egfTyoMwDY2y1px8Wmok-2W0BCecg"  # Token direto para evitar problemas
ADMIN_IDS = [7428791161, 1993108159]  # Lista de admins
SUPPORT_USERNAME = "koalamoney3"  # Sem @ para URLs
PROMO_CODE = "MOB500RR"
REG_LINK = "https://1wbkpnt.com/?open=register&p=gv72"
CHANNEL_LINK = "https://t.me/+dWqBt5Ix380zNjI5"
CHANNEL_USERNAME = "@mgoldenmines"  # Com @ para verificação
MINI_APP_URL = "https://zenobioyenom.github.io/appmineswin/"

# Modo de desenvolvimento para obter FILE IDs
GET_FILE_ID_MODE = False

# IDs das imagens (substituir pelos reais)
PHOTO_IDS = {
    'privet': 'AgACAgQAAxkBAAIB...',
    'menu': 'AgACAgQAAxkBAAIB...', 
    'instr': 'AgACAgQAAxkBAAIB...',
    'id_example': 'AgACAgQAAxkBAAIB...',
    'reg_RU': 'AgACAgQAAxkBAAIB...',
    'reg_EN': 'AgACAgQAAxkBAAIB...',
    'reg_ES': 'AgACAgQAAxkBAAIB...',
    'reg_PT': 'AgACAgQAAxkBAAIB...',
}

# Estados da conversação CORRIGIDOS
START_MENU, MAIN_MENU = range(2)
AWAITING_ID, AWAITING_CHANNEL_CHECK = range(2, 4)
ADMIN_MENU, ADMIN_BROADCAST_MENU = range(4, 6)
BROADCAST_NOW_MSG, BROADCAST_NOW_CONFIRM = range(6, 8)
BROADCAST_LATER_MSG, BROADCAST_LATER_TIME, BROADCAST_LATER_CONFIRM = range(8, 11)
PROCESSING_REQUESTS, PROCESS_REQUEST_COMMENT = range(11, 13)

# Banco de dados
USER_DATA = {}
PENDING_QUEUE = deque([])
STATS = {
    'accepted': 0,
    'denied': 0,
    'corrected': 0,
    'total_handled': 0,
    'bot_status': '✅ Operating normally'
}

# --- SISTEMA DE MENSAGENS MULTILÍNGUE ---

MESSAGES = {
    'EN': {
        'start_user': "🌐 Select your language / Elige tu idioma / Escolha o idioma 🌐",
        'start_admin': "👨‍💻 Admin Panel\nWelcome back!",
        'language_set': "Language set to English.",
        'admin_access_denied': "Access denied. You are not an administrator.",
        'photo_placeholder': "[Image]",
        'support_link_text': "Click to contact support: @{username}",
        
        # Botões do usuário
        'btn_instruction': "📖 Instruction",
        'btn_registration': "🔗 Registration", 
        'btn_get_access': "🔑 Get Bot Access",
        'btn_change_lang': "🌍 Change Language",
        'btn_support': "💬 Contact Support",
        'btn_launch_app': "🚀 Launch Program",
        'btn_menu_back': "↩️ Back to Menu",
        'btn_get_promo': "💰 Get Promo Code",
        'btn_check_sub': "✅ Check Subscription",
        
        # Status do usuário
        'menu_access_closed': "Access to the program: 🔴 Closed",
        'menu_access_granted': "Access to the program: 🟢 Granted", 
        'menu_telegram_id': "Your Telegram ID: {id}",
        'menu_game_id_none': "Your Game ID: Not set",
        'menu_game_id_set': "Your Game ID: {game_id}",
        'menu_pending': "Your application is pending review. Please wait.",
        'access_denied_perm': "Access was denied by the administrator. Status: ❌ Denied",
        
        # Mensagens de acesso
        'access_granted_msg': "🎉 **Congratulations! Access has been granted!**\n\nYou can now use the 'Launch Program' button.",
        'access_rejected_msg': "Access was denied. If you think this is an error, please check the instructions and try again.",
        'access_rejected_with_comment_msg': "Access was denied. Reason: {comment}\nPlease check the instructions and resend your application.",
        'launch_denied': "❌ Access denied. Please submit or wait for approval of your application.",
        'awaiting_id_prompt': "Please send your account ID or a screenshot showing the ID.",
        'application_received': "✅ Information accepted! Your application is under review.",
        'reg_button_text': "🔗 Registration Link",
        
        # Sistema de promoção
        'promo_check_prompt': "To receive the promo code, you must subscribe to our channel: {link}",
        'promo_not_subscribed': "You are not yet subscribed. Please subscribe and press the 'Check Subscription' button.",
        'promo_subscribed_success': "✅ Subscription verified! Your exclusive promo code is: `{promo}`",
        'promo_code_already_sent': "You already have the promo code: `{promo}`",
        'promo_channel_error': "⚠️ Cannot verify subscription. Please ensure the bot is an administrator in the channel.",
        'promo_needed_note': "Please get your promo code first by clicking '💰 Get Promo Code'",
        
        # Instruções
        'instr_text': (
            "📖 **INSTRUCTIONS FOR GETTING STARTED**\n\n"
            "1) Get the exclusive promo code by pressing the '💰 Get Promo Code' button.\n"
            "2) Register using the exclusive link: {link}\n"
            "3) When registering, be sure to use the promo code you received.\n"
            "4) Click the '🔑 Get Bot Access' button in our chat.\n"
            "5) Send the bot your registration ID (account number on 1win).\n"
            "6) Wait for the connection. As soon as the bot is connected, you will be granted access."
        ),
        
        # Admin
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
        'app_accepted': "✅ Application ACCEPTED. User notified.",
        'app_rejected': "❌ Application REJECTED. User notified.",
        'prompt_reject_comment': "Please send the rejection comment you want to send to the user.",
        'comment_sent': "Application REJECTED with comment. User notified.",
        'stats_text': "📊 Statistics:\nAccepted users: {a}\nUsers denied access: {d}\nRequests sent for correction: {c}\nTotal requests handled: {t}",
        'bot_status_text': "Current bot status: {status}",
        'status_normal': "✅ Operating normally",
        
        # Broadcast system
        'prompt_broadcast_msg': "Please send the message (text and/or photo) you want to broadcast.",
        'confirm_broadcast_now': "CONFIRM: This message will be sent to all users NOW.",
        'broadcast_success': "Broadcast sent successfully to all active users.",
        'prompt_broadcast_time': "Please specify the time and date (e.g., 2025-10-25 14:30) for the scheduled broadcast.",
        'confirm_broadcast_later': "CONFIRM: This message is scheduled for {time} UTC.",
        'broadcast_scheduled': "Broadcast successfully scheduled for {time}.",
        'broadcast_cancelled': "Broadcast sending cancelled. Returning to Admin Menu.",
    },
    'PT': {
        'start_user': "🌐 Selecione seu idioma / Choose your language / Elige tu idioma 🌐",
        'language_set': "Idioma definido para Português.",
        'photo_placeholder': "[Imagem]",
        'support_link_text': "Clique para contatar suporte: @{username}",
        
        'btn_instruction': "📖 Instrução",
        'btn_registration': "🔗 Registro",
        'btn_get_access': "🔑 Obter Acesso ao Bot",
        'btn_change_lang': "🌍 Mudar Idioma", 
        'btn_support': "💬 Contatar Suporte",
        'btn_launch_app': "🚀 Lançar Programa",
        'btn_get_promo': "💰 Obter Código Promocional",
        'btn_check_sub': "✅ Verificar Assinatura",
        
        'menu_access_closed': "Acesso ao programa: 🔴 Fechado",
        'menu_access_granted': "Acesso ao programa: 🟢 Concedido",
        'menu_telegram_id': "Seu ID do Telegram: {id}",
        'menu_game_id_none': "Seu ID de Jogo: Não definido", 
        'menu_game_id_set': "Seu ID de Jogo: {game_id}",
        'menu_pending': "Sua aplicação está sob revisão. Por favor aguarde.",
        
        'access_granted_msg': "🎉 **Parabéns! Acesso concedido!**\n\nAgora você pode usar o botão 'Lançar Programa'.",
        'awaiting_id_prompt': "Por favor envie seu ID da conta ou uma captura de tela mostrando o ID.",
        'application_received': "✅ Informação aceita! Sua aplicação está sob revisão.",
        
        'promo_check_prompt': "Para receber o código promocional, você deve se inscrever no nosso canal: {link}",
        'promo_subscribed_success': "✅ Inscrição verificada! Seu código promocional exclusivo é: `{promo}`",
        'promo_needed_note': "Por favor, obtenha seu código promocional primeiro clicando em '💰 Obter Código Promocional'",
        
        'instr_text': (
            "📖 **INSTRUÇÕES PARA COMEÇAR**\n\n"
            "1) Obtenha o código promocional exclusivo pressionando o botão '💰 Obter Código Promocional'.\n"
            "2) Registre-se usando o link exclusivo: {link}\n"
            "3) Ao se registrar, use o código promocional recebido.\n"
            "4) Clique no botão '🔑 Obter Acesso ao Bot' no nosso chat.\n"
            "5) Envie ao bot seu ID de registro (número da conta no 1win).\n"
            "6) Aguarde a conexão. Assim que o bot estiver conectado, o acesso será concedido."
        ),
        
        'btn_admin_apps': "🧾 Aplicações ({count})",
        'btn_admin_stats': "📊 Estatísticas",
        'apps_pending_count': "Solicitações ativas pendentes: {count}",
        'stats_text': "📊 Estatísticas:\nUsuários aceitos: {a}\nUsuários negados: {d}\nSolicitações corrigidas: {c}\nTotal processado: {t}",
    }
}

# --- FUNÇÕES UTILITÁRIAS CORRIGIDAS ---

def get_message(user_id, key, **kwargs):
    """Obtém mensagem no idioma do usuário"""
    if user_id in ADMIN_IDS:
        lang = 'EN'
    else:
        lang = USER_DATA.get(user_id, {}).get('lang', 'EN')
    
    message = MESSAGES.get(lang, MESSAGES['EN']).get(key, MESSAGES['EN'].get(key, key))
    return message.format(**kwargs) if kwargs else message

def get_photo_id(key):
    """Obtém File ID da foto"""
    return PHOTO_IDS.get(key)

def admin_only(func):
    """Decorator para funções apenas de admin"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id in ADMIN_IDS:
            return await func(update, context, *args, **kwargs)
        else:
            message = get_message(user_id, 'admin_access_denied')
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(message)
            elif update.message:
                await update.message.reply_text(message)
            return MAIN_MENU
    return wrapper

def get_user_status(user_id):
    return USER_DATA.get(user_id, {}).get('access', 'NONE')

def get_user_game_id(user_id):
    return USER_DATA.get(user_id, {}).get('game_id')

def has_promo_code(user_id):
    return USER_DATA.get(user_id, {}).get('has_promo', False)

# --- HANDLERS PRINCIPAIS CORRIGIDOS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    if user_id not in USER_DATA:
        lang_code = update.effective_user.language_code
        USER_DATA[user_id] = {
            'lang': lang_code.upper() if lang_code and lang_code.upper() in MESSAGES else 'EN', 
            'access': 'NONE', 
            'game_id': None, 
            'application_info': {}, 
            'has_promo': False
        }
    
    if user_id in ADMIN_IDS:
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
            await update.message.reply_photo(photo_id, caption=caption, reply_markup=get_lang_keyboard())
        else:
            await update.message.reply_text(caption, reply_markup=get_lang_keyboard())
        return START_MENU

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = query.data.split('_')[2]
    
    USER_DATA[user_id]['lang'] = lang_code
    
    await query.edit_message_text(get_message(user_id, 'language_set'))
    await show_user_main_menu(update, context)
    return MAIN_MENU

async def show_user_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra menu principal - CORRIGIDO"""
    user_id = update.effective_user.id
    
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
        
    text = f"{status_line}\n\n{get_message(user_id, 'menu_telegram_id').format(id=user_id)}\n{game_id_line}"
    
    photo_id = get_photo_id('menu')
    if photo_id:
        await context.bot.send_photo(
            chat_id=user_id,
            photo=photo_id, 
            caption=text,
            reply_markup=get_main_menu_keyboard(user_id)
        )
    else:
        await context.bot.send_message(
            chat_id=user_id, 
            text=text,
            reply_markup=get_main_menu_keyboard(user_id)
        )

async def handle_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    text = get_message(user_id, 'instr_text').format(link=REG_LINK)
    
    photo_id = get_photo_id('instr')
    if photo_id:
        await update.message.reply_photo(photo_id, caption=text, reply_markup=get_main_menu_keyboard(user_id))
    else:
        await update.message.reply_text(text, reply_markup=get_main_menu_keyboard(user_id))
    return MAIN_MENU

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    if has_promo_code(user_id):
        promo_note = f"\n\n🎁 Your promo code: `{PROMO_CODE}`"
    else:
        promo_note = f"\n\n{get_message(user_id, 'promo_needed_note')}"
    
    text = f"🔗 {REG_LINK}{promo_note}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_message(user_id, 'reg_button_text'), url=REG_LINK)],
    ])
    
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    return MAIN_MENU

async def handle_get_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    return AWAITING_CHANNEL_CHECK

async def handle_check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if has_promo_code(user_id):
        await show_user_main_menu(update, context)
        return MAIN_MENU

    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        if member.status not in ['left', 'kicked']:
            USER_DATA[user_id]['has_promo'] = True
            text = get_message(user_id, 'promo_subscribed_success').format(promo=PROMO_CODE)
            await query.edit_message_text(text, parse_mode='Markdown')
            await show_user_main_menu(update, context)
            return MAIN_MENU
        else:
            text = get_message(user_id, 'promo_not_subscribed')
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Telegram Channel", url=CHANNEL_LINK)],
                [InlineKeyboardButton(get_message(user_id, 'btn_check_sub'), callback_data='check_sub_now')],
            ])
            await query.edit_message_text(text, reply_markup=keyboard)
            return AWAITING_CHANNEL_CHECK
            
    except BadRequest as e:
        logger.error(f"Error checking subscription: {e}")
        error_text = get_message(user_id, 'promo_channel_error')
        await query.edit_message_text(error_text)
        return MAIN_MENU
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await query.edit_message_text("An unexpected error occurred. Please try again later.")
        return MAIN_MENU

async def handle_get_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    status = get_user_status(user_id)
    
    if not has_promo_code(user_id):
        await update.message.reply_text(get_message(user_id, 'promo_needed_note'))
        return MAIN_MENU
        
    if status == 'GRANTED':
        keyboard = [
            [InlineKeyboardButton("📲 Open Application", web_app=WebAppInfo(url=MINI_APP_URL))],
            [InlineKeyboardButton("🆘 Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            get_message(user_id, 'access_granted_msg'),
            reply_markup=reply_markup
        )
        return MAIN_MENU
        
    if status == 'PENDING':
        await update.message.reply_text(get_message(user_id, 'menu_pending'))
        return MAIN_MENU
    
    USER_DATA[user_id]['application_info'] = {'text': None, 'photo_id': None, 'timestamp': None}
    text = get_message(user_id, 'awaiting_id_prompt')
    photo_id = get_photo_id('id_example')
    
    if photo_id:
        await update.message.reply_photo(photo_id, caption=text)
    else:
        await update.message.reply_text(text)
        
    return AWAITING_ID

async def handle_user_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    application_info = USER_DATA[user_id].get('application_info', {})

    if update.message.text:
        game_id = update.message.text.strip()
        if not re.match(r'^\d{4,}$', game_id):
            await update.message.reply_text(get_message(user_id, 'awaiting_id_prompt'))
            return AWAITING_ID

        application_info['text'] = game_id
        application_info['game_id'] = game_id
        USER_DATA[user_id]['game_id'] = game_id
        
    elif update.message.photo:
        photo_id = update.message.photo[-1].file_id
        application_info['photo_id'] = photo_id
        
        if not application_info.get('text'):
            await update.message.reply_text("Thanks for the screenshot. Please also send your account ID as text.")
            return AWAITING_ID
        
    else:
        await update.message.reply_text(get_message(user_id, 'awaiting_id_prompt'))
        return AWAITING_ID

    if application_info.get('game_id'):
        USER_DATA[user_id]['access'] = 'PENDING'
        application_info['timestamp'] = datetime.now()
        
        PENDING_QUEUE.append(user_id)
        
        await update.message.reply_text(get_message(user_id, 'application_received'))
        
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id, 
                    f"🔔 New application from user {user_id}. Queue: {len(PENDING_QUEUE)}"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
        
        return MAIN_MENU
    else:
        await update.message.reply_text(get_message(user_id, 'awaiting_id_prompt'))
        return AWAITING_ID

async def handle_launch_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    status = get_user_status(user_id)
    
    if status == 'GRANTED':
        keyboard = [[InlineKeyboardButton(
            get_message(user_id, 'btn_launch_app'), 
            web_app=WebAppInfo(url=MINI_APP_URL)
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            get_message(user_id, 'access_granted_msg'),
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(get_message(user_id, 'launch_denied'))
        
    return MAIN_MENU

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    text = get_message(user_id, 'support_link_text').format(username=SUPPORT_USERNAME)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Support", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ])
    
    await update.message.reply_text(text, reply_markup=keyboard)
    return MAIN_MENU

async def handle_change_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        get_message(user_id, 'start_user'),
        reply_markup=get_lang_keyboard()
    )
    return START_MENU

async def go_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    if user_id in ADMIN_IDS and update.message.text == get_message(user_id, 'btn_admin_back'):
        return await admin_start_menu(update, context)
    
    await show_user_main_menu(update, context)
    return MAIN_MENU

# --- SISTEMA DE TELECLADOS CORRIGIDOS ---

def get_lang_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("English", callback_data='set_lang_EN')],
        [InlineKeyboardButton("Português", callback_data='set_lang_PT')],
        [InlineKeyboardButton("Español", callback_data='set_lang_ES')],
        [InlineKeyboardButton("Русский", callback_data='set_lang_RU')],
    ])

def get_main_menu_keyboard(user_id):
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
    
    if user_id in ADMIN_IDS:
        buttons.append([KeyboardButton(get_message(user_id, 'btn_menu_back'))])
        
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_admin_main_keyboard(admin_id):
    count = len(PENDING_QUEUE)
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_admin_apps').format(count=count))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_status')), KeyboardButton(get_message(admin_id, 'btn_admin_stats'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_broadcast'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_back'))], 
    ], resize_keyboard=True)

def get_admin_processing_keyboard(admin_id):
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_accept'))],
        [KeyboardButton(get_message(admin_id, 'btn_reject')), KeyboardButton(get_message(admin_id, 'btn_reject_comment'))],
        [KeyboardButton(get_message(admin_id, 'btn_menu_back'))],
    ], resize_keyboard=True)

def get_admin_apps_menu(admin_id):
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_start_processing'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_back'))],
    ], resize_keyboard=True)

def get_admin_broadcast_keyboard(admin_id):
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_broadcast_now')), KeyboardButton(get_message(admin_id, 'btn_broadcast_later'))],
        [KeyboardButton(get_message(admin_id, 'btn_admin_back'))],
    ], resize_keyboard=True)

def get_confirm_keyboard(admin_id):
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_message(admin_id, 'btn_confirm')), KeyboardButton(get_message(admin_id, 'btn_cancel'))],
    ], resize_keyboard=True)

# --- SISTEMA ADMIN CORRIGIDO ---

@admin_only
async def admin_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = update.effective_user.id
    await update.message.reply_text(
        "Welcome to Admin Panel.",
        reply_markup=get_admin_main_keyboard(admin_id)
    )
    return ADMIN_MENU

@admin_only
async def admin_apps_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = update.effective_user.id
    count = len(PENDING_QUEUE)
    
    text = get_message(admin_id, 'apps_pending_count').format(count=count)
    
    if count > 0:
        await update.message.reply_text(text, reply_markup=get_admin_apps_menu(admin_id))
    else:
        await update.message.reply_text(text + "\n(No pending requests.)", reply_markup=get_admin_main_keyboard(admin_id))
    return ADMIN_MENU

@admin_only
async def start_processing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = update.effective_user.id
    
    if not PENDING_QUEUE:
        await update.message.reply_text("The application queue is empty.", reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU
    
    target_user_id = PENDING_QUEUE.popleft()
    context.user_data['target_user_id'] = target_user_id
    
    user_data = USER_DATA.get(target_user_id, {})
    app_info = user_data.get('application_info', {})
    
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

    if app_info.get('photo_id'):
        await update.message.reply_photo(
            photo=app_info['photo_id'],
            caption=final_text,
            reply_markup=get_admin_processing_keyboard(admin_id)
        )
    else:
        await update.message.reply_text(final_text, reply_markup=get_admin_processing_keyboard(admin_id))
        
    return PROCESSING_REQUESTS

@admin_only
async def process_request_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = update.effective_user.id
    action = update.message.text
    target_user_id = context.user_data.get('target_user_id')
    
    if not target_user_id:
        await update.message.reply_text("Error: No user ID found for processing.", reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU

    if action == get_message(admin_id, 'btn_accept'):
        USER_DATA[target_user_id]['access'] = 'GRANTED'
        STATS['accepted'] += 1
        STATS['total_handled'] += 1
        
        await context.bot.send_message(target_user_id, get_message(target_user_id, 'access_granted_msg'))
        await update.message.reply_text(get_message(admin_id, 'app_accepted'), reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU

    elif action == get_message(admin_id, 'btn_reject_comment'):
        await update.message.reply_text(get_message(admin_id, 'prompt_reject_comment'), reply_markup=ReplyKeyboardRemove())
        return PROCESS_REQUEST_COMMENT

    elif action == get_message(admin_id, 'btn_reject'):
        USER_DATA[target_user_id]['access'] = 'DENIED'
        STATS['denied'] += 1
        STATS['total_handled'] += 1
        
        await context.bot.send_message(target_user_id, get_message(target_user_id, 'access_rejected_msg'))
        await update.message.reply_text(get_message(admin_id, 'app_rejected'), reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU
        
    elif action == get_message(admin_id, 'btn_menu_back'):
        PENDING_QUEUE.appendleft(target_user_id) 
        del context.user_data['target_user_id']
        await update.message.reply_text("Request deferred. Returning to Admin Menu.", reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU

    return PROCESSING_REQUESTS

@admin_only
async def process_request_comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = update.effective_user.id
    comment = update.message.text
    target_user_id = context.user_data.get('target_user_id')
    
    if not target_user_id:
        await update.message.reply_text("Error: No user ID found for processing.", reply_markup=get_admin_main_keyboard(admin_id))
        return ADMIN_MENU

    USER_DATA[target_user_id]['access'] = 'DENIED'
    STATS['corrected'] += 1
    STATS['total_handled'] += 1
    
    user_msg = get_message(target_user_id, 'access_rejected_with_comment_msg').format(comment=comment)
    await context.bot.send_message(target_user_id, user_msg)
    
    await update.message.reply_text(get_message(admin_id, 'comment_sent'), reply_markup=get_admin_main_keyboard(admin_id))

    del context.user_data['target_user_id']
    return ADMIN_MENU

@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    admin_id = update.effective_user.id
    
    status_text = get_message(admin_id, 'bot_status_text').format(status=STATS['bot_status'])
    
    await update.message.reply_text(status_text, reply_markup=get_admin_main_keyboard(admin_id))
    return ADMIN_MENU

# --- SISTEMA DE BROADCAST CORRIGIDO ---

@admin_only
async def admin_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = update.effective_user.id
    await update.message.reply_text(
        "Choose broadcast type:",
        reply_markup=get_admin_broadcast_keyboard(admin_id)
    )
    return ADMIN_BROADCAST_MENU

@admin_only
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    admin_id = update.effective_user.id
    
    if update.message.text:
        context.user_data['broadcast_text'] = update.message.text
    if update.message.photo:
        context.user_data['broadcast_photo_id'] = update.message.photo[-1].file_id

    if not context.user_data.get('broadcast_text') and not context.user_data.get('broadcast_photo_id'):
        await update.message.reply_text("Please provide text or a photo for the broadcast.")
        return context.user_data.get('broadcast_state')
    
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
    admin_id = update.effective_user.id
    action = update.message.text
    
    if action == get_message(admin_id, 'btn_confirm'):
        text = context.user_data.get('broadcast_text')
        photo_id = context.user_data.get('broadcast_photo_id')
        
        user_ids = [uid for uid in USER_DATA if uid not in ADMIN_IDS]
        
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
    admin_id = update.effective_user.id
    time_str = update.message.text
    
    try:
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
    admin_id = update.effective_user.id
    action = update.message.text
    
    if action == get_message(admin_id, 'btn_confirm'):
        scheduled_time = context.user_data['scheduled_time']
        
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
    data = context.job.data
    text = data.get('text')
    photo_id = data.get('photo_id')
    admin_id = data.get('admin_id')
    
    user_ids = [uid for uid in USER_DATA if uid not in ADMIN_IDS]
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
            
    await context.bot.send_message(
        admin_id, 
        f"✅ Scheduled broadcast completed! Sent to {success_count}/{len(user_ids)} users."
    )

# --- HANDLER PARA FILE IDs ---
async def get_file_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        await update.message.reply_text(f"📸 FILE ID: `{file_id}`", parse_mode='Markdown')
    elif update.message.document:
        file_id = update.message.document.file_id
        await update.message.reply_text(f"📄 FILE ID: `{file_id}`", parse_mode='Markdown')
    else:
        await update.message.reply_text("Send a photo or document to get its FILE ID")

# --- CONFIGURAÇÃO PRINCIPAL CORRIGIDA ---

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    if GET_FILE_ID_MODE:
        application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT, get_file_id_handler))
        print("🛠️ FILE ID MODE ACTIVE")
        application.run_polling()
        return

    # Conversation handler CORRIGIDO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            START_MENU: [
                CallbackQueryHandler(set_language, pattern='^set_lang_'),
            ],
            MAIN_MENU: [
                MessageHandler(filters.Regex('^📖 '), handle_instruction),
                MessageHandler(filters.Regex('^🔗 '), handle_registration),
                MessageHandler(filters.Regex('^💰 '), handle_get_promo_code),
                MessageHandler(filters.Regex('^🔑 '), handle_get_access),
                MessageHandler(filters.Regex('^🚀 '), handle_launch_app),
                MessageHandler(filters.Regex('^💬 '), handle_support),
                MessageHandler(filters.Regex('^🌍 '), handle_change_lang),
                MessageHandler(filters.Regex('^🧾 '), admin_apps_menu),
                MessageHandler(filters.Regex('^🤖 '), admin_status),
                MessageHandler(filters.Regex('^📊 '), admin_stats),
                MessageHandler(filters.Regex('^💬 User Messages$'), admin_broadcast_menu),
                MessageHandler(filters.Regex('^↩️ '), go_to_main_menu),
            ],
            AWAITING_CHANNEL_CHECK: [
                CallbackQueryHandler(handle_check_subscription, pattern='^check_sub_now$'),
            ],
            AWAITING_ID: [
                MessageHandler(filters.TEXT | filters.PHOTO, handle_user_id_input),
            ],
            ADMIN_MENU: [
                MessageHandler(filters.Regex('^🧾 '), admin_apps_menu),
                MessageHandler(filters.Regex('^🤖 '), admin_status),
                MessageHandler(filters.Regex('^📊 '), admin_stats),
                MessageHandler(filters.Regex('^💬 User Messages$'), admin_broadcast_menu),
                MessageHandler(filters.Regex('^🚀 '), start_processing),
                MessageHandler(filters.Regex('^↩️ '), go_to_main_menu),
            ],
            PROCESSING_REQUESTS: [
                MessageHandler(filters.Regex('^(✅ |❌ |💬 |↩️ )'), process_request_action),
            ],
            PROCESS_REQUEST_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_request_comment_input),
            ],
            ADMIN_BROADCAST_MENU: [
                MessageHandler(filters.Regex('^(Send Now|Send Later|↩️ )'), start_broadcast),
            ],
            BROADCAST_NOW_MSG: [
                MessageHandler(filters.ALL & ~filters.COMMAND, save_broadcast_content),
            ],
            BROADCAST_NOW_CONFIRM: [
                MessageHandler(filters.Regex('^(✅ Confirm|❌ Cancel)'), broadcast_confirm_now),
            ],
            BROADCAST_LATER_MSG: [
                MessageHandler(filters.ALL & ~filters.COMMAND, save_broadcast_content),
            ],
            BROADCAST_LATER_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_set_time),
            ],
            BROADCAST_LATER_CONFIRM: [
                MessageHandler(filters.Regex('^(✅ Confirm|❌ Cancel)'), broadcast_confirm_later),
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('menu', go_to_main_menu))
    
    logger.info("🤖 Bot started successfully!")
    application.run_polling()

if __name__ == '__main__':
    main()
