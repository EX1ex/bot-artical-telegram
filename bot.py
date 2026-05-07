import json
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import telegram

ADMIN_ID = 000000000   
TOKEN = "your_bot_token"  
ARTICLES_FILE = "articles.json"
PAGE_SIZE = 3  
MESSAGE_TIMEOUT = 3

user_states = {}
edit_states = {}

def load_articles():
    if os.path.exists(ARTICLES_FILE):
        with open(ARTICLES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_articles(articles):
    with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)

def split_message(text, max_length=4096):
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

def is_admin(user_id):
    return user_id == ADMIN_ID

def get_articles_keyboard(page=0, action="select", show_back=True, back_to=""):
    articles = load_articles()
    article_list = list(articles.keys())
    total_pages = (len(article_list) + PAGE_SIZE - 1) // PAGE_SIZE
    
    if total_pages == 0:
        if show_back:
            return [[InlineKeyboardButton("🔙 رجوع", callback_data=f"back_to_{back_to}")]], 0, 0
        return None, 0, 0
    
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current_articles = article_list[start:end]
    
    keyboard = []
    row = []
    for article in current_articles:
        display_name = article[:20] + "..." if len(article) > 20 else article
        row.append(InlineKeyboardButton(display_name, callback_data=f"{action}_article_{article}"))
        if len(row) == 1:
            keyboard.append(row)
            row = []
    
    nav_buttons = []
    if page > 0: nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"page_{action}_{page-1}"))
    if page < total_pages - 1: nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"page_{action}_{page+1}"))
    if nav_buttons: keyboard.append(nav_buttons)
    
    if show_back: keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"back_to_{back_to}")])
    return keyboard, page, total_pages

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("المقالات", callback_data="show_articles")]]
    await update.message.reply_text("اختر أحد المقالات التالية:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    keyboard = [
        [InlineKeyboardButton("تعديل مقالات", callback_data="admin_edit")],
        [InlineKeyboardButton("حذف مقالات", callback_data="admin_delete")],
        [InlineKeyboardButton("إضافة مقالة", callback_data="admin_add")]
    ]
    await update.message.reply_text("واجهة التحكم:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("back_to_"):
        target = data.replace("back_to_", "")
        if target == "main":
            await query.edit_message_text("اختر أحد المقالات:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("المقالات", callback_data="show_articles")]]))
        elif target == "admin":
            kb = [[InlineKeyboardButton("تعديل", callback_data="admin_edit")], [InlineKeyboardButton("حذف", callback_data="admin_delete")], [InlineKeyboardButton("إضافة", callback_data="admin_add")]]
            await query.edit_message_text("واجهة التحكم:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data == "show_articles":
        kb, p, t = get_articles_keyboard(0, "view", True, "main")
        await query.edit_message_text("اختر المقالة:", reply_markup=InlineKeyboardMarkup(kb))
    
    elif data.startswith("view_article_"):
        name = data.replace("view_article_", "")
        arts = load_articles()
        if name in arts:
            parts = split_message(arts[name])
            await query.edit_message_text(parts[0], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]))
            for p in parts[1:]: await query.message.reply_text(p)

    elif data == "admin_add" and is_admin(user_id):
        user_states[user_id] = "waiting_for_name"
        await query.edit_message_text("أرسل اسم المقالة الجديدة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]]))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if user_id in user_states and user_states[user_id] == "waiting_for_name":
        user_states[user_id] = {"name": text, "state": "waiting_for_content"}
        await update.message.reply_text(f"تم استقبال الاسم: {text}\nالآن أرسل محتوى المقالة:")
    elif user_id in user_states and isinstance(user_states[user_id], dict) and user_states[user_id]["state"] == "waiting_for_content":
        name = user_states[user_id]["name"]
        arts = load_articles()
        arts[name] = text
        save_articles(arts)
        del user_states[user_id]
        await update.message.reply_text(f"✅ تم حفظ المقالة: {name}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
