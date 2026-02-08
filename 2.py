from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import mysql.connector
from datetime import datetime

TOKEN = "8501388208:AAFp8CfdIoF26Ag3KjKk9SMt7vUz4r7lDaY"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="nail_bot"
)
cursor = db.cursor()

SERVICES = ["全贴", "半贴", "脚", "经典"]
user_step = {}
user_data = {}

# ========== 基本 ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💅 美甲预约管理系统\n\n"
        "/add 新增预约\n"
        "/today 今日预约\n"
        "/date 查询指定日期\n"
        "/all 列出所有预约\n"
        "/edit 修改预约\n"
        "/delete 删除预约"
    )

# ========== 新增预约 ==========

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_step[uid] = "add_date"
    user_data[uid] = {}
    await update.message.reply_text("请输入预约日期 (YYYY-MM-DD)：")

# ========== 回调按钮 ==========

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()

    if query.data.startswith("service_"):
        service = query.data.replace("service_", "")
        user_data[uid]["service"] = service
        user_step[uid] = "add_name"
        await query.edit_message_text("请输入顾客姓名：")

# ========== 文本统一处理 ==========

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    step = user_step.get(uid)

    if step == "add_date":
        try:
            datetime.strptime(text, "%Y-%m-%d")
            user_data[uid]["date"] = text
            user_step[uid] = "add_time"
            await update.message.reply_text("请输入预约时间 (如 14:30)：")
        except:
            await update.message.reply_text("❌ 日期格式错误，请输入 YYYY-MM-DD")

    elif step == "add_time":
        user_data[uid]["time"] = text

        cursor.execute("SELECT id FROM bookings WHERE date=%s AND time=%s",
                       (user_data[uid]["date"], text))
        if cursor.fetchone():
            await update.message.reply_text("⚠ 该时间已被预约，请重新输入时间：")
            return

        kb = [[InlineKeyboardButton(s, callback_data=f"service_{s}")] for s in SERVICES]
        await update.message.reply_text("请选择服务：", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "add_name":
        user_data[uid]["name"] = text
        user_step[uid] = "add_phone"
        await update.message.reply_text("请输入电话：")

    elif step == "add_phone":
        user_data[uid]["phone"] = text
        data = user_data[uid]

        sql = "INSERT INTO bookings (name, phone, service, date, time) VALUES (%s,%s,%s,%s,%s)"
        val = (data["name"], data["phone"], data["service"], data["date"], data["time"])
        cursor.execute(sql, val)
        db.commit()

        await update.message.reply_text("✅ 预约成功！")
        user_step.pop(uid)

    elif step == "query_date":
        cursor.execute("SELECT id,time,name,service FROM bookings WHERE date=%s ORDER BY time", (text,))
        rows = cursor.fetchall()

        if not rows:
            await update.message.reply_text("📭 该日期无预约")
        else:
            msg = f"📅 {text} 预约\n\n"
            for r in rows:
                msg += f"#{r[0]}  {r[1]} - {r[2]} ({r[3]})\n"
            await update.message.reply_text(msg)

        user_step.pop(uid)

    elif step == "edit_id":
        context.user_data["edit_id"] = text
        user_step[uid] = "edit_time"
        await update.message.reply_text("请输入新时间 (如 16:00)：")

    elif step == "edit_time":
        cursor.execute("UPDATE bookings SET time=%s WHERE id=%s",
                       (text, context.user_data["edit_id"]))
        db.commit()
        await update.message.reply_text("✅ 修改成功")
        user_step.pop(uid)

    elif step == "delete_id":
        cursor.execute("DELETE FROM bookings WHERE id=%s", (text,))
        db.commit()
        await update.message.reply_text("🗑 删除成功")
        user_step.pop(uid)

# ========== 功能指令 ==========

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT id,time,name,service FROM bookings WHERE date=%s ORDER BY time", (today,))
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📭 今日暂无预约")
        return

    msg = "📅 今日预约\n\n"
    for r in rows:
        msg += f"#{r[0]}  {r[1]} - {r[2]} ({r[3]})\n"
    await update.message.reply_text(msg)

async def date_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_step[update.effective_user.id] = "query_date"
    await update.message.reply_text("请输入查询日期 (YYYY-MM-DD)：")

async def all_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT id,date,time,name,service FROM bookings ORDER BY date,time")
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📭 当前无任何预约")
        return

    msg = "📋 所有预约\n\n"
    last_date = None

    for r in rows:
        if last_date != r[1]:
            msg += f"\n📅 {r[1]}\n"
            last_date = r[1]
        msg += f"#{r[0]}  {r[2]} - {r[3]} ({r[4]})\n"

    await update.message.reply_text(msg)

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await all_booking(update, context)
    user_step[update.effective_user.id] = "edit_id"
    await update.message.reply_text("\n请输入要修改的预约 ID：")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await all_booking(update, context)
    user_step[update.effective_user.id] = "delete_id"
    await update.message.reply_text("\n请输入要删除的预约 ID：")

# ========== 启动 ==========

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("today", today))
app.add_handler(CommandHandler("date", date_query))
app.add_handler(CommandHandler("all", all_booking))
app.add_handler(CommandHandler("edit", edit))
app.add_handler(CommandHandler("delete", delete))

app.add_handler(CallbackQueryHandler(callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("Bot running...")
app.run_polling()
