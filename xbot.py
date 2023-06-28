from distutils.log import error
import imp
from urllib import response
import telegram
import logging
import sqlite3
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes, ApplicationBuilder, CallbackQueryHandler, ConversationHandler
import requests
import configparser
from telegram import ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
import json
from persiantools.jdatetime import JalaliDate, JalaliDateTime
import random
import pytz    


config_obj = configparser.ConfigParser()
config_obj.read("configfile.ini")
payment_info = config_obj["payment_info"]
panelparam = config_obj["panel_info"]
botinfo = config_obj["bot_info"]
priceinfo = config_obj["price_info"]
# set your parameters for the database connection URI using the keys from the configfile.ini
TOKEN = botinfo["TOKEN"]
CHANNEL_ID = botinfo["CHANNEL_ID"]
addr = panelparam["addr"]
port = int(panelparam["port"])
apiaddr = panelparam["apiaddr"]
welcome_text = botinfo["welcome_text"]
udp = panelparam["udp"]
admin_id =  int(botinfo["adminid"])
DB_FILE =  botinfo["dbfile"]
pay_method = payment_info["pay_method"]



ad_cost = int(priceinfo["ad_cost"])
#تعداد کاربران روی یک سرور
usersnum =int( priceinfo["usersnum"])
#هزینه سرور
server_cost = int(priceinfo["server_cost"])
#قیمت به ازای یک گیگابایت ترافیک به ریال
price_in_GB = int(priceinfo["price_in_GB"])
#حداقل سود مورد انتظار به درصد
min_profit = int(priceinfo["min_profit"])



logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

bot = telegram.Bot("TOKEN")

# اتصال به دیتابیس SQLite
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# ساخت جدول users در دیتابیس SQLite
c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                join_date TEXT,
                is_admin INTEGER,
                wallet INTEGER
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
def save_user_data(user_id, username, join_date, is_admin, wallet):
    c.execute('INSERT OR REPLACE INTO users (user_id, username, join_date, is_admin, wallet) VALUES (?, ?, ?, ?, ?)', (user_id, username, join_date, is_admin, wallet))
    conn.commit()

def update_wallet(userid, new_value):
    try:
        sql_update_query = """ Update users set wallet = ? where user_id = ? """
        data = (new_value, userid)
        
        c.execute(sql_update_query, data)
    except sqlite3.Error as error:
        pass



# دکمه بازگشت
back_button = InlineKeyboardButton("بازگشت", callback_data="start")
back_key = [[back_button]]
back_reply_markup = InlineKeyboardMarkup(back_key)

#password gen
def password_gen():
    list_of_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890!@#$%^&*()"  
  
    # using the random.sample() method to return a list of randomly selected characters from the list of characters.  
    selected_char = random.sample(list_of_chars, 12)  
  
    # converting the list into the string  
    pass_str = "".join(selected_char)  
      
    # returning the generated password string  
    return pass_str 

# جداسازی ه رقم 
def rial_nums(nums):
    num = str(nums)
    new_num = ""
    for i in range(len(num)):
        if i % 3 == 0 and i != 0:
            new_num += ","
        new_num += num[len(num)-1-i]
    
    return (new_num[::-1])
