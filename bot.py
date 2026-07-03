import os
import logging
import time
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)

import database
import timer
import pomodoro

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Memory fallback storage tracking for stopwatches & premium concurrent paths
USER_STOPWATCHES = {}
USER_POMODOROS = {}

def main_menu():
    keyboard = [
        [InlineKeyboardButton("⏱ Stopwatch", callback_data="nav_stopwatch"),
         InlineKeyboardButton("⏳ Countdown", callback_data="nav_countdown")],
        [InlineKeyboardButton("🍅 Pomodoro", callback_data="nav_pomo"),
         InlineKeyboardButton("⏰ Quick Timers", callback_data="nav_quick")],
        [InlineKeyboardButton("📊 My Statistics", callback_data="nav_stats"),
         InlineKeyboardButton("⚙️ Settings", callback_data="nav_settings")],
        [InlineKeyboardButton("❓ Help", callback_data="nav_help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "👋 Welcome to *TimeTrack Bot*!\n"
        "Your personal productivity assistant for timers, stopwatches, and focused work.\n\n"
        "⏱ Start and manage stopwatches\n"
        "⏳ Create custom countdown timers\n"
        "🍅 Use the Pomodoro technique for focused study or work\n"
        "📊 Track your productivity statistics\n\n"
        "Choose an option below to get started."
    )
    if update.message:
        await update.message.reply_text(welcome, reply_markup=main_menu(), parse_mode="Markdown")

async def menu_routing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    chat_id = query.message.chat_id
    
    if query.data == "nav_stopwatch":
        if uid not in USER_STOPWATCHES:
            USER_STOPWATCHES[uid] = timer.Stopwatch()
        sw = USER_STOPWATCHES[uid]
        txt = f"⏱ *Stopwatch Mode*\n\nElapsed Time: `{sw.get_time_string()}`"
        kb = [
            [InlineKeyboardButton("▶️ Start / Resume", callback_data="sw_start"),
             InlineKeyboardButton("⏸ Pause", callback_data="sw_pause")],
            [InlineKeyboardButton("🔄 Reset", callback_data="sw_reset"),
             InlineKeyboardButton("🔙 Menu", callback_data="nav_main")]
        ]
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif query.data.startswith("sw_"):
        sw = USER_STOPWATCHES.get(uid, timer.Stopwatch())
        action = query.data.split("_")[1]
        if action == "start": sw.start()
        elif action == "pause": sw.pause()
        elif action == "reset": sw.reset()
        USER_STOPWATCHES[uid] = sw
        
        kb = [
            [InlineKeyboardButton("▶️ Start / Resume", callback_data="sw_start"),
             InlineKeyboardButton("⏸ Pause", callback_data="sw_pause")],
            [InlineKeyboardButton("🔄 Reset", callback_data="sw_reset"),
             InlineKeyboardButton("🔙 Menu", callback_data="nav_main")]
        ]
        await query.edit_message_text(f"⏱ *Stopwatch Mode*\n\nElapsed Time: `{sw.get_time_string()}`", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif query.data == "nav_countdown":
        await query.edit_message_text("⏳ Send a text message defining your custom countdown duration.\nExamples: `5 minutes`, `45 seconds`, `1 hour 30 minutes`.\n\n*Premium Mode active:* You can assign a custom label by separating it with a comma (e.g., `10 minutes, Study`).", parse_mode="Markdown")
        context.user_data['action'] = 'expecting_timer_input'

    elif query.data == "nav_quick":
        times = [1, 5, 10, 15, 25, 30, 45, 60]
        kb = [[InlineKeyboardButton(f"⏱ {t} Min", callback_data=f"qtimer_{t*60}")] for t in times]
        kb.append([InlineKeyboardButton("🔙 Menu", callback_data="nav_main")])
        await query.edit_message_text("⏰ *Quick Timers Selection Menu:*", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("qtimer_"):
        secs = int(query.data.split("_")[1])
        await start_countdown_job(secs, chat_id, uid, "Quick Timer", context)
        await query.edit_message_text(f"✅ Timer started successfully for {secs // 60} minutes!")

    elif query.data == "nav_pomo":
        pomo = USER_POMODOROS.setdefault(uid, pomodoro.PomodoroSession(uid))
        txt = f"🍅 *Pomodoro Control Panel*\n\nCurrent State: `{pomo.state}`\nCompleted Cycles: `{pomo.cycle_count}`"
        kb = [[InlineKeyboardButton("🚀 Start Focus Session", callback_data="pomo_next")],
              [InlineKeyboardButton("🔙 Menu", callback_data="nav_main")]]
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif query.data == "pomo_next":
        pomo = USER_POMODOROS.get(uid)
        state_name, minutes = pomo.next_state()
        await start_countdown_job(minutes * 60, chat_id, uid, f"Pomodoro [{state_name}]", context, is_pomo=True)
        await query.edit_message_text(f"🍅 Pomodoro transition complete! Started context: *{state_name}* for {minutes} minutes.", parse_mode="Markdown")

    elif query.data == "nav_stats":
        t, p, f = await database.get_stats(uid)
        stats_msg = f"📊 *Your Metrics Overview:*\n\nTotal Timers Spawned: `{t}`\nCompleted Pomodoros: `{p}`\nAggregated Focus Time: `{f} minutes`"
        await query.edit_message_text(stats_msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="nav_main")]]), parse_mode="Markdown")

    elif query.data == "nav_help":
        help_txt = "❓ *TimeTrack Bot Help Manual*\n\n- /start: Access the dashboard context panel.\n- Stopwatch: Track elapsed time intervals in high resolution.\n- Countdown: Input raw natural language time formats to schedule text alerts."
        await query.edit_message_text(help_txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="nav_main")]]))

    elif query.data == "nav_main":
        await query.edit_message_text("Choose an option below to get started.", reply_markup=main_menu())

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text
    
    if context.user_data.get('action') == 'expecting_timer_input':
        label = "Custom Timer"
        if "," in text:
            time_part, label_part = text.split(",", 1)
            text = time_part.strip()
            label = label_part.strip()
            
        secs = timer.parse_time_input(text)
        if secs <= 0:
            await update.message.reply_text("❌ Could not interpret that time format. Please try again.")
            return
            
        await start_countdown_job(secs, chat_id, uid, label, context)
        context.user_data['action'] = None
        await update.message.reply_text(f"⏳ Timer started for *{text}* [Label: {label}]!", parse_mode="Markdown")
    else:
        await start(update, context)

