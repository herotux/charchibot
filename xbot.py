import telegram
import logging
import sqlite3
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes, ApplicationBuilder, CallbackQueryHandler, ConversationHandler
import requests
import configparser
from telegram import ReplyKeyboardRemove
from datetime import datetime, timedelta


config_obj = configparser.ConfigParser()
config_obj.read("configfile.ini")
panelparam = config_obj["panel_info"]
botinfo = config_obj["bot_info"]
priceinfo = config_obj["price_info"]
# set your parameters for the database connection URI using the keys from the configfile.ini
TOKEN = botinfo["TOKEN"]
CHANNEL_ID = botinfo["CHANNEL_ID"]
addr = panelparam["addr"]
port = int(panelparam["port"])
apiaddr = panelparam["apiaddr"]
udp = panelparam["udp"]
admin_id =  int(botinfo["adminid"])
DB_FILE =  botinfo["dbfile"]




ad_cost = int(priceinfo["ad_cost"])
#تعداد کاربران روی یک سرور
usersnum =int( priceinfo["usersnum"])
#هزینه سرور
server_cost = int(priceinfo["server_cost"])
#قیمت به ازای یک گیگابایت ترافیک به ریال
price_in_GB = int(priceinfo["price_in_GB"])
#حداقل سود مورد انتظار به درصد
min_profit = int(priceinfo["min_profit"])



#logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


