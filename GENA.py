import re
import subprocess
import platform
# import telegram (ЧИСТО ДЛЯ ФУНКЦИИ С ID-КАРТИНОК)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler, CommandHandler
from telegram.constants import ParseMode 

#ОСНОВНЫЕ ДАННЫЕ ДЛЯ РАБОТЫ БОТА
SUPPORT_CHAT_ID = -100 #ОБЯЗАТЕЛЬНО ДЛЯ РАБОТЫ БОТА!
TELEGRAM_TOKEN = "" #ОБЯЗАТЕЛЬНО ДЛЯ РАБОТЫ БОТА!

TARGET_SERVERS = {
    "TranSibVPN-Германия-02": "", #ОБЯЗАТЕЛЬНО ДЛЯ ПРОВЕРКИ СТАТУСА!
    "TranSibVPN-Финляндия-02": "", #ОБЯЗАТЕЛЬНО ДЛЯ ПРОВЕРКИ СТАТУСА!       
    "TranSibVPN-Латвия-01": "", #ОБЯЗАТЕЛЬНО ДЛЯ ПРОВЕРКИ СТАТУСА!
    "TranSibVPN-Нидерланды-01": "" #ОБЯЗАТЕЛЬНО ДЛЯ ПРОВЕРКИ СТАТУСА!         
}

CB_MENU = 'menu_main'
CB_KNOWLEDGE = 'menu_baza'
CB_STATUS = 'menu_status'
CB_SUBMIT = 'menu_request' 

USER_STATE = {} 
USER_CATEGORY = {} 

PHOTO_ID_KEY = 'main_photo_id'
START_PHOTO_ID = '' #ID ЛЮБОЙ ФОТОГРАФИИ!

CATEGORIES = {
    "PAYMENT": "💰 Проблема с оплатой", 
    "TECH": "💻 Проблема с подключением", 
    "GENERAL": "❓ Другая проблема" 
}

#КОД ДЛЯ ПРОВЕРКИ СТАТУСА СЕРВЕРОВ
def ping_server(address: str) -> str:

    system = platform.system().lower()
    
    if system == 'windows':
        param = '-n'
        timeout_param = '-w'
        timeout_val = '4000' 
        command = ['ping', param, '1', timeout_param, timeout_val, address]
    else:
        param = '-c'
        timeout_param = '-W'
        timeout_val = '4'
        command = ['ping', param, '1', timeout_param, timeout_val, address]
        
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            timeout=5 
        )
        
        if result.returncode == 0:
            if system == 'windows':
                match = re.search(r'Average = (\d+)ms', result.stdout)
                if match:
                    return f"✅ OK (Задержка: {match.group(1)} мс)"
            else:
                match = re.search(r'min/avg/max/mdev = [\d\.]+/([\d\.]+)', result.stdout)
                if match:
                    return f"✅ OK (Задержка: {round(float(match.group(1)))} мс)"

            return "✅ OK (Задержка: <500 мс)"
            
        else:
            return "❌ ТАЙМАУТ или недоступен"

    except subprocess.TimeoutExpired:
        return "❌ ТАЙМАУТ (Превышен лимит 5 с)"
    except Exception as e:
        return f"⚠️ ОШИБКА проверки ({escape_markdown_v2(str(e))})"

#ЭКРАНИРОВАНИЕ ДЛЯ МАКРКДАУНА
def escape_markdown_v2(text: str) -> str:
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)

#МЕНЮ В ГЛАВНОМ МЕНЮ
def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("✍️ Отправить заявку о вашей проблеме", callback_data=CB_SUBMIT)],
        [InlineKeyboardButton("📚 БАЗА-ЗНАНИЙ", callback_data=CB_KNOWLEDGE)],
        [InlineKeyboardButton("⚡️ Проверить статус", callback_data=CB_STATUS)],
    ]
    return InlineKeyboardMarkup(keyboard)

#КНОПКА ДЛЯ ВОЗВРАТА В ГЛАВНОЕ МЕНЮ
def get_return_to_main_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Вернуться в главное меню", callback_data=CB_MENU)]
    ])

