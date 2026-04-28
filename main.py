import asyncio
import logging
import os
import random
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ChatMemberUpdated
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# ==================== ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ====================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в .env файле!")

# Парсинг списка админов (через запятую)
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id_str.strip()) for id_str in ADMIN_IDS_STR.split(",") if id_str.strip().isdigit()]
if not ADMIN_IDS:
    print("⚠️ Внимание: ADMIN_IDS пуст или не указан в .env!")

CHANNEL_ID = os.getenv("CHANNEL_ID", "@mygame_channel")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/mygame_channel")

# ==================== МЕМНЫЕ ФРАЗЫ ====================
GOOD_TRAINING_PHRASES = [
    "💪 Ты поднял штангу… почти. Завтра точно получится!",
    "🔥 Мышцы кричат: «За что?!», но ты неумолим!",
    "😤 Ты выложился на максимум. Пот заливает глаза, но ты доволен.",
    "🚀 Кажется, ты становишься сильнее с каждой секундой!",
    "😅 Тренер вышел попить воды и не вернулся, но ты справился сам!",
    "💀 Ты сделал вид, что тренируешься. Это почти сработало!",
    "🎭 Твоя техника — чистый театр. Но мышцы всё равно болят!",
    "🤖 Ты тренируешься как робот… сломанный робот.",
    "🦍 Твой стиль: горилла в тренажёрке. Эффективно, но страшно.",
    "🧠 Мозг: «Хватит!». Ты: «Ещё подход!». Мозг ушёл в аутсорс.",
    "😎 Ты посмотрел на себя в зеркало и подмигнул. +2 к уверенности!",
    "🦵 Ноги дрожат как у новорождённого оленёнка. Ты растёшь!",
    "🎯 Ты попал штангой по полу. Зато громко! Все обернулись.",
    "🧘 Ты пытался медитировать со штангой. Не советую повторять.",
    "🤸 Акробатика на турнике: 0 баллов, зрители в шоке."
]

BAD_TRAINING_PHRASES = [
    "🤕 Ты уронил штангу на ногу. Больно, обидно и смешно (не тебе).",
    "😴 Тренер уснул на скамейке. Тренировка прошла впустую.",
    "🤧 Ты чихнул во время подхода — штанга уехала не туда.",
    "🤡 Оказывается, ты жал не штангу, а воздух. Эффективность — ноль.",
    "🐌 Твой прогресс медленнее, чем скорость улитки в отпуске.",
    "🎈 Ты надувал мышцы как шарик. Они сдулись.",
    "👻 Твой пресс спрятался в другое измерение.",
    "🥔 Твоя форма: картошка. Максимум — пюре.",
    "😭 Тренер уволился после твоего подхода. Ты доволен?",
    "🪑 Ты сел на штангу отдохнуть. Это не так работает.",
    "🧈 Твои мышцы сегодня — масло. Размякшее масло.",
    "🎪 Ты пытался сделать сальто с гантелями. Цирк уехал без тебя.",
    "🦥 Тренировка в стиле ленивца: медленно и без результата.",
    "🤖 Тренер сказал: «Одобряю». Но он был саркастичным роботом.",
    "🫠 Твоя выносливость: 0, воля: 0, самомнение: 100."
]

INJURY_PHRASES = {
    "light": [
        "🤕 Лёгкое растяжение. Ты всё ещё можешь чипсики открывать!",
        "💢 Мышцы ноют: «Зачем ты так с нами?»",
        "🩹 Твоя гордость пострадала больше, чем тело."
    ],
    "medium": [
        "🤕 Серьёзное растяжение. Тренер качает головой.",
        "🏥 Кажется, твоя спина решила уйти на пенсию раньше тебя.",
        "😫 Твой позвоночник сказал: «Я устал, я ухожу»."
    ],
    "heavy": [
        "💀 ТЯЖЁЛАЯ ТРАВМА! Скорая уже выехала. И полиция. И пожарные.",
        "🚑 Ты сломал не только штангу, но и веру тренера в человечество.",
        "🪦 Тренер: «Я же говорил не пробовать это дома». Ты в зале, но суть ясна."
    ]
}

FIGHT_WIN_PHRASES = [
    "🏆 Ты победил! Противник просит пощады. И автограф.",
    "👑 Ты — король арены! Бот отправляется в нокаут и в депрессию.",
    "💥 Твой удар был настолько силён, что бот перезагрузился!",
    "⚡ Ты двигался как молния… медленная молния, но всё же!",
    "🎯 Точный удар! Бот отправляется чинить свои микросхемы.",
    "🦍 Джон Сина плачет от гордости где-то в сторонке.",
    "😎 Ты посмотрел на бота — он самоустранился."
]

FIGHT_LOSE_PHRASES = [
    "😢 Ты проиграл. Даже бот смотрит с сочувствием.",
    "💔 Бот был безжалостен. Твоя стратегия «авось» не сработала.",
    "🎭 Поражение — это просто репетиция будущей победы. Наверное.",
    "🫠 Ты дрался храбро… но бесполезно, как бульдозер против танка.",
    "😴 Бот победил тебя, пока проверял уведомления.",
    "🤡 Твоя тактика боя: «Закрыть глаза и махать». Не вышло."
]

FIGHT_DRAW_PHRASES = [
    "🤝 Ничья! Вы оба настолько сильны, что решили дружить.",
    "🕊 Бот предлагает мир. Ты согласился. Пацифисты +2.",
    "😐 Ничья. Как будто вы просто обнялись вместо боя.",
    "🤷 Два бойца — ноль результата. Но зато какие красивые!"
]

SUBSCRIBE_PHRASES = [
    "🎉 Ты официально крутой! +500 ₽ за подписку!",
    "💎 Элитный статус активирован! Деньги уже в кармане.",
    "🌟 Теперь ты в элитном клубе. Вход — 500 ₽ (но тебе подарили)."
]

EAT_FOOD_PHRASES = [
    "🍔 Ням-ням! Энергия восстановлена. Желудок доволен.",
    "😋 Вкуснотища! Даже штанга обзавидовалась.",
    "🤤 Ты ел как чемпион. Чемпион по поеданию.",
    "🍕 Еда — топливо для мышц. И для лени тоже."
]