# اتصال به دیتابیس SQLite
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# ساخت جدول users در دیتابیس SQLite
c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                join_date TEXT,
                is_admin INTEGER
            )''')
conn.commit()

def date_calc(days):
   today = datetime.today()
   new_date = today + timedelta(int(days))
   new_date_str = new_date.strftime('%Y-%m-%d')
   return new_date_str

def price_calc(traffic, expindays, multiuser):
   fixed_cost= ad_cost + server_cost
   fcu = (fixed_cost / usersnum)/30 
   inv = 1 + min_profit/100
   musr = int(multiuser)
   if multiuser == 1:
      price = (traffic * price_in_GB + fcu * expindays) * inv
   else:
      price = ((int(traffic) * price_in_GB + fcu * int(expindays)) * inv) * (musr - musr/10)
   return round(price)
# تابع برای ذخیره اطلاعات کاربر در دیتابیس SQLite
def save_user_data(user_id, username, join_date, is_admin):
    c.execute('INSERT OR REPLACE INTO users (user_id, username, join_date, is_admin) VALUES (?, ?, ?, ?)', (user_id, username, join_date, is_admin))
    conn.commit()

# تابع برای نمایش اطلاعات کاربر در پاسخ به دستور /info
async def show_user_info(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if row:
        username = row[1]
        join_date = row[2]
        is_admin = row[3]
        if is_admin == 1 :
            role = 'مدیر'
        else:
            role = 'کاربر'
        message_text = f'نام کاربری: @{username}\nتاریخ عضویت: {join_date}\nنوع عضویت: {role}'
    else:
        message_text = 'شما هنوز در ربات عضو نشده‌اید.'
    
    await update.message.reply_text(message_text)

# تابع برای پاسخ به دکمه نمایش اطلاعات کاربر
async def button_callback(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query.answer()
    
    await show_user_info(query)


# تعریف دکمه‌های منو
menu_keyboard = [['🛍 خرید سرویس'], ['افزایش موجودی'], ['حساب کاربری']]
menu_markup = telegram.ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)



#  تعریف دکمه‌های منو مدیر
adminmenu_keyboard = [['مشخصات کاربر'], ['️حذف کاربر'], ['افزودن کاربر'], ['بکاپ'], ['ویرایش کاربر']]
adminmenu_markup = telegram.ReplyKeyboardMarkup(adminmenu_keyboard, resize_keyboard=True)



# تعریف دکمه برای عضویت در کانال
join_channel_button = [telegram.InlineKeyboardButton('عضویت در کانال', url=f'https://t.me/{CHANNEL_ID}'),]
#join_channel_markup = telegram.InlineKeyboardMarkup(join_channel_button)
#join_channel_markup = telegram.InlineKeyboardMarkup([[join_channel_button]])

# تعریف دکمه‌های منو اصلی
menu_buttons = [[telegram.KeyboardButton('🛍 خرید سرویس')], [telegram.KeyboardButton('افزایش موجودی')], [telegram.KeyboardButton('حساب کاربری')]]
menu_markup = telegram.ReplyKeyboardMarkup(menu_buttons, resize_keyboard=True)


# تابع برای استارت ربات
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    join_date = update.message.date.strftime('%Y-%m-%d %H:%M:%S')
    
    
    if user_id == admin_id: 
        is_admin = 1
        await context.bot.send_message(chat_id=update.effective_chat.id, text='مدیر عزیز به چرچی بات خوش آمدید!', reply_markup=adminmenu_markup)
    else:
        is_admin = 0
        # ارسال پیام خوش‌آمدگویی
        #join_channel_markup = telegram.InlineKeyboardMarkup([join_channel_button])
        await context.bot.send_message(chat_id=update.effective_chat.id, text='به چرچی بات خوش آمدید!', reply_markup=menu_markup)
    save_user_data(user_id, username, join_date, is_admin)



#تابع خرید سرویس
traffic_STATE, EXP_STATE, MUTIUSER_STATE, PASS_STATE, USESRNAME_STATE = range(5)
# Define a dictionary to store the user's answers
user_data = {}

async def buy(update, context: ContextTypes.DEFAULT_TYPE) -> int:

    """Stores the info about the user and ends the conversation."""
    await update.message.reply_text('حجم مورد نیاز خود را وارد کنید:', reply_markup=ReplyKeyboardRemove(),)
    


    return traffic_STATE

async def traffic(update, context: ContextTypes.DEFAULT_TYPE):
    # Save the user's answer and send the second question
    user_data['traffic'] = update.message.text
    await update.message.reply_text("مدت زمان بسته به روز وارد کنید")
    

    return EXP_STATE
    
async def EXPDATE(update, context: ContextTypes.DEFAULT_TYPE):
    # Save the user's answer and send the second question
    user_data['expdate'] = update.message.text
    
    await update.message.reply_text('تعداد کاربر را وارد کنید')

    return MUTIUSER_STATE

async def multiuser(update, context: ContextTypes.DEFAULT_TYPE):
    # Save the user's answer and send the third question
    user_data['multiuser'] = update.message.text
    await update.message.reply_text('رمز عبور برای سرویس را وارد کنید')

    return PASS_STATE

async def passwd(update, context: ContextTypes.DEFAULT_TYPE):
    # Save the user's answer and send the fourth question
    user_data['passwd'] = update.message.text
    await update.message.reply_text('یک نام کاربری وارد کنید:')
    return USESRNAME_STATE


async def username(update, context: ContextTypes.DEFAULT_TYPE):
    # Save the user's answer and display all the answers
    user_data['username'] = update.message.text

    url = apiaddr+"&method=adduser"
    kart = {
        "username": user_data["username"],
        "password": user_data["passwd"],
        "multiuser": user_data["multiuser"],
        "traffic": user_data['traffic'],
        "type_traffic": "gb",
        "expdate": date_calc(user_data["expdate"]),
    }
    #requests.post(url,kart)
    service_price = price_calc(user_data['traffic'], user_data["expdate"], user_data["multiuser"])
    await update.message.reply_text(f'از خرید شما ممنونیم!\n\n'
                              f'حجم بسته : {user_data["traffic"]} گیگابایت\n'
                              f'مدت اعتبار: {user_data["expdate"]} روز\n'
                              f'تعداد کاربران: {user_data["multiuser"]} کاربر \n'
                              f'کلمه عبور: {user_data["passwd"]}\n'
                              f'نام کاربری: {user_data["username"]}\n'
			      f'هزینه سرویس: {service_price} ریال')
    return ConversationHandler.END

async def cancel(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(

        "سفارش لغو شد", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END





# تابع برای بررسی عضویت کاربر در کانال
async def check_membership(update, context: ContextTypes.DEFAULT_TYPE):
   user_id = update.effective_user.id
   chat_id = update.effective_chat.id
    
   # چک کنید که آیدی کاربر عضو کانال است یا نه
   is_member = context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id).status == 'member'
    
   if is_member:
        # اگر عضو بود، منو اصلی را به او نشان دهید
      await context.bot.send_message(chat_id=chat_id, text='لطفا یکی از گزینه‌های زیر را انتخاب کنید')
   else:
      # If not a member, show the join channel button
      join_channel_markup = telegram.InlineKeyboardMarkup([[join_channel_button]])
      await context.bot.send_message(chat_id=chat_id, text='برای استفاده از ربات، لطفا در کانال عضو شوید.', reply_markup=join_channel_markup)

# Function to show the main menu
async def show_menu(update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Show the menu with desired buttons
    await context.bot.send_message(chat_id=chat_id, text='لطفا یکی از گزینه‌های زیر را انتخاب کنید:', reply_markup=menu_markup)

# Define handlers

if __name__ == '__main__':
   application = ApplicationBuilder().token(TOKEN).build()
   application.add_handler(CommandHandler('start', start))
   application.add_handler(CommandHandler('info', show_user_info))
   application.add_handler(CallbackQueryHandler(button_callback))
   application.add_handler(MessageHandler(filters.Regex('حساب کاربری'), show_user_info))
   conv_handler = ConversationHandler(

        entry_points=[MessageHandler(filters.Regex('خرید سرویس'), buy)],

        states={
            traffic_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, traffic)],

            EXP_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, EXPDATE)],

            MUTIUSER_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, multiuser)],

            PASS_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, passwd)],

            USESRNAME_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, username)]

        },

        fallbacks=[CommandHandler("cancel", cancel)],

    )


   application.add_handler(conv_handler)
   application.run_polling()	