async def start_countdown_job(seconds: int, chat_id: int, user_id: int, label: str, context: ContextTypes.DEFAULT_TYPE, is_pomo: bool = False):
    timer_id = f"{user_id}_{int(time.time())}"
    expiry = time.time() + seconds
    
    await database.save_active_timer(timer_id, user_id, chat_id, expiry, label)
    await database.increment_stat(user_id, "total_timers", 1)
    
    context.job_queue.run_once(
        timeout_callback, 
        seconds, 
        chat_id=chat_id, 
        user_id=user_id, 
        name=timer_id, 
        data={"label": label, "is_pomo": is_pomo, "secs": seconds}
    )

async def timeout_callback(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await database.remove_active_timer(job.name)
    
    msg = f"⏰ *Time's up!*\nYour countdown for *{job.data['label']}* has completed."
    await context.bot.send_message(chat_id=job.chat_id, text=msg, parse_mode="Markdown")
    
    if job.data.get('is_pomo'):
        await database.increment_stat(job.user_id, "total_pomo_sessions", 1)
        await database.increment_stat(job.user_id, "total_focus_time", job.data['secs'] // 60)

def main():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(database.init_db())

    if not TOKEN:
        print("Fatal error: Missing BOT_TOKEN")
        return
        
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(menu_routing, pattern="^nav_|^sw_|^qtimer_|^pomo_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    print("TimeTrack Bot initialized successfully...")
    application.run_polling()

if __name__ == '__main__':
    main()