BUY_ITEM_PHRASES = [
    "🛒 Покупка совершена! Твой кошелёк плачет, но ты рад.",
    "💸 Деньги ушли, товар пришёл. Капитализм в действии!",
    "🎁 Ты купил это. Зачем? Потому что можешь!",
    "💳 Ещё одна покупка. Твоя мама бы не одобрила."
]

PROMO_ACTIVATED_PHRASES = [
    "🎟 Промокод активирован! Ты чувствуешь себя хакером.",
    "🔓 Код принят. Где ты его взял? Неважно. Держи плюшки!",
    "🎁 Бонус за секретный код! Ты — везунчик!",
    "💎 Промокод сработал! Удача сегодня на твоей стороне."
]

REFERRAL_PHRASES = [
    "👥 Ты привёл друга! Друг доволен, ты богаче на 50 ₽.",
    "🤝 Реферал залетел! +50 ₽ в твою копилку.",
    "📣 Сарафанное радио работает! Держи монету."
]

# ==================== БАЗА ДАННЫХ ====================
DB_NAME = "game_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                strength INTEGER DEFAULT 5,
                energy INTEGER DEFAULT 10,
                max_energy INTEGER DEFAULT 10,
                money INTEGER DEFAULT 100,
                experience INTEGER DEFAULT 0,
                energy_timestamp REAL DEFAULT 0,
                last_train REAL DEFAULT 0,
                last_fight REAL DEFAULT 0,
                injury_type TEXT DEFAULT NULL,
                injury_until REAL DEFAULT 0,
                boost_xp REAL DEFAULT 0,
                boost_strength REAL DEFAULT 0,
                boost_protection REAL DEFAULT 0,
                subscribed INTEGER DEFAULT 0,
                referral_code TEXT,
                referred_by INTEGER DEFAULT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                type TEXT DEFAULT 'money',
                value INTEGER,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_usage (
                user_id INTEGER,
                promo_id INTEGER,
                PRIMARY KEY (user_id, promo_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, item_name)
            )
        """)
        await db.commit()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
    return None

async def update_user(user_id: int, **kwargs):
    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
        await db.commit()

async def create_user(user_id: int, username: str, referred_by: Optional[int] = None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, referred_by, referral_code)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, referred_by, f"ref_{user_id}"))
        await db.commit()

async def get_promo(code: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM promocodes WHERE code = ?", (code,)) as cursor:
            row = await cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
    return None

async def use_promo(user_id: int, promo_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM promo_usage WHERE user_id = ? AND promo_id = ?", (user_id, promo_id))
        if await cursor.fetchone():
            return False
        await db.execute("INSERT INTO promo_usage (user_id, promo_id) VALUES (?, ?)", (user_id, promo_id))
        await db.execute("UPDATE promocodes SET current_uses = current_uses + 1 WHERE id = ?", (promo_id,))
        await db.commit()
        return True

async def add_item(user_id: int, item_name: str, quantity: int = 1):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO items (user_id, item_name, quantity) VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + ?
        """, (user_id, item_name, quantity, quantity))
        await db.commit()

async def get_item_count(user_id: int, item_name: str) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT quantity FROM items WHERE user_id = ? AND item_name = ?", (user_id, item_name)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def remove_item(user_id: int, item_name: str, quantity: int = 1) -> bool:
    current = await get_item_count(user_id, item_name)
    if current < quantity:
        return False
    async with aiosqlite.connect(DB_NAME) as db:
        if current == quantity:
            await db.execute("DELETE FROM items WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        else:
            await db.execute("UPDATE items SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?", (quantity, user_id, item_name))
        await db.commit()
    return True

async def get_top_strength(limit: int = 10) -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, username, strength FROM users ORDER BY strength DESC LIMIT ?", (limit,)) as cursor:
            return await cursor.fetchall()

async def get_top_money(limit: int = 10) -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, username, money FROM users ORDER BY money DESC LIMIT ?", (limit,)) as cursor:
            return await cursor.fetchall()

# ==================== ИГРОВАЯ ЛОГИКА ====================
def format_money(amount: int) -> str:
    return f"{amount:,} ₽".replace(",", ".")

def get_random_damage(strength: int) -> int:
    base = random.randint(5, 15)
    bonus = int(strength * 1.5)
    return base + bonus

def calculate_training_result(strength: int, energy_spent: int, boost_strength: float = 0, boost_protection: float = 0) -> dict:
    # Базовые параметры
    if strength <= 15:
        gain_range = (2, 5)
        injury_chance = 0.08
        strength_level = "noob"
    elif strength <= 50:
        gain_range = (1, 3)
        injury_chance = 0.12
        strength_level = "middle"
    else:
        gain_range = (2, 4)
        injury_chance = 0.15
        strength_level = "pro"
    
    # Модификаторы от бафов
    gain_range = (int(gain_range[0] * (1 + boost_strength)), int(gain_range[1] * (1 + boost_strength)))
    injury_chance *= (1 - boost_protection)
    
    # Случайный результат
    bad_training_chance = 0.15
    if random.random() < bad_training_chance:
        strength_change = random.randint(-3, 0)
        xp_gain = random.randint(1, 3)
        msg = random.choice(BAD_TRAINING_PHRASES)
    else:
        strength_change = random.randint(*gain_range)
        xp_gain = random.randint(3, 8) + energy_spent
        msg = random.choice(GOOD_TRAINING_PHRASES)
    
    # Проверка на травму
    injury_type = None
    if random.random() < injury_chance:
        injury_roll = random.random()
        if injury_roll < 0.005:
            injury_type = "heavy"
            injury_msg = random.choice(INJURY_PHRASES["heavy"])
        elif injury_roll < 0.02:
            injury_type = "medium"
            injury_msg = random.choice(INJURY_PHRASES["medium"])
        else:
            injury_type = "light"
            injury_msg = random.choice(INJURY_PHRASES["light"])
        
        msg += f"\n\n{injury_msg}"
        
        if injury_type == "heavy":
            msg += "\nТренировки заблокированы на 1 час."
        elif injury_type == "medium":
            msg += "\nЭффективность снижена на 30 минут."
        else:
            msg += "\nЭффективность немного снижена на 15 минут."
    
    # Добавляем дополнительный мемный комментарий в зависимости от уровня
    if strength_level == "noob" and strength_change > 3:
        msg += "\n\n🐣 Новичкам везёт! Прогресс идёт семимильными шагами."
    elif strength_level == "pro" and strength_change > 3:
        msg += "\n\n🦍 Машина! Ты в зоне абсолютного доминирования!"
    elif strength_level == "middle" and strength_change == 1:
        msg += "\n\n🐌 Медленно, но верно. Как ипотека."
    
    return {
        "strength_change": strength_change,
        "xp_gain": xp_gain,
        "message": msg,
        "injury_type": injury_type
    }

# ==================== КЛАВИАТУРЫ ====================
def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ Тренировка", callback_data="train"),
        InlineKeyboardButton(text="🥊 Бои", callback_data="fight_menu")
    )
    builder.row(
        InlineKeyboardButton(text="🍔 Еда", callback_data="food"),
        InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="🏆 Топ", callback_data="top")
    )
    return builder.as_markup()

