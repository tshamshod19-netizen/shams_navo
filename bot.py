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

if name == "main":
    asyncio.run(main())
