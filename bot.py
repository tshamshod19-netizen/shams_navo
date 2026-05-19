import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
from database import Database
from config import BOT_TOKEN, ADMIN_IDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db = Database()

# ==================== STATES ====================
class AddMusic(StatesGroup):
    waiting_for_title = State()
    waiting_for_artist = State()
    waiting_for_file = State()

class SearchMusic(StatesGroup):
    waiting_for_query = State()

# ==================== KEYBOARDS ====================
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Musiqa qidirish", callback_data="search")],
        [InlineKeyboardButton(text="📋 Barcha musiqalar", callback_data="all_music")],
        [InlineKeyboardButton(text="🎲 Tasodifiy musiqa", callback_data="random")],
    ])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Musiqa qidirish", callback_data="search")],
        [InlineKeyboardButton(text="📋 Barcha musiqalar", callback_data="all_music")],
        [InlineKeyboardButton(text="🎲 Tasodifiy musiqa", callback_data="random")],
        [InlineKeyboardButton(text="➕ Musiqa qo'shish", callback_data="add_music")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")]
    ])

def music_list_keyboard(songs, page=0, per_page=5):
    buttons = []
    start = page * per_page
    end = min(start + per_page, len(songs))
    
    for song in songs[start:end]:
        buttons.append([InlineKeyboardButton(
            text=f"🎵 {song['artist']} - {song['title']}",
            callback_data=f"play_{song['id']}"
        )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"page_{page-1}"))
    if end < len(songs):
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"page_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ==================== HANDLERS ====================

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    db.add_user(user_id, message.from_user.full_name)
    
    is_admin = user_id in ADMIN_IDS
    keyboard = admin_keyboard() if is_admin else main_keyboard()
    
    await message.answer(
        f"🎵 <b>Musiqa Botga Xush Kelibsiz!</b>\n\n"
        f"Salom, <b>{message.from_user.first_name}</b>! 👋\n\n"
        f"Bu bot orqali siz:\n"
        f"🔍 Musiqa qidirishingiz\n"
        f"📥 Yuklab olishingiz\n"
        f"📋 Barcha musiqalarni ko'rishingiz mumkin\n\n"
        f"Quyidagi tugmalardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@dp.message(Command("admin"))
async def admin_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Siz admin emassiz!")
        return
    await message.answer("👑 Admin panel:", reply_markup=admin_keyboard())

# ==================== CALLBACKS ====================

@dp.callback_query(F.data == "back")
async def back_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    is_admin = user_id in ADMIN_IDS
    keyboard = admin_keyboard() if is_admin else main_keyboard()
    
    await callback.message.edit_text(
        "🎵 <b>Asosiy Menu</b>\n\nQuyidagi tugmalardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "search")
async def search_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SearchMusic.waiting_for_query)
    await callback.message.edit_text(
        "🔍 <b>Musiqa qidirish</b>\n\n"
        "Qo'shiq nomi yoki ijrochi ismini yozing:",
        parse_mode="HTML",
        reply_markup=back_keyboard()
    )

@dp.message(SearchMusic.waiting_for_query)
async def search_music_handler(message: types.Message, state: FSMContext):
    query = message.text.strip()
    results = db.search_music(query)
    
    if not results:
        await message.answer(
            f"❌ <b>'{query}'</b> bo'yicha hech narsa topilmadi.\n\n"
            "Boshqa so'z bilan qidirib ko'ring:",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
        return
    
    await state.clear()
    await message.answer(
        f"✅ <b>'{query}'</b> bo'yicha {len(results)} ta natija topildi:",
        parse_mode="HTML",
        reply_markup=music_list_keyboard(results)
    )

@dp.callback_query(F.data == "all_music")
async def all_music_callback(callback: types.CallbackQuery):
    songs = db.get_all_music()
    
    if not songs:
        await callback.message.edit_text(
            "📭 Hali musiqa qo'shilmagan.",
            reply_markup=back_keyboard()
        )
        return
    
    await callback.message.edit_text(
        f"📋 <b>Barcha musiqalar</b> ({len(songs)} ta):",
        parse_mode="HTML",
        reply_markup=music_list_keyboard(songs)
    )

@dp.callback_query(F.data.startswith("page_"))
async def page_callback(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    songs = db.get_all_music()
    
    await callback.message.edit_reply_markup(
        reply_markup=music_list_keyboard(songs, page)
    )

@dp.callback_query(F.data == "random")
async def random_callback(callback: types.CallbackQuery):
    song = db.get_random_music()
    
    if not song:
        await callback.message.edit_text(
            "📭 Hali musiqa qo'shilmagan.",
            reply_markup=back_keyboard()
        )
        return
    
    await callback.answer("🎲 Tasodifiy musiqa yuborilmoqda...")
    
    file_path = song['file_path']
    if os.path.exists(file_path):
        audio = FSInputFile(file_path)
        await callback.message.answer_audio(
            audio=audio,
            title=song['title'],
            performer=song['artist'],
            caption=f"🎵 <b>{song['artist']} - {song['title']}</b>\n📥 Yuklab olindi: {song['downloads']} marta",
            parse_mode="HTML"
        )
        db.increment_downloads(song['id'])
    else:
        await callback.message.answer("❌ Fayl topilmadi!")

@dp.callback_query(F.data.startswith("play_"))
async def play_callback(callback: types.CallbackQuery):
    song_id = int(callback.data.split("_")[1])
    song = db.get_music_by_id(song_id)
    
    if not song:
        await callback.answer("❌ Musiqa topilmadi!", show_alert=True)
        return
    
    await callback.answer("⏳ Yuklanmoqda...")
    
    file_path = song['file_path']
    if os.path.exists(file_path):
        audio = FSInputFile(file_path)
        await callback.message.answer_audio(
            audio=audio,
            title=song['title'],
            performer=song['artist'],
            caption=f"🎵 <b>{song['artist']} - {song['title']}</b>\n📥 Yuklab olindi: {song['downloads']} marta",
            parse_mode="HTML"
        )
        db.increment_downloads(song_id)
    else:
        await callback.answer("❌ Fayl topilmadi!", show_alert=True)

# ==================== ADMIN: ADD MUSIC ====================

@dp.callback_query(F.data == "add_music")
async def add_music_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    await state.set_state(AddMusic.waiting_for_title)
    await callback.message.edit_text(
        "➕ <b>Yangi musiqa qo'shish</b>\n\n"
        "1️⃣ Qo'shiq nomini yozing:",
        parse_mode="HTML",
        reply_markup=back_keyboard()
    )

@dp.message(AddMusic.waiting_for_title)
async def add_title_handler(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddMusic.waiting_for_artist)
    await message.answer(
        "2️⃣ Ijrochi ismini yozing:",
        reply_markup=back_keyboard()
    )

@dp.message(AddMusic.waiting_for_artist)
async def add_artist_handler(message: types.Message, state: FSMContext):
    await state.update_data(artist=message.text.strip())
    await state.set_state(AddMusic.waiting_for_file)
    await message.answer(
        "3️⃣ Audio faylni yuboring (MP3 yoki M4A):",
        reply_markup=back_keyboard()
    )

@dp.message(AddMusic.waiting_for_file, F.audio)
async def add_file_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    title = data.get('title')
    artist = data.get('artist')
    
    audio = message.audio
    
    # Save file
    os.makedirs("music_files", exist_ok=True)
    file_path = f"music_files/{audio.file_id}.mp3"
    
    await bot.download(audio, destination=file_path)
    
    # Save to DB
    song_id = db.add_music(title, artist, file_path, audio.file_id)
    
    await state.clear()
    await message.answer(
        f"✅ <b>Musiqa muvaffaqiyatli qo'shildi!</b>\n\n"
        f"🎵 Nomi: <b>{title}</b>\n"
        f"👤 Ijrochi: <b>{artist}</b>\n"
        f"🆔 ID: <code>{song_id}</code>",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )

@dp.message(AddMusic.waiting_for_file)
async def add_file_wrong_handler(message: types.Message):
    await message.answer("❌ Iltimos, audio fayl yuboring!")

# ==================== ADMIN: STATS ====================

@dp.callback_query(F.data == "stats")
async def stats_callback(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    stats = db.get_stats()
    await callback.message.edit_text(
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['users']}</b>\n"
        f"🎵 Musiqalar: <b>{stats['songs']}</b>\n"
        f"📥 Jami yuklamalar: <b>{stats['downloads']}</b>",
        parse_mode="HTML",
        reply_markup=back_keyboard()
    )

# ==================== MAIN ====================

async def main():
    logger.info("Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