def train_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💪 Силовая (2⚡)", callback_data="train_strength"))
    builder.row(InlineKeyboardButton(text="🏃 Выносливость (2⚡)", callback_data="train_endurance"))
    builder.row(InlineKeyboardButton(text="🔥 Интенсив (5⚡)", callback_data="train_intense"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    return builder.as_markup()

def back_to_menu_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu"))
    return builder.as_markup()

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)
logging.basicConfig(level=logging.INFO)

# ==================== ПРОВЕРКА ПОДПИСКИ ====================
async def check_subscription(user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    # Проверка реферала
    referred_by = None
    args = command.args
    if args and args.startswith("ref_"):
        try:
            ref_id = int(args.split("_")[1])
            if ref_id != user_id:
                referred_by = ref_id
        except:
            pass
    
    user = await get_user(user_id)
    if not user:
        await create_user(user_id, username, referred_by)
        
        # Награда рефереру
        if referred_by:
            ref_user = await get_user(referred_by)
            if ref_user:
                bonus = 50
                await update_user(referred_by, money=ref_user["money"] + bonus)
                try:
                    ref_msg = random.choice(REFERRAL_PHRASES)
                    await bot.send_message(referred_by, f"🎉 {ref_msg}")
                except:
                    pass
        
        # Стартовое сообщение
        await message.answer(
            f"🏋️ Добро пожаловать в <b>Качалку Бот 3000</b>!\n\n"
            f"Ты — офисный хлюпик с силой 5 и 100 ₽ в кармане. "
            f"Пора становиться машиной!\n"
            f"Твоя форма сейчас: 🥔 картошка\n\n"
            f"🔥 <b>Бонус за подписку:</b> Подпишись на канал {CHANNEL_URL} и получи 500 ₽ и случайный буст!\n\n"
            f"Выбери действие в меню:",
            reply_markup=main_menu_keyboard()
        )
    else:
        await message.answer(
            f"🏋️ С возвращением, <b>{username}</b>!\n"
            f"💪 Сила: {user['strength']} | ⚡ Энергия: {user['energy']}/{user['max_energy']} | 💰 Деньги: {format_money(user['money'])}",
            reply_markup=main_menu_keyboard()
        )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📚 <b>Помощь по Качалке Бот 3000</b>\n\n"
        "🏋️ <b>Тренировки</b> — прокачивай силу. КД 30 сек.\n"
        "🥊 <b>Бои</b> — сражайся с ботами или игроками. КД 30 сек.\n"
        "🍔 <b>Еда</b> — восстанавливай энергию.\n"
        "🛒 <b>Магазин</b> — покупай бафы и предметы.\n"
        "👤 <b>Профиль</b> — твоя статистика.\n"
        "🏆 <b>Топ</b> — лучшие игроки.\n\n"
        "📋 <b>Команды:</b>\n"
        "/start — Главное меню\n"
        "/help — Это сообщение\n"
        "/top — Топ игроков\n"
        "/promo КОД — Использовать промокод\n"
        "/fight — Вызвать на бой (ответом на сообщение или /fight @user)\n"
        "/subscribe — Проверить подписку и получить бонус\n\n"
        "🎁 <b>Подпишись на канал</b> и получи 500 ₽ + случайный буст!\n\n"
        "💡 <b>Совет:</b> Не будь 🥔, будь 🦍!"
    )
    await message.answer(help_text, reply_markup=back_to_menu_button())

@dp.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала нажми /start")
        return
    
    if user.get("subscribed"):
        await message.answer("✅ Ты уже получил бонус за подписку! Второй раз не прокатит 😏")
        return
    
    if await check_subscription(user_id):
        # Даём награду
        bonus_money = 500
        # Случайный буст
        boosts = [
            ("boost_xp", 0.2, "📈 +20% к опыту на 24 часа"),
            ("boost_strength", 0.15, "💪 +15% к силе на 24 часа"),
            ("boost_protection", 0.3, "🛡 Защита от травм 30% на 24 часа"),
        ]
        boost_field, boost_value, boost_desc = random.choice(boosts)
        
        await update_user(user_id, 
                         money=user["money"] + bonus_money, 
                         subscribed=1,
                         **{boost_field: boost_value})
        
        sub_msg = random.choice(SUBSCRIBE_PHRASES)
        await message.answer(
            f"{sub_msg}\n\n"
            f"💰 Ты получаешь: <b>{format_money(bonus_money)}</b>\n"
            f"{boost_desc}\n\n"
            f"Награда уже начислена!",
            reply_markup=main_menu_keyboard()
        )
    else:
        await message.answer(
            f"❌ Ты не подписан на канал!\n\n"
            f"Подпишись: {CHANNEL_URL}\n"
            f"Затем нажми /subscribe снова, чтобы получить награду.\n\n"
            f"Псс.. это бесплатные деньги 💰",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Перейти в канал", url=CHANNEL_URL)],
                [InlineKeyboardButton(text="🔄 Проверить подписку", callback_data="check_sub")]
            ])
        )

