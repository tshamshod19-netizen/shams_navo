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

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
shazam = Shazam()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Salom! Musiqa botiman!\n\n"
        "Yuboring:\n"
        "- YouTube/TikTok linki\n"
        "- Ovozli xabar\n"
        "- Audio yoki video fayl"
    )


def make_music_text(title, artist):
    q = urllib.parse.quote(artist + " " + title)
    yt = "https://www.youtube.com/results?search_query=" + q
    remix = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(artist + " " + title + " remix")
    spot = "https://open.spotify.com/search/" + q
    return "🎵 " + title + "\n👤 " + artist + "\n\n🎬 [YouTube](" + yt + ")\n🔴 [Remix](" + remix + ")\n🟢 [Spotify](" + spot + ")"


@dp.message(F.text)
async def handle_link(message: types.Message):
    url = message.text.strip()
    if not any(x in url for x in ["youtube.com", "youtu.be", "tiktok.com", "instagram.com"]):
        await message.answer("YouTube yoki TikTok linki yuboring!")
        return

    wait = await message.answer("Video yuklanmoqda...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Avval faqat audio yuklab Shazam uchun
            audio_opts = {
                "outtmpl": tmpdir + "/audio.%(ext)s",
                "format": "worstaudio/worst",
                "quiet": True,
                "no_warnings": True,
            }
            song_title = "Video"
            song_artist = ""
            cover = ""

            try:
                with yt_dlp.YoutubeDL(audio_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    song_title = info.get("title", "Video")

                audio_path = None
                for f in os.listdir(tmpdir):
                    audio_path = os.path.join(tmpdir, f)
                    break

                if audio_path:
                    shazam_result = await shazam.recognize(audio_path)
                    track = shazam_result.get("track")
                    if track:
                        song_title = track.get("title", song_title)
                        song_artist = track.get("subtitle", "")
                        cover = track.get("images", {}).get("coverarthq", "")
            except Exception as e:
                logger.warning("Audio xato: " + str(e))

            # Video yuklab yuborish
            video_opts = {
                "outtmpl": tmpdir + "/video.%(ext)s",
                "format": "best[ext=mp4][filesize<45M]/best[filesize<45M]",
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(video_opts) as ydl:
                ydl.extract_info(url, download=True)

            video_path = None
            for f in os.listdir(tmpdir):
                if "video" in f:
                    video_path = os.path.join(tmpdir, f)
                    break

            if not video_path:
                for f in os.listdir(tmpdir):
                    p = os.path.join(tmpdir, f)
                    if os.path.getsize(p) > 100000:
                        video_path = p
                        break

            await bot.delete_message(message.chat.id, wait.message_id)

            if video_path and os.path.exists(video_path):
                with open(video_path, "rb") as vf:
                    await message.answer_video(vf, caption="🎬 " + song_title, supports_streaming=True)

            if song_artist:
                text = make_music_text(song_title, song_artist)
                if cover:
                    await message.answer_photo(cover, caption=text, parse_mode="Markdown")
                else:
                    await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(str(e))
        try:
            await bot.edit_message_text("Xatolik: " + str(e)[:200], message.chat.id, wait.message_id)
        except Exception:
            await message.answer("Xatolik yuz berdi.")


async def recognize_and_reply(message: types.Message, file_id: str, ext: str):
    wait = await message.answer("Qoshiq aniqlanmoqda...")
    try:
        file = await bot.get_file(file_id)
        data = await bot.download_file(file.file_path)

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(data.read())
            tmp_path = tmp.name

        result = await shazam.recognize(tmp_path)
        os.unlink(tmp_path)

        track = result.get("track")
        if not track:
            await bot.edit_message_text("Qoshiq aniqlanmadi.", message.chat.id, wait.message_id)
            return

        title = track.get("title", "Noma'lum")
        artist = track.get("subtitle", "Noma'lum")
        cover = track.get("images", {}).get("coverarthq", "")
        text = make_music_text(title, artist)

        await bot.delete_message(message.chat.id, wait.message_id)

        if cover:
            await message.answer_photo(cover, caption=text, parse_mode="Markdown")
        else:
            await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(str(e))
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