#ГЛАВНОЕ МЕНЮ
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None) -> None:
    user_id = update.effective_user.id
    
    USER_STATE.pop(user_id, None)
    USER_CATEGORY.pop(user_id, None)

    caption = 'Здравствуйте! Моё имя Гена - я виртуальный технический помошник сервиса TranSib. \n\nМоя задача помочь вам в ваших трудностях, либо перенаправить вас на наших специалистов самым быстрым способом. \n\nЧем я могу вам помочь?'
    
    bot = context.bot
    chat_id = update.effective_chat.id
    
    if message_id:
        photo_id = context.user_data.get(PHOTO_ID_KEY, START_PHOTO_ID)
        
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(
                media=photo_id,
                caption=caption,
                parse_mode=None
            ),
            reply_markup=get_main_menu_keyboard() 
        )
    else:

        sent_message = await bot.send_photo(
            chat_id=chat_id,
            photo=START_PHOTO_ID,
            caption=caption,
            reply_markup=get_main_menu_keyboard()
        )
        context.user_data[PHOTO_ID_KEY] = sent_message.photo[-1].file_id

#ЗАГЛУШКА ПРИ ВВОДЕ КОМАНДЫ START (КОСТЫЛЬ)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            text="Загрузка...", 
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True),
            disable_notification=True
        )
        try:
            await context.bot.delete_message(
                chat_id=update.message.chat_id, 
                message_id=update.message.message_id + 1
            )
        except Exception:
            pass 
    await show_main_menu(update, context)

#БАЗА-ЗНАНИЙ И ЗАЯВКИ
async def handle_callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    bot = context.bot
    photo_id = context.user_data.get(PHOTO_ID_KEY, START_PHOTO_ID)
    
    if data == CB_MENU:
        await show_main_menu(update, context, message_id=message_id)
        return
        
    elif data == CB_KNOWLEDGE:
        
        caption_text = (
            "📖 **БАЗА\\-ЗНАНИЙ**\n\n"
            "Здесь вы найдете все необходимые инструкции и ответы на часто задаваемые вопросы\\." 
        )
        
        knowledge_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➡️ Перейти в БАЗУ-ЗНАНИЙ", url="https://transibvpn-baza-znanii.gitbook.io/book/")],
            [InlineKeyboardButton("🔙 Вернуться в главное меню", callback_data=CB_MENU)]
        ])
        
        await bot.edit_message_media(
            chat_id=chat_id, 
            message_id=message_id,
            media=InputMediaPhoto(
                media=photo_id,
                caption=caption_text,
                parse_mode=ParseMode.MARKDOWN_V2
            ),
            reply_markup=knowledge_keyboard 
        )
        
    elif data == CB_STATUS:
        
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(
                media=photo_id,
                caption=escape_markdown_v2("🖥 Запускаю проверку статуса... Это займет несколько секунд."),
                parse_mode=ParseMode.MARKDOWN_V2
            ),
            reply_markup=get_return_to_main_button()
        )

        status_results = []
        for name, address in TARGET_SERVERS.items():
            result = ping_server(address)
            status_results.append(f"• *{escape_markdown_v2(name)}*: {escape_markdown_v2(result)}")
        
        status_message = "🖥 **РЕЗУЛЬТАТ ПРОВЕРКИ СТАТУСА**\n\n"
        status_message += "Проверено: " + escape_markdown_v2(", ".join(TARGET_SERVERS.keys())) + "\n\n"
        status_message += "\n".join(status_results)
        
        await bot.edit_message_media(
            chat_id=chat_id, 
            message_id=message_id,
            media=InputMediaPhoto(
                media=photo_id,
                caption=status_message,
                parse_mode=ParseMode.MARKDOWN_V2
            ),
            reply_markup=get_return_to_main_button()
        )

    elif data == CB_SUBMIT:
        user_id = query.from_user.id
        USER_STATE[user_id] = 'AWAITING_CATEGORY'
        
        keyboard = [
            [InlineKeyboardButton(text, callback_data=key)] 
            for key, text in CATEGORIES.items()
        ]
        keyboard.append([InlineKeyboardButton("🔙 Вернуться в главное меню", callback_data=CB_MENU)])
        
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(
                media=photo_id,
                caption="📝 **Отправка заявки**\n\nВыберите категорию вашей проблемы:",
                parse_mode=ParseMode.MARKDOWN
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data in CATEGORIES.keys():
        await handle_category_selection(update, context)


async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    category_key = query.data
    photo_id = context.user_data.get(PHOTO_ID_KEY, START_PHOTO_ID)
    
    if USER_STATE.get(user_id) != 'AWAITING_CATEGORY':
        await query.answer("Пожалуйста, начните диалог с 'Отправить заявку'.")
        return
    
    selected_category_text = CATEGORIES.get(category_key, "Неизвестная категория")
    USER_CATEGORY[user_id] = selected_category_text
    

    await query.message.edit_media(
        media=InputMediaPhoto(
            media=photo_id,
            caption=f"✅ Выбрана категория: **{selected_category_text}**.",
            parse_mode=ParseMode.MARKDOWN
        ),
        reply_markup=None 
    )
    
    instruction_text = (
        "Теперь, пожалуйста, опишите вашу проблему текстом."
    )
    back_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Вернуться к категориям", callback_data=CB_SUBMIT)]
    ])
    
    await context.bot.send_message(
        chat_id=user_id,
        text=instruction_text,
        reply_markup=back_keyboard 
    )
    
    USER_STATE[user_id] = 'AWAITING_PROBLEM'
    await query.answer() 