# تابع برای نمایش اطلاعات کاربر
async def show_user_info(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if row:
        username = row[1]
        join_date = row[2]
        Jalali_join_date = JalaliDateTime.fromtimestamp(float(join_date), pytz.timezone("Asia/Tehran")).strftime("%Y/%m/%d")
        is_admin = row[3]
        wallet = row[4]
        persian_wallet = rial_nums(wallet)
        if is_admin == 1 :
            role = 'مدیر'
        else:
            role = 'کاربر'
        message_text = f'نام کاربری: @{username}\nشناسه کاربر: {user_id}\nتاریخ عضویت: {Jalali_join_date}\nنوع عضویت: {role}\nموجودی کیف پول شما: {persian_wallet} ریال'
    else:
        message_text = 'شما هنوز در ربات عضو نشده‌اید.'
    
     
    user_info_message = update.message.reply_text(message_text, reply_markup=back_reply_markup)
    await user_info_message

#check for user exist
def check_user_reg(user_id):
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if row:
        return True
    else:
        return False

# موجودی کیف پول
def wallet_info(user_id):
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if row:
        wallet = row[4]
        return wallet
    else:
        return False


# تابع برای پاسخ به دکمه نمایش اطلاعات کاربر
async def button_callback(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query.answer()
    await show_user_info(query)


#  تعریف دکمه‌های منو مدیر
adminmenu_keyboard = [
    [
        InlineKeyboardButton('افزودن کاربر', callback_data="add_user"),
        InlineKeyboardButton('حذف کاربر', callback_data="del_user"),
        InlineKeyboardButton('ویرایش کاربر', callback_data="edit_user")
    ]
    ,[
        InlineKeyboardButton('فعالسازی کاربر', callback_data="deactive_user"),
        InlineKeyboardButton('غیر فعالسازی کاربر', callback_data="active_user")]
    ]
adminmenu_markup = InlineKeyboardMarkup(adminmenu_keyboard)


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
     
    
    if user_id == admin_id: 
        is_admin = 1
        await context.bot.send_message(chat_id=update.effective_chat.id, text='مدیر عزیز به چرچی بات خوش آمدید!', reply_markup=adminmenu_markup)
    else:
        is_admin = 0
        # ارسال پیام خوش‌آمدگویی
        #join_channel_markup = telegram.InlineKeyboardMarkup([join_channel_button])
        await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text, reply_markup=menu_markup)
    
    if check_user_reg(user_id) == False:
        join_date = update.message.date.timestamp()
        wallet = 0
        save_user_data(user_id, username, join_date, is_admin, wallet)   
    
    #دریافت رسید از کاربر
    async def photo(update, context: ContextTypes.DEFAULT_TYPE) -> int:

        """Stores the photo and wight for admin confirm."""

        user = update.message.from_user

        photo_file = await update.message.photo[-1].get_file()

        await photo_file.download_to_drive("user_receipt.jpg")

        logger.info("Photo of %s: %s", user.first_name, "user_receipt.jpg")

        await update.message.reply_text(

            "با تشکر از پرداخت شما تا لحظانی دیگر یکی از ادمین ها سفارش شما را تایید میکند و مشخصات سرویس برای شما ارسال میگردد."

        )

        with open(photo_path, "rb") as photo:
            await bot.send_photo(chat_id=admin_id, photo=photo, caption="کاربر مبلغ ریال واریز و رسید آنرا ارسال نموده")

#تابع پرداخت
#def peymentnow(data):
    #if pay_method ==1:
        
#    elif == 2:
        #
#    else:


#تابع پرداخت کارت به کارت
#def carttocart(data):
    

#تابع خرید سرویس
traffic_STATE, EXP_STATE, MUTIUSER_STATE, USESRNAME_STATE = range(4)
# Define a dictionary to store the user's answers
user_data = {}

async def buy(update, context: ContextTypes.DEFAULT_TYPE) -> int:

    """Stores the info about the user and ends the conversation."""
    await update.message.reply_text('حجم مورد نیاز خود را وارد کنید:', reply_markup=back_reply_markup,)
    


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
    await update.message.reply_text('یک نام کاربری وارد کنید:')

    return USESRNAME_STATE


def button(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query



#تابع برای ایجاد کاربر جدید
def add_user(kart):
    url = apiaddr+"&method=adduser"
    response = requests.post(url,kart)
    return response.status_code

#تابع حذف کاربر
def del_user(username):
    url = apiaddr+"&method=deleteuser"
    user_name = {"username": username}
    response = requests.post(url,user_name)
    return response.status_code


#تابع ویرایش کاربر
def edit_user(kart):
    url = apiaddr+"&method=edituser"
    response = requests.post(url,kart)
    return response.status_code



#تابع غیرفعالسازی کاربر
def deactive_user(username):
    url = apiaddr+"&method=deactiveuser"
    user_name = {"username": username}
    response = requests.post(url, user_name)
    return response.status_code
    

#تابع فعالسازی کاربر
def actiate_user(username):
    url = apiaddr+"&method=activeuser"
    user_name = {"username": username}
    response = requests.post(url, user_name)
    return response.status_code


        
async def username(update, context: ContextTypes.DEFAULT_TYPE):
    # Save the user's answer and display all the answers
    user_data['username'] = update.message.text
    user_id = update.effective_user.id
    kart = {
        "username": user_data["username"],
        "password": password_gen,
        "multiuser": user_data["multiuser"],
        "traffic": user_data['traffic'],
        "type_traffic": "gb",
        "expdate": date_calc(user_data["expdate"]),
    }
    service_price = price_calc(user_data['traffic'], user_data["expdate"], user_data["multiuser"])
    #دکمه پرداخت
     
    keyboard = [[InlineKeyboardButton("پرداخت", callback_data='pay')]]
    pay_reply_markup = InlineKeyboardMarkup(keyboard)
    wallet_balance = wallet_info(user_id)
    if wallet_balance >= service_price:

        adduser_status = add_user(kart)
        if adduser_status == 200:
            new_value = (wallet_balance) - (service_price)
            pfw = update_wallet(user_id, new_value)
            print (new_value)
            await update.message.reply_text(f'از خرید شما ممنونیم!\n\n'
                                f'حجم بسته : {user_data["traffic"]} گیگابایت\n'
                                f'مدت اعتبار: {user_data["expdate"]} روز\n'
                                f'تعداد کاربران: {user_data["multiuser"]} کاربر \n'
                                f'نام کاربری: {user_data["username"]}\n'
                                f'کلمه عبور: {password_gen}\n'
                                f'هزینه سرویس: {service_price} ریال\n'
                                f'مانده حساب کیف پول:{new_value}', reply_markup=pay_reply_markup)
        else:
            await update.message.reply_text('مشکلی در ایجاد کاربر بوجود آمد با پشتیبانی تماس بگیرید', areply_markup = back_button )
    else :
        await update.message.reply_text('موجودی کیف پول شما برای این سرویس کافی نمیباشد ابتدا حساب خود را شارژ کنید سپس مجدد اقدام به خرید نمایید',reply_markup= back_button)
    data = {
        'amount': service_price,
    }

    headers = {'Content-type': 'application/json'}
    pay_url = 'http://localhost:5000/payment'
    #response = requests.post(pay_url, data=json.dumps(data), headers=headers)

    #print(response.json())

     
    
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
   #application.add_handler(CallbackQueryHandler(button_callback))
   application.add_handler(CallbackQueryHandler(start, pattern='start'))
   application.add_handler(MessageHandler(filters.Regex('حساب کاربری'), show_user_info))
   #application.add_handler(MessageHandler(filters.Regex('back'), start))
   #application.add_handler(MessageHandler(filters.Regex('pay'), peymentnow))
   conv_handler = ConversationHandler(

        entry_points=[MessageHandler(filters.Regex('خرید سرویس'), buy)],

        states={
            traffic_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, traffic)],

            EXP_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, EXPDATE)],

            MUTIUSER_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, multiuser)],

            USESRNAME_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, username)]

        },

        fallbacks=[CommandHandler("cancel", cancel)],

    )


   application.add_handler(conv_handler)
   application.run_polling()	
