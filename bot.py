import logging
import os
import asyncio
import tempfile
import urllib.parse
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from shazamio import Shazam

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
shazam = Shazam()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Salom! Men musiqa botiman!\n\n"
        "Menga quyidagilarni yuboring:\n"
        "- YouTube yoki TikTok linki\n"
        "- Ovozli xabar\n"
        "- Audio yoki video fayl\n\n"
        "Videoni yuklab va qoshiqni topib beraman!"
    )


@dp.message(F.text)
async def handle_link(message: types.Message):
    url = message.text.strip()
    if not any(x in url for x in ["youtube.com", "youtu.be", "tiktok.com", "instagram.com"]):
        await message.answer("YouTube, TikTok yoki Instagram linki yuboring!")
        return

    wait = await message.answer("Video yuklanmoqda, kuting...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "outtmpl": tmpdir + "/video.%(ext)s",
                "format": "best[filesize<50M]/best",
                "quiet": True,
                "merge_output_format": "mp4",
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "Video")
                artist = info.get("uploader", "")
                filepath = None
                for f in os.listdir(tmpdir):
                    filepath = os.path.join(tmpdir, f)
                    break

            if filepath is None:
                await bot.edit_message_text("Video topilmadi!", message.chat.id, wait.message_id)
                return

            if os.path.getsize(filepath) > 50 * 1024 * 1024:
                await bot.edit_message_text("Video 50MB dan katta!", message.chat.id, wait.message_id)
                return

            # Shazam bilan qoshiq aniqlash
            shazam_info = await shazam.recognize(filepath)
            track = shazam_info.get("track")

            await bot.delete_message(message.chat.id, wait.message_id)

            # Videoni yuborish
            with open(filepath, "rb") as vf:
                await message.answer_video(vf, caption="🎬 " + title, supports_streaming=True)

            # Qoshiq topilsa chiqarish
            if track:
                song_title = track.get("title", title)
                song_artist = track.get("subtitle", artist)
                cover = track.get("images", {}).get("coverarthq", "")

                yt_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(song_artist + " " + song_title)
                yt_remix = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(song_artist + " " + song_title + " remix")
                spot_url = "https://open.spotify.com/search/" + urllib.parse.quote(song_artist + " " + song_title)

                text = (
                    "🎵 " + song_title + "\n"
                    "👤 " + song_artist + "\n\n"
                    "🎬 [YouTube Original](" + yt_url + ")\n"
                    "🔴 [YouTube Remix](" + yt_remix + ")\n"
                    "🟢 [Spotify](" + spot_url + ")"
                )

                if cover:
                    await message.answer_photo(cover, caption=text, parse_mode="Markdown")
                else:
                    await message.answer(text, parse_mode="Markdown")
            else:
                yt_search = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(title)
                await message.answer(
                    "Qoshiq aniqlanmadi, lekin qidirish:\n"
                    "[YouTube da qidirish](" + yt_search + ")",
                    parse_mode="Markdown"
                )

    except Exception as e:
        logger.error("Xato: " + str(e))
        try:
            await bot.edit_message_text("Xatolik yuz berdi. Qayta urining.", message.chat.id, wait.message_id)
        except:
            await message.answer("Xatolik yuz berdi.")


async def recognize_and_reply(message: types.Message, file_id: str, ext: str):
    wait = await message.answer("Qoshiq aniqlanmoqda...")
    try:
        file = await bot.get_file(file_id)
        file_data = await bot.download_file(file.file_path)

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_data.read())
            tmp_path = tmp.name

        result = await shazam.recognize(tmp_path)
        os.unlink(tmp_path)

        track = result.get("track")
        if not track:
            await bot.edit_message_text("Qoshiq aniqlanmadi. Boshqa audio yuboring.", message.chat.id, wait.message_id)
            return

        title = track.get("title", "Noma'lum")
        artist = track.get("subtitle", "Noma'lum")
        cover = track.get("images", {}).get("coverarthq", "")

        yt_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(artist + " " + title)
        yt_remix = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(artist + " " + title + " remix")
        spot_url = "https://open.spotify.com/search/" + urllib.parse.quote(artist + " " + title)

        text = (
            "🎵 " + title + "\n"
            "👤 " + artist + "\n\n"
            "🎬 [YouTube Original](" + yt_url + ")\n"
            "🔴 [YouTube Remix](" + yt_remix + ")\n"
            "🟢 [Spotify](" + spot_url + ")"
        )

        await bot.delete_message(message.chat.id, wait.message_id)

        if cover:
            await message.answer_photo(cover, caption=text, parse_mode="Markdown")
        else:
            await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error("Shazam xato: " + str(e))
        try:
            await bot.edit_message_text("Xatolik yuz berdi.", message.chat.id, wait.message_id)
        except:
            await message.answer("Xatolik yuz berdi.")


@dp.message(F.voice)
async def handle_voice(message: types.Message):
    await recognize_and_reply(message, message.voice.file_id, ".ogg")


@dp.message(F.audio)
async def handle_audio(message: types.Message):
    await recognize_and_reply(message, message.audio.file_id, ".mp3")


@dp.message(F.video)
async def handle_video(message: types.Message):
    await recognize_and_reply(message, message.video.file_id, ".mp4")


@dp.message(F.video_note)
async def handle_video_note(message: types.Message):
    await recognize_and_reply(message, message.video_note.file_id, ".mp4")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