async def submit_problem_to_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    user = update.effective_user
    user_id = user.id
    
    if USER_STATE.get(user_id) != 'AWAITING_PROBLEM':
        if update.message and update.message.text and update.message.text != '/start':
             await update.message.reply_text("Пожалуйста, воспользуйтесь командой /start для вызова главного меню.")
        return    
    category = USER_CATEGORY.get(user_id, "Категория не указана")
    
    user_mention = f"@{user.username}" if user.username else "нет username"
    header = f"🚨 **НОВАЯ ЗАЯВКА** 🚨\n\n"
    header += f"**Категория:** `{category}`\n"
    header += f"**От пользователя:** `{user_mention}` \\(ID: `{user.id}`\\)\n\n" 
    
    try:
        if update.message.reply_to_message and \
           update.message.reply_to_message.reply_markup and \
           update.message.reply_to_message.reply_markup.inline_keyboard and \
           update.message.reply_to_message.reply_markup.inline_keyboard[0][0].callback_data == CB_SUBMIT:
            try:
                await update.message.reply_to_message.delete()
            except Exception:
                pass 
                
        if update.message.text:
            problem_text_safe = escape_markdown_v2(update.message.text)
            full_text = header + f"**Текст проблемы:**\n{problem_text_safe}"
            
            await context.bot.send_message(
                chat_id=SUPPORT_CHAT_ID,
                text=full_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
        elif update.message.photo or update.message.video or update.message.document:
            caption_text = header + f"**Описание:**\n{escape_markdown_v2(update.message.caption or 'Нет описания')}"

            await update.message.copy(
                chat_id=SUPPORT_CHAT_ID,
                caption=caption_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )

        else:
            raise ValueError("Неподдерживаемый тип сообщения для заявки.")


        await update.message.reply_text("🎉 Ваша заявка принята. Ожидайте ответа в течении часа!")
        await show_main_menu(update, context) 
        
    except Exception as e:
        print(f"Ошибка при пересылке заявки: {e}")
        await update.message.reply_text("Произошла ошибка при регистрации. Пожалуйста, попробуйте снова!")
        
    USER_STATE.pop(user_id, None)
    USER_CATEGORY.pop(user_id, None)


#КОД ДЛЯ ПОЛУЧЕНИЯ ID КАРТИНОК 
# async def handle_photo(update, context):

#      photo_info = update.message.photo
    
#      print("--- Получена фотография ---")
#      print(photo_info)
#      print("---------------------------")
    
#      if photo_info:
#          file_id = photo_info[-1].file_id
#          await update.message.reply_text(
#              f"Я получил ваше фото. Его File ID (для повторного использования): \n`{file_id}`",
#              parse_mode=telegram.constants.ParseMode.MARKDOWN
#          )

#КОД ЗАПУСКА БОТА И ФУНКЦИЙ
def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CallbackQueryHandler(handle_callback_menu))
    # application.add_handler(MessageHandler(filters.PHOTO, handle_photo)) ДЛЯ ID КАРТИНОК
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND, 
        submit_problem_to_support
    ))
    
    print("Ну чё давай, проверяй...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()