@dp.message(Command("top"))
async def cmd_top(message: Message):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💪 Топ по силе", callback_data="top_strength"),
        InlineKeyboardButton(text="💰 Топ по деньгам", callback_data="top_money")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    await message.answer("🏆 Выбери категорию топа.\nЗнай своих героев и бездельников:", reply_markup=builder.as_markup())

@dp.message(Command("promo"))
async def cmd_promo(message: Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args
    
    if not args:
        await message.answer("❌ Использование: /promo КОД\nПодсказка: ищи промокоды в канале 😉")
        return
    
    code = args.strip().upper()
    promo = await get_promo(code)
    
    if not promo:
        await message.answer("❌ Промокод не найден! Может, у тебя пальцы не туда жмут?")
        return
    
    if not promo["is_active"] or promo["current_uses"] >= promo["max_uses"]:
        await message.answer("❌ Промокод больше не действителен! Его съели до тебя 🥲")
        return
    
    if not await use_promo(user_id, promo["id"]):
        await message.answer("❌ Ты уже использовал этот промокод! Жадина-говядина 🤨")
        return
    
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала нажми /start")
        return
    
    promo_msg = random.choice(PROMO_ACTIVATED_PHRASES)
    # Выдача награды
    if promo["type"] == "money":
        await update_user(user_id, money=user["money"] + promo["value"])
        await message.answer(f"{promo_msg}\n\n✅ Получено: {format_money(promo['value'])}")
    elif promo["type"] == "strength":
        await update_user(user_id, strength=user["strength"] + promo["value"])
        await message.answer(f"{promo_msg}\n\n✅ Получено силы: +{promo['value']}")
    elif promo["type"] == "energy_boost":
        await add_item(user_id, "energy_drink", promo["value"])
        await message.answer(f"{promo_msg}\n\n✅ Получено: {promo['value']} энергетиков 🥤")
    elif promo["type"] == "protection":
        await update_user(user_id, boost_protection=min(1.0, user.get("boost_protection", 0) + promo["value"] / 100))
        await message.answer(f"{promo_msg}\n\n✅ Защита от травм увеличена на {promo['value']}%")

@dp.message(Command("fight"))
async def cmd_fight(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала нажми /start")
        return
    
    # Проверка на PvP (ответ на сообщение)
    if message.reply_to_message and message.reply_to_message.from_user.id != user_id:
        opponent_id = message.reply_to_message.from_user.id
        opponent = await get_user(opponent_id)
        if not opponent:
            await message.answer("❌ Этот игрок ещё не зарегистрирован в боте!\nСкажи ему нажать /start, ленивцу 🦥")
            return
        
        # Проверка КД
        current_time = time.time()
        if current_time - user["last_fight"] < 30:
            remaining = 30 - int(current_time - user["last_fight"])
            await message.answer(f"⏳ Подожди ещё {remaining} сек. перед боем!\nПока можешь попить воды 🚰")
            return
        
        # Бой
        user_dmg = get_random_damage(user["strength"])
        opp_dmg = get_random_damage(opponent["strength"])
        
        if user_dmg > opp_dmg:
            winner_id, loser_id = user_id, opponent_id
            winner_dmg, loser_dmg = user_dmg, opp_dmg
        elif user_dmg < opp_dmg:
            winner_id, loser_id = opponent_id, user_id
            winner_dmg, loser_dmg = opp_dmg, user_dmg
        else:
            # Ничья
            await update_user(user_id, last_fight=current_time)
            draw_msg = random.choice(FIGHT_DRAW_PHRASES)
            await message.answer(
                f"⚔️ <b>PvP Бой: НИЧЬЯ!</b>\n\n"
                f"{draw_msg}\n\n"
                f"{message.from_user.username}: {user_dmg} урона\n"
                f"{message.reply_to_message.from_user.username}: {opp_dmg} урона",
                reply_markup=main_menu_keyboard()
            )
            return
        
        winner = await get_user(winner_id)
        loser = await get_user(loser_id)
        
        # Награда
        reward_money = random.randint(20, 100)
        reward_xp = random.randint(5, 20)
        
        await update_user(winner_id, 
                         money=winner["money"] + reward_money,
                         experience=winner["experience"] + reward_xp,
                         last_fight=current_time)
        await update_user(loser_id, last_fight=current_time)
        
        winner_name = message.from_user.username if winner_id == user_id else message.reply_to_message.from_user.username
        loser_name = message.reply_to_message.from_user.username if loser_id == user_id else message.from_user.username
        
        win_msg = random.choice(FIGHT_WIN_PHRASES)
        await message.answer(
            f"⚔️ <b>PvP Бой завершён!</b>\n\n"
            f"{win_msg}\n\n"
            f"🏆 Победитель: <b>{winner_name}</b> ({winner_dmg} урона)\n"
            f"😢 Проигравший: <b>{loser_name}</b> ({loser_dmg} урона)\n\n"
            f"💰 Награда победителю: {format_money(reward_money)}\n"
            f"✨ Опыт: +{reward_xp}",
            reply_markup=main_menu_keyboard()
        )
    else:
        # Бой с ботом
        await message.answer(
            "🥊 <b>Выбери тип боя:</b>\n\n"
            "🤖 <b>Бой с ботом</b> — безопасный вариант\n"
            "👤 <b>PvP</b> — ответь на сообщение соперника командой /fight\n\n"
            "Кто на новенького? 😏",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🤖 Бой с ботом", callback_data="fight_bot")],
                [InlineKeyboardButton(text="👤 PvP (ответь на сообщение)", callback_data="fight_pvp_info")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
            ])
        )

# Команды админа
@dp.message(Command("give_money"))
async def cmd_give_money(message: Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 Ты не админ, дружок. Иди качайся!")
        return
    
    args = command.args.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /give_money USER_ID AMOUNT")
        return
    
    try:
        target_id = int(args[0])
        amount = int(args[1])
    except:
        await message.answer("❌ Неверный формат чисел!\nЧувак, это просто цифры, соберись!")
        return
    
    user = await get_user(target_id)
    if not user:
        await message.answer("❌ Пользователь не найден!\nОн что, в спортзале без телефона?")
        return
    
    await update_user(target_id, money=user["money"] + amount)
    await message.answer(f"✅ Игроку {target_id} выдано {format_money(amount)}\nБаланс пополнен как бицуха после протеина 💉")
    try:
        await bot.send_message(target_id, f"💰 Админ подогнал тебе {format_money(amount)}!\nТрать с умом (или не трать)")
    except:
        pass

@dp.message(Command("give_strength"))
async def cmd_give_strength(message: Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 Не админ — не командуй!")
        return
    
    args = command.args.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /give_strength USER_ID AMOUNT")
        return
    
    try:
        target_id = int(args[0])
        amount = int(args[1])
    except:
        await message.answer("❌ Цифры, говорю, цифры! Не буквы!")
        return
    
    user = await get_user(target_id)
    if not user:
        await message.answer("❌ Пользователь не найден!\nНаверное, ушёл есть после тренировки 🍔")
        return
    
    await update_user(target_id, strength=user["strength"] + amount)
    await message.answer(f"✅ Игроку {target_id} выдано +{amount} силы\nТеперь он сможет открыть банку огурцов без помощи 💪")
    try:
        await bot.send_message(target_id, f"💪 Админ накачал тебя на +{amount} силы!\nИди жми штангу, герой!")
    except:
        pass

@dp.message(Command("give_item"))
async def cmd_give_item(message: Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 Только для больших боссов!")
        return
    
    args = command.args.split()
    if len(args) < 3:
        await message.answer("❌ Использование: /give_item USER_ID ITEM_NAME COUNT")
        return
    
    try:
        target_id = int(args[0])
        item_name = args[1]
        count = int(args[2])
    except:
        await message.answer("❌ Неверный формат!\nUSER_ID — число, ITEM_NAME — слово, COUNT — число. Всё просто!")
        return
    
    user = await get_user(target_id)
    if not user:
        await message.answer("❌ Пользователь не найден!")
        return
    
    await add_item(target_id, item_name, count)
    await message.answer(f"✅ Игроку {target_id} выдано {count}x {item_name}\nПосылка доставлена курьером-качком 📦")
    try:
        await bot.send_message(target_id, f"🎁 Админ отправил тебе {count}x {item_name}!\nРаспаковывай, пока горячее!")
    except:
        pass

@dp.message(Command("createpromo"))
async def cmd_create_promo(message: Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 Создавать промокоды могут только админы!\nТы пока просто смертный 🧑")
        return
    
    args = command.args.split()
    if len(args) < 3:
        await message.answer("❌ Использование: /createpromo CODE VALUE USES [type]\nТипы: money, strength, energy_boost, protection")
        return
    
    code = args[0].upper()
    try:
        value = int(args[1])
        max_uses = int(args[2])
    except:
        await message.answer("❌ VALUE и USES должны быть числами!\nМатематика, 1 класс 🤓")
        return
    
    promo_type = args[3].lower() if len(args) > 3 else "money"
    if promo_type not in ["money", "strength", "energy_boost", "protection"]:
        await message.answer("❌ Неверный тип промокода!\nВыбирай: money, strength, energy_boost, protection")
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT INTO promocodes (code, type, value, max_uses) VALUES (?, ?, ?, ?)",
                (code, promo_type, value, max_uses)
            )
            await db.commit()
            await message.answer(f"✅ Промокод <b>{code}</b> создан!\nТип: {promo_type}, Ценность: {value}, Использований: {max_uses}\n\nРаздавай с умом, спам не приветствуется 🎫")
        except:
            await message.answer("❌ Такой промокод уже существует!\nПридумай что-то пооригинальнее, а? 🎨")

# ==================== CALLBACK ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала нажми /start", show_alert=True)
        return
    
    # Авто-реген энергии
    current_time = time.time()
    if user["energy"] < user["max_energy"] and current_time > user["energy_timestamp"]:
        elapsed = current_time - user["energy_timestamp"]
        regen = min(user["max_energy"] - user["energy"], int(elapsed * 0.00139))
        if regen > 0:
            await update_user(callback.from_user.id, energy=user["energy"] + regen, energy_timestamp=current_time)
            user["energy"] += regen
    
    # Определяем статус формы по силе
    if user["strength"] <= 10:
        form = "🥔 Картошка"
    elif user["strength"] <= 25:
        form = "🐣 Птенец"
    elif user["strength"] <= 50:
        form = "💪 Качок-любитель"
    elif user["strength"] <= 80:
        form = "🦍 Горилла"
    else:
        form = "🐉 Легенда"
    
    await callback.message.edit_text(
        f"🏋️ <b>Главное меню</b>\n\n"
        f"💪 Сила: {user['strength']}\n"
        f"⚡ Энергия: {user['energy']}/{user['max_energy']}\n"
        f"💰 Деньги: {format_money(user['money'])}\n"
        f"✨ Опыт: {user['experience']}\n"
        f"🏅 Форма: {form}\n\n"
        f"Выбери действие:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "train")
async def cb_train(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏋️ <b>Выбери тип тренировки:</b>\n\n"
        "💪 <b>Силовая</b> (2⚡) — база, база и ещё раз база\n"
        "🏃 <b>Выносливость</b> (2⚡) — беги, Форрест, беги\n"
        "🔥 <b>Интенсив</b> (5⚡) — хардкор, только для отчаянных\n\n"
        "⚠️ Помни: травмы — это не шутки!\n"
        "Ну, то есть шутки, но обидные 😅",
        reply_markup=train_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("train_"))
async def cb_do_training(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.answer("Сначала нажми /start")
        return
    
    # Проверка КД
    current_time = time.time()
    if current_time - user["last_train"] < 30:
        remaining = 30 - int(current_time - user["last_train"])
        await callback.answer(f"⏳ Подожди ещё {remaining} сек.\nТвои мышцы ещё не остыли! 🧊", show_alert=True)
        return
    
    # Проверка травмы
    if user.get("injury_until") and current_time < user["injury_until"]:
        remaining = int(user["injury_until"] - current_time)
        await callback.answer(f"🤕 Ты травмирован! Восстановление через {remaining} сек.\nПока можешь смотреть мотивационные видео 📺", show_alert=True)
        return
    
    # Определение типа тренировки
    train_type = callback.data.split("_")[1]
    if train_type == "strength":
        energy_cost = 2
        train_name = "Силовая"
    elif train_type == "endurance":
        energy_cost = 2
        train_name = "Выносливость"
    else:  # intense
        energy_cost = 5
        train_name = "Интенсивная"
    
    if user["energy"] < energy_cost:
        await callback.answer(f"❌ Недостаточно энергии! Нужно {energy_cost}⚡\nИди поешь, слабак 🍔", show_alert=True)
        return
    
    # Применяем бафы
    boost_strength = user.get("boost_strength", 0)
    boost_protection = user.get("boost_protection", 0)
    if user.get("injury_type") == "medium" and current_time < user.get("injury_until", 0):
        boost_strength -= 0.2  # штраф за среднюю травму
    
    result = calculate_training_result(user["strength"], energy_cost, boost_strength, boost_protection)
    
    new_strength = max(0, user["strength"] + result["strength_change"])
    new_energy = user["energy"] - energy_cost
    new_exp = user["experience"] + result["xp_gain"]
    
    # Если травма
    injury_type = result["injury_type"]
    injury_until = 0
    if injury_type == "light":
        injury_until = current_time + 900  # 15 минут
    elif injury_type == "medium":
        injury_until = current_time + 1800  # 30 минут
    elif injury_type == "heavy":
        injury_until = current_time + 3600  # 1 час
    
    await update_user(user_id, 
                     strength=new_strength, 
                     energy=new_energy,
                     experience=new_exp,
                     last_train=current_time,
                     energy_timestamp=current_time,
                     injury_type=injury_type,
                     injury_until=injury_until)
    
    msg = f"🏋️ <b>Тренировка: {train_name}</b>\n\n"
    msg += result["message"]
    msg += f"\n\n💪 Сила: {user['strength']} → {new_strength} ({'+' if result['strength_change'] >= 0 else ''}{result['strength_change']})"
    msg += f"\n✨ Опыт: +{result['xp_gain']}"
    msg += f"\n⚡ Энергия: {new_energy}/{user['max_energy']}"
    
    await callback.message.edit_text(msg, reply_markup=back_to_menu_button())
    await callback.answer()

@dp.callback_query(F.data == "fight_menu")
async def cb_fight_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🥊 <b>Боевая арена</b>\n\n"
        "Выбери с кем хочешь подраться:\n\n"
        "🤖 <b>Бот</b> — безопасный спарринг\n"
        "👤 <b>PvP</b> — докажи что ты не 🐥",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Бой с ботом", callback_data="fight_bot")],
            [InlineKeyboardButton(text="👤 PvP (ответь на сообщение)", callback_data="fight_pvp_info")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "fight_bot")
async def cb_fight_bot(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.answer("Сначала нажми /start")
        return
    
    # Проверка КД
    current_time = time.time()
    if current_time - user["last_fight"] < 30:
        remaining = 30 - int(current_time - user["last_fight"])
        await callback.answer(f"⏳ Кулдаун {remaining} сек.\nБот пока попьёт машинного масла 🛢", show_alert=True)
        return
    
    # Бой с ботом
    bot_strength = random.randint(max(1, user["strength"] - 10), user["strength"] + 10)
    user_dmg = get_random_damage(user["strength"])
    bot_dmg = get_random_damage(bot_strength)
    
    if user_dmg > bot_dmg:
        # Победа
        reward_money = random.randint(10, 50) + int(user["strength"] * 0.5)
        reward_xp = random.randint(3, 15)
        
        await update_user(user_id, 
                         money=user["money"] + reward_money,
                         experience=user["experience"] + reward_xp,
                         last_fight=current_time)
        
        win_msg = random.choice(FIGHT_WIN_PHRASES)
        msg = (f"🥊 <b>Бой с ботом</b>\n\n"
               f"{win_msg}\n\n"
               f"Твой урон: {user_dmg}\n"
               f"Урон бота (сила {bot_strength}): {bot_dmg}\n\n"
               f"💰 Награда: {format_money(reward_money)}\n"
               f"✨ Опыт: +{reward_xp}")
    elif user_dmg < bot_dmg:
        # Поражение
        loss_xp = random.randint(1, 5)
        await update_user(user_id, 
                         experience=max(0, user["experience"] + loss_xp),
                         last_fight=current_time)
        
        lose_msg = random.choice(FIGHT_LOSE_PHRASES)
        msg = (f"🥊 <b>Бой с ботом</b>\n\n"
               f"{lose_msg}\n\n"
               f"Твой урон: {user_dmg}\n"
               f"Урон бота (сила {bot_strength}): {bot_dmg}\n\n"
               f"✨ Утешительный опыт: +{loss_xp}\n"
               f"Не расстраивайся, железяки тоже умеют драться 🤖")
    else:
        await update_user(user_id, last_fight=current_time)
        draw_msg = random.choice(FIGHT_DRAW_PHRASES)
        msg = (f"🥊 <b>Бой с ботом</b>\n\n"
               f"{draw_msg}\n\n"
               f"Твой урон: {user_dmg}\n"
               f"Урон бота (сила {bot_strength}): {bot_dmg}")
    
    await callback.message.edit_text(msg, reply_markup=back_to_menu_button())
    await callback.answer()

@dp.callback_query(F.data == "fight_pvp_info")
async def cb_pvp_info(callback: CallbackQuery):
    await callback.answer(
        "👤 Для PvP боя:\n"
        "1. Найди сообщение соперника\n"
        "2. Ответь на него командой /fight\n"
        "3. Жди результата! ⚔️",
        show_alert=True
    )

@dp.callback_query(F.data == "food")
async def cb_food(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала нажми /start")
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🍎 Яблоко (+2⚡) — 20₽", callback_data="eat_apple"))
    builder.row(InlineKeyboardButton(text="🥤 Энергетик (+5⚡) — 50₽", callback_data="eat_drink"))
    builder.row(InlineKeyboardButton(text="🍗 Стейк (полное восстановление) — 150₽", callback_data="eat_steak"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    
    await callback.message.edit_text(
        f"🍔 <b>Столовая для качков</b>\n\n"
        f"⚡ Энергия: {user['energy']}/{user['max_energy']}\n"
        f"💰 Деньги: {format_money(user['money'])}\n\n"
        f"Выбирай, что будешь жрать:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("eat_"))
async def cb_eat_food(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.answer("Сначала нажми /start")
        return
    
    food_type = callback.data.split("_")[1]
    if food_type == "apple":
        cost, energy_restore, name = 20, 2, "Яблоко"
        emoji = "🍎"
    elif food_type == "drink":
        cost, energy_restore, name = 50, 5, "Энергетик"
        emoji = "🥤"
    else:  # steak
        cost, energy_restore, name = 150, user["max_energy"], "Стейк"
        emoji = "🍗"
    
    if user["money"] < cost:
        await callback.answer(f"❌ Недостаточно денег! Нужно {format_money(cost)}\nИди зарабатывай, бомж 🥲", show_alert=True)
        return
    
    if user["energy"] >= user["max_energy"]:
        await callback.answer("⚡ Энергия уже полная!\nКуда ещё есть? Ты что, Пумба? 🐗", show_alert=True)
        return
    
    new_energy = min(user["max_energy"], user["energy"] + energy_restore)
    new_money = user["money"] - cost
    
    await update_user(user_id, energy=new_energy, money=new_money)
    
    eat_msg = random.choice(EAT_FOOD_PHRASES)
    await callback.message.edit_text(
        f"{emoji} <b>{name}</b> уничтожен!\n\n"
        f"{eat_msg}\n\n"
        f"⚡ Энергия: {user['energy']} → {new_energy}\n"
        f"💰 Деньги: {format_money(new_money)}",
        reply_markup=back_to_menu_button()
    )
    await callback.answer()

@dp.callback_query(F.data == "shop")
async def cb_shop(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала нажми /start")
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🥤 Энергетик x3 — 120₽", callback_data="buy_energy_drink"))
    builder.row(InlineKeyboardButton(text="📈 Буст опыта (20% на 24ч) — 300₽", callback_data="buy_boost_xp"))
    builder.row(InlineKeyboardButton(text="💪 Буст силы (15% на 24ч) — 400₽", callback_data="buy_boost_strength"))
    builder.row(InlineKeyboardButton(text="🛡 Защита от травм (30% на 24ч) — 500₽", callback_data="buy_boost_protection"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    
    await callback.message.edit_text(
        f"🛒 <b>Магазин Качка</b>\n\n"
        f"💰 Твой баланс: {format_money(user['money'])}\n\n"
        f"Выбери товар:\n"
        f"(цены кусаются, но ты же не лох 🤑)",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.answer("Сначала нажми /start")
        return
    
    item_type = callback.data.split("_", 1)[1]
    buy_msg = random.choice(BUY_ITEM_PHRASES)
    
    if item_type == "energy_drink":
        cost, name = 120, "Энергетик x3"
        if user["money"] < cost:
            await callback.answer(f"❌ Не хватает денег! Нужно {format_money(cost)}\nТы нищеброд? 💸", show_alert=True)
            return
        await update_user(user_id, money=user["money"] - cost)
        await add_item(user_id, "energy_drink", 3)
        await callback.message.edit_text(f"{buy_msg}\n\n✅ Куплено: <b>{name}</b> за {format_money(cost)}\nПей с умом 🥤", reply_markup=back_to_menu_button())
    
    elif item_type == "boost_xp":
        cost, name = 300, "Буст опыта +20%"
        if user["money"] < cost:
            await callback.answer(f"❌ Не хватает денег! Нужно {format_money(cost)}", show_alert=True)
            return
        await update_user(user_id, money=user["money"] - cost, boost_xp=0.2)
        await callback.message.edit_text(f"{buy_msg}\n\n✅ Куплено: <b>{name}</b> за {format_money(cost)}\nОпыт теперь льётся рекой 🌊", reply_markup=back_to_menu_button())
    
    elif item_type == "boost_strength":
        cost, name = 400, "Буст силы +15%"
        if user["money"] < cost:
            await callback.answer(f"❌ Не хватает денег! Нужно {format_money(cost)}", show_alert=True)
            return
        await update_user(user_id, money=user["money"] - cost, boost_strength=0.15)
        await callback.message.edit_text(f"{buy_msg}\n\n✅ Куплено: <b>{name}</b> за {format_money(cost)}\nТы становишься Халком! 🟢", reply_markup=back_to_menu_button())
    
    elif item_type == "boost_protection":
        cost, name = 500, "Защита от травм +30%"
        if user["money"] < cost:
            await callback.answer(f"❌ Не хватает денег! Нужно {format_money(cost)}", show_alert=True)
            return
        await update_user(user_id, money=user["money"] - cost, boost_protection=0.3)
        await callback.message.edit_text(f"{buy_msg}\n\n✅ Куплено: <b>{name}</b> за {format_money(cost)}\nТеперь ты бронированный качок 🛡", reply_markup=back_to_menu_button())
    
    await callback.answer()

@dp.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала нажми /start")
        return
    
    # Реферальная ссылка
    bot_info = await bot.me()
    ref_link = f"t.me/{bot_info.username}?start={user['referral_code']}"
    
    # Статус травмы
    injury_status = "Нет травм ✅ (фух, пронесло)"
    if user.get("injury_type") and time.time() < user.get("injury_until", 0):
        remaining = int(user["injury_until"] - time.time())
        injury_names = {"light": "Лёгкая 🤕", "medium": "Средняя 😫", "heavy": "Тяжёлая 💀"}
        injury_status = f"{injury_names.get(user['injury_type'], 'Травма')} (ещё {remaining} сек.)"
    
    # Определяем ранг по силе
    if user['strength'] <= 10:
        rank = "🥔 Картофельный воин"
    elif user['strength'] <= 25:
        rank = "🐣 Подающий надежды"
    elif user['strength'] <= 50:
        rank = "💪 Уверенный качок"
    elif user['strength'] <= 80:
        rank = "🦍 Доминатор"
    else:
        rank = "🐉 Бог качалки"
    
    msg = (
        f"👤 <b>Профиль игрока</b>\n\n"
        f"🏅 Ранг: <b>{rank}</b>\n"
        f"💪 Сила: <b>{user['strength']}</b>\n"
        f"⚡ Энергия: <b>{user['energy']}/{user['max_energy']}</b>\n"
        f"💰 Деньги: <b>{format_money(user['money'])}</b>\n"
        f"✨ Опыт: <b>{user['experience']}</b>\n\n"
        f"🛡 Статус: {injury_status}\n"
        f"📈 Буст XP: {int(user.get('boost_xp', 0) * 100)}%\n"
        f"💪 Буст силы: {int(user.get('boost_strength', 0) * 100)}%\n"
        f"🛡 Защита от травм: {int(user.get('boost_protection', 0) * 100)}%\n\n"
        f"🔗 Реферальная ссылка:\n{ref_link}\n\n"
        f"💡 Приглашай друзей и получай бонусы!"
    )
    
    await callback.message.edit_text(msg, reply_markup=back_to_menu_button())
    await callback.answer()

@dp.callback_query(F.data == "top")
async def cb_top_menu(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💪 Топ по силе", callback_data="top_strength"),
        InlineKeyboardButton(text="💰 Топ по деньгам", callback_data="top_money")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    await callback.message.edit_text(
        "🏆 <b>Доска почёта</b>\n\n"
        "Кто тут самый сильный и богатый?\n"
        "Сейчас узнаем! 👇",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "top_strength")
async def cb_top_strength(callback: CallbackQuery):
    top = await get_top_strength(10)
    msg = "🏆 <b>Топ-10 Качков</b>\n\n"
    
    if not top:
        msg += "Пока никого нет. Ты можешь быть первым! 🥇"
    else:
        for i, (user_id, username, strength) in enumerate(top, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            name = username or f"ID:{user_id}"
            
            # Мемные комментарии к топу
            if i == 1:
                comment = "👑 Абсолютный чемпион!"
            elif i == 2:
                comment = "😤 Почти король"
            elif i == 3:
                comment = "🥉 Бронза тоже металл"
            elif i <= 5:
                comment = "💪 Топ-5, респект"
            else:
                comment = "👍 В десятке лучших"
            
            msg += f"{medal} <b>{name}</b> — {strength} силы | {comment}\n"
    
    await callback.message.edit_text(msg, reply_markup=back_to_menu_button())
    await callback.answer()

@dp.callback_query(F.data == "top_money")
async def cb_top_money(callback: CallbackQuery):
    top = await get_top_money(10)
    msg = "💰 <b>Топ-10 Богачей</b>\n\n"
    
    if not top:
        msg += "Пока никого нет. Печатаем деньги! 🖨💵"
    else:
        for i, (user_id, username, money) in enumerate(top, 1):
            medal = {1: "💎", 2: "💵", 3: "💸"}.get(i, f"{i}.")
            name = username or f"ID:{user_id}"
            
            # Мемные комментарии
            if i == 1:
                comment = "🤑 Денежный мешок"
            elif i == 2:
                comment = "💳 Платиновая карта"
            elif i == 3:
                comment = "💵 Почти олигарх"
            elif money > 1000:
                comment = "💰 Купается в деньгах"
            else:
                comment = "🪙 Копит на мечту"
            
            msg += f"{medal} <b>{name}</b> — {format_money(money)} | {comment}\n"
    
    await callback.message.edit_text(msg, reply_markup=back_to_menu_button())
    await callback.answer()

@dp.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        user = await get_user(user_id)
        if user and not user.get("subscribed"):
            await update_user(user_id, money=user["money"] + 500, subscribed=1)
            boost_field, boost_value, boost_desc = random.choice([
                ("boost_xp", 0.2, "📈 +20% к опыту"),
                ("boost_strength", 0.15, "💪 +15% к силе"),
                ("boost_protection", 0.3, "🛡 Защита от травм 30%")
            ])
            await update_user(user_id, **{boost_field: boost_value})
            sub_msg = random.choice(SUBSCRIBE_PHRASES)
            await callback.message.edit_text(
                f"{sub_msg}\n\n"
                f"💰 +500 ₽\n{boost_desc}",
                reply_markup=main_menu_keyboard()
            )
        else:
            await callback.message.edit_text("✅ Ты уже получил награду!\nНе жадничай 🤑", reply_markup=main_menu_keyboard())
    else:
        await callback.answer(
            "❌ Ты всё ещё не подписан!\n"
            "Награда ждёт тебя после подписки 🎁",
            show_alert=True
        )
    await callback.answer()

# ==================== ЗАПУСК ====================
async def main():
    await init_db()
    print("✅ Бот запущен!")
    print(f"🤖 Токен: {BOT_TOKEN[:10]}...")
    print(f"👑 Админы: {ADMIN_IDS}")
    print(f"📢 Канал: {CHANNEL_ID}")
    print("\n🎭 Мемные фразы загружены!")
    print("💪 Готовься качаться!\n")
    
    # Выводим рандомную мемную фразу при старте
    startup_phrases = [
        "🏋️ Штанги заряжены, протеин взболтан!",
        "💪 Мышцы готовы, мозг — не очень.",
        "🦍 Время делать кач!",
        "🥔 Картошки становятся качками...",
        "😤 Бот запущен. Тренер в шоке."
    ]
    print(random.choice(startup_phrases))
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
