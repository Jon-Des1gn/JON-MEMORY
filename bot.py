import os, asyncio, logging, sqlite3, re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
load_dotenv(); TOKEN=os.getenv('BOT_TOKEN'); DB='data/jon_memory.db'
logging.basicConfig(level=logging.INFO); bot=Bot(TOKEN); dp=Dispatcher(); scheduler=AsyncIOScheduler()
PLANS={'free':('🆓 FREE','100','10'),'pro':('⚡ PRO','2 000','100'),'max':('👑 MAX','10 000','∞')}
def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init_db():
 c=conn(); c.executescript('''CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,plan TEXT NOT NULL DEFAULT 'free',created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,text TEXT,created_at TEXT);CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,text TEXT,remind_at TEXT,done INTEGER DEFAULT 0);'''); c.commit(); c.close()
def user(uid):
 c=conn(); c.execute('INSERT OR IGNORE INTO users VALUES(?,?,?)',(uid,'free',datetime.now().isoformat())); c.commit(); c.close()
def menu(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🧠 Память',callback_data='memory'),InlineKeyboardButton(text='⏰ Напоминания',callback_data='reminders')],[InlineKeyboardButton(text='👤 Профиль',callback_data='profile'),InlineKeyboardButton(text='💎 Тарифы',callback_data='plans')],[InlineKeyboardButton(text='❓ Помощь',callback_data='help')]])
@dp.message(CommandStart())
async def start(m):
 user(m.from_user.id); await m.answer('🧠 <b>JON MEMORY</b>\n\nТвоя личная память в Telegram.\n\nПросто напиши:\n• <i>Запомни, мой проект называется JON AI</i>\n• <i>Напомни через 2 часа проверить сайт</i>\n\nЯ сохраню информацию и напомню в нужный момент.',reply_markup=menu())
@dp.message(Command('menu'))
async def cmdmenu(m): user(m.from_user.id); await m.answer('🧠 <b>JON MEMORY</b>\nВыбери действие:',reply_markup=menu())
@dp.callback_query(F.data=='plans')
async def plans(q):
 await q.message.edit_text('💎 <b>ТАРИФЫ JON MEMORY</b>\n\n🆓 <b>FREE</b> — 0 ₽\n• 100 воспоминаний\n• 10 напоминаний в месяц\n• текстовые записи\n\n⚡ <b>PRO</b> — 49 ₽/мес · 149 ₽/год\n• 2 000 воспоминаний\n• 100 напоминаний/мес\n• умный поиск\n• повторяющиеся напоминания\n• голосовые сообщения\n\n👑 <b>MAX</b> — 79 ₽/мес · 199 ₽/год\n• 10 000 воспоминаний\n• безлимитные напоминания\n• голос → память\n• голосовые ответы\n• файлы и документы\n• расширенный поиск\n• новые функции первыми\n\n💳 Оплату подключим следующим этапом.',reply_markup=menu()); await q.answer()
@dp.callback_query(F.data=='profile')
async def profile(q):
 user(q.from_user.id); c=conn(); u=c.execute('SELECT * FROM users WHERE user_id=?',(q.from_user.id,)).fetchone(); mc=c.execute('SELECT COUNT(*) n FROM memories WHERE user_id=?',(q.from_user.id,)).fetchone()['n']; rc=c.execute('SELECT COUNT(*) n FROM reminders WHERE user_id=? AND done=0',(q.from_user.id,)).fetchone()['n']; c.close(); p=PLANS[u['plan']]; await q.message.edit_text(f"👤 <b>Твой JON MEMORY</b>\n\nТариф: {p[0]}\n🧠 Память: {mc} / {p[1]}\n⏰ Активных напоминаний: {rc}\n\n💎 /plans — тарифы",reply_markup=menu()); await q.answer()
@dp.callback_query(F.data=='memory')
async def memory(q):
 user(q.from_user.id); c=conn(); rows=c.execute('SELECT text FROM memories WHERE user_id=? ORDER BY id DESC LIMIT 10',(q.from_user.id,)).fetchall(); c.close(); text='🧠 <b>Моя память</b>\n\n'+('\n'.join('• '+r['text'] for r in rows) if rows else 'Пока пусто. Напиши: «Запомни, ...»'); await q.message.edit_text(text,reply_markup=menu()); await q.answer()
@dp.callback_query(F.data=='reminders')
async def reminders(q):
 user(q.from_user.id); c=conn(); rows=c.execute('SELECT text,remind_at FROM reminders WHERE user_id=? AND done=0 ORDER BY remind_at LIMIT 10',(q.from_user.id,)).fetchall(); c.close(); text='⏰ <b>Напоминания</b>\n\n'+('\n'.join(f"• {r['text']} — {datetime.fromisoformat(r['remind_at']).strftime('%d.%m %H:%M')}" for r in rows) if rows else 'Активных напоминаний нет.'); await q.message.edit_text(text,reply_markup=menu()); await q.answer()
@dp.callback_query(F.data=='help')
async def help_(q): await q.message.edit_text('❓ <b>Как пользоваться</b>\n\n🧠 «Запомни, мой проект называется JON AI»\n⏰ «Напомни через 2 часа проверить сайт»\n\n📋 /menu',reply_markup=menu()); await q.answer()
def add_memory(uid,t):
 c=conn(); c.execute('INSERT INTO memories(user_id,text,created_at) VALUES(?,?,?)',(uid,t,datetime.now().isoformat())); c.commit(); c.close()
def add_rem(uid,t,when):
 c=conn(); cur=c.execute('INSERT INTO reminders(user_id,text,remind_at) VALUES(?,?,?)',(uid,t,when.isoformat())); rid=cur.lastrowid; c.commit(); c.close(); return rid
async def fire(rid):
 c=conn(); r=c.execute('SELECT * FROM reminders WHERE id=? AND done=0',(rid,)).fetchone()
 if r: await bot.send_message(r['user_id'],f"🔔 <b>JON MEMORY</b>\n\nТы просил напомнить:\n📝 {r['text']}"); c.execute('UPDATE reminders SET done=1 WHERE id=?',(rid,)); c.commit()
 c.close()
@dp.message()
async def text(m):
 user(m.from_user.id); t=(m.text or '').strip(); low=t.lower(); match=re.search(r'через\s+(\d+)\s+(минут\w*|час\w*|дн\w*)',low)
 if low.startswith('напомни') and match:
  n=int(match.group(1)); unit=match.group(2); delta=timedelta(minutes=n) if unit.startswith('минут') else timedelta(hours=n) if unit.startswith('час') else timedelta(days=n); rt=re.sub(r'^напомни\s+через\s+\d+\s+\S+\s*','',t,flags=re.I).strip() or 'Проверить задачу'; when=datetime.now()+delta; rid=add_rem(m.from_user.id,rt,when); scheduler.add_job(fire,'date',run_date=when,args=[rid],id=f'r{rid}',replace_existing=True); await m.answer(f'⏰ <b>Готово!</b>\n\nНапомню: <b>{rt}</b>\n🕐 {when.strftime("%d.%m.%Y в %H:%M")}'); return
 if low.startswith('запомни'):
  x=t[len('запомни'):].strip(' :—-');
  if x: add_memory(m.from_user.id,x); await m.answer('🧠 <b>Запомнил.</b>\n\n'+x)
  else: await m.answer('🧠 Напиши после «Запомни», что сохранить.')
  return
 if low.startswith('что ты помнишь') or low.startswith('моя память'):
  c=conn(); rows=c.execute('SELECT text FROM memories WHERE user_id=? ORDER BY id DESC LIMIT 10',(m.from_user.id,)).fetchall(); c.close(); await m.answer('🧠 <b>Я помню:</b>\n\n'+('\n'.join('• '+r['text'] for r in rows) if rows else 'Пока ничего не сохранено.')); return
 await m.answer('🧠 Я готов запоминать и напоминать.\n\nПопробуй:\n«Запомни, мой проект называется JON AI»\n«Напомни через 2 часа проверить сайт»',reply_markup=menu())
async def main():
 if not TOKEN: raise RuntimeError('BOT_TOKEN не найден')
 init_db(); scheduler.start(); await dp.start_polling(bot)
if __name__=='__main__': asyncio.run(main())
