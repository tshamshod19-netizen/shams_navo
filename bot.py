import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class Search(StatesGroup):
    waiting_for_query = State()

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Musiqa qidirish", callback_data="search")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")]
    ])

def results_keyboard(results):
    buttons = []
    for i, r in enumerate(results[:5]):
        title = r['title'][:40]
        buttons.append([InlineKeyboardButton(
            text=f"🎵 {title}",
            callback_data=f"dl_{i}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        f"🎵 <b>Shams Navo Music Bot</b>\n\n"
        f"Salom, <b>{message.from_user.first_name}</b>! 👋\n\n"
        f"Istalgan qo'shiqni yozing — topib yuklab beraman! 🎶",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

@dp.callback_query(F.data == "back")
async def back_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🎵 <b>Shams Navo Music Bot</b>\n\nQo'shiq nomini yozing:",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

@dp.callback_query(F.data == "search")
async def search_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Search.waiting_for_query)
    await callback.message.edit_text(
        "🔍 Qo'shiq nomini yozing:\n\n(masalan: <i>Janona</i> yoki <i>Shape of You</i>)",
        parse_mode="HTML",
        reply_markup=back_keyboard()
    )

@dp.message(Search.waiting_for_query)
async def search_handler(message: types.Message, state: FSMContext):
    query = message.text.strip()
    msg = await message.answer("⏳ Qidirilmoqda...")

    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'default_search': 'ytsearch5',
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            results = info.get('entries', [])

        if not results:
            await msg.edit_text("❌ Hech narsa topilmadi. Boshqa so'z bilan qidiring:", reply_markup=back_keyboard())
            return

        await state.update_data(results=results, query=query)
        await msg.edit_text(
            f"🔍 <b>'{query}'</b> bo'yicha natijalar:",
            parse_mode="HTML",
            reply_markup=results_keyboard(results)
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await msg.edit_text("❌ Xatolik yuz berdi. Qayta urinib ko'ring.", reply_markup=back_keyboard())

@dp.callback_query(F.data.startswith("dl_"))
async def download_callback(callback: types.CallbackQuery, state: FSMContext):
    index = int(callback.data.split("_")[1])
    data = await state.get_data()
    results = data.get('results', [])

    if index >= len(results):
        await callback.answer("❌ Xatolik!", show_alert=True)
        return

    song = results[index]
    url = f"https://www.youtube.com/watch?v={song['id']}"
    title = song.get('title', 'Noma\'lum')

    await callback.message.edit_text(f"⏳ <b>{title}</b> yuklanmoqda...", parse_mode="HTML")

    try:
        os.makedirs("downloads", exist_ok=True)
        filepath = f"downloads/{song['id']}.mp3"

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f"downloads/{song['id']}.%(ext)s",
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if os.path.exists(filepath):
            from aiogram.types import FSInputFile
            audio = FSInputFile(filepath)
            await callback.message.answer_audio(
                audio=audio,
                title=title,
                caption=f"🎵 <b>{title}</b>\n\n🤖 @shams_navo_bot",
                parse_mode="HTML"
            )
            await callback.message.edit_text(
                "✅ Musiqa yuborildi!",
                reply_markup=main_keyboard()
            )
            os.remove(filepath)
        else:
            await callback.message.edit_text("❌ Yuklab bo'lmadi.", reply_markup=back_keyboard())

    except Exception as e:
        logger.error(f"Download error: {e}")
        await callback.message.edit_text("❌ Yuklab bo'lmadi. Qayta urinib ko'ring.", reply_markup=back_keyboard())

@dp.message()
async def any_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await state.set_state(Search.waiting_for_query)
        await search_handler(message, state)

async def main():
    logger.info("Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
