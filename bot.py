import urllib.parse
        yt_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(f"{artist} {title}")
        yt_remix = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(f"{artist} {title} remix")
        spot_url = "https://open.spotify.com/search/" + urllib.parse.quote(f"{artist} {title}")

        text = (
            f"🎵 *{title}*\n"
            f"👤 {artist}\n\n"
            f"🎬 [YouTube Original]({yt_url})\n"
            f"🔴 [YouTube Remix]({yt_remix})\n"
            f"🟢 [Spotify]({spot_url})"
        )

        await bot.delete_message(message.chat.id, wait.message_id)

        if cover:
            await message.answer_photo(cover, caption=text, parse_mode="Markdown")
        else:
            await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Shazam xato: {e}")
        await bot.edit_message_text("⚠️ Xatolik yuz berdi.", message.chat.id, wait.message_id)


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


# ── ISHGA TUSHIRISH ───────────────────────────────
async def main():
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
