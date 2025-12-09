import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot import dependencies
from bot.handlers.hexaco import format_results_message
from bot.handlers.svs import format_results_message as format_svs_results_message
from bot.handlers.hogan import (
    build_hogan_results_chunks,
    build_hogan_results_keyboard,
)
from bot.keyboards import main_menu_keyboard
from aiogram.types import FSInputFile
from bot.utils.plot import build_hogan_radar

start_router = Router(name="start")

WELCOME_TEXT = (
    "Hi 👋\n\n"
    "This bot currently contains three assessments:\n"
    "• HEXACO two-facet (24 items, 1–5 scale, live scoring)\n"
    "• Schwartz Value Survey (20 items, 1–7 scale, core values + 4 higher-order themes)\n"
    "• Hogan DSUSI-SF (11 stress derailers + Hogan coaching / career snippets)\n\n"
    "Answer based on real behavior. You can pause any time—results stay saved and you can request "
    "them again via the menu buttons."
)

HEXACO_RESULTS_COMMANDS = {
    "результаты hexaco",
    "hexaco results",
    "📊 hexaco results",
}
HOGAN_RESULTS_COMMANDS = {
    "результаты hogan",
    "hogan results",
    "📊 hogan results",
}
SVS_RESULTS_COMMANDS = {
    "результаты svs",
    "svs results",
    "📊 svs results",
}
RESET_COMMANDS = {"/reset", "/cancel", "reset", "cancel", "сброс"}


@start_router.message(CommandStart())
async def handle_start(message: Message) -> None:
    hexaco_ready = await _has_results(message.from_user.id, "HEXACO")
    hogan_ready = await _has_results(message.from_user.id, "HOGAN")
    svs_ready = await _has_results(message.from_user.id, "SVS")
    await message.answer(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard(hexaco_ready, hogan_ready, svs_ready),
    )


@start_router.message(lambda m: m.text and m.text.lower() in HEXACO_RESULTS_COMMANDS)
async def handle_show_hexaco_results(message: Message) -> None:
    storage = dependencies.storage_gateway
    if not storage:
        await message.answer("Storage is unavailable, please try again later.")
        return
    user_id = message.from_user.id
    hexaco_ready = await _has_results(user_id, "HEXACO")
    hogan_ready = await _has_results(user_id, "HOGAN")
    svs_ready = await _has_results(user_id, "SVS")
    results = await storage.fetch_latest_hexaco_results(message.from_user.id)
    public_results = [r for r in results if r.visibility == "public"]
    if not public_results:
        await message.answer(
            "No HEXACO results yet. Run the assessment first.",
            reply_markup=main_menu_keyboard(False, hogan_ready, svs_ready),
        )
        return
    await message.answer(
        format_results_message(public_results),
        reply_markup=main_menu_keyboard(hexaco_ready, hogan_ready, svs_ready),
    )


@start_router.message(lambda m: m.text and m.text.lower() in HOGAN_RESULTS_COMMANDS)
async def handle_show_hogan_results(message: Message) -> None:
    storage = dependencies.storage_gateway
    if not storage:
        await message.answer("Storage is unavailable, please try again later.")
        return
    user_id = message.from_user.id
    hexaco_ready = await _has_results(user_id, "HEXACO")
    hogan_ready = await _has_results(user_id, "HOGAN")
    svs_ready = await _has_results(user_id, "SVS")

    report = await storage.fetch_latest_hogan_report(message.from_user.id)
    if not report or not report.scales:
        await message.answer(
            "No Hogan results yet. Complete the assessment first.",
            reply_markup=main_menu_keyboard(hexaco_ready, False, svs_ready),
        )
        return

    keyboard = build_hogan_results_keyboard(report.scales)
    chunks = build_hogan_results_chunks(report)
    radar_path = None
    try:
        radar_path = build_hogan_radar(report.scales)
    except Exception as exc:  # pragma: no cover - diagnostics
        logging.exception("Failed to build Hogan radar: %s", exc)
        radar_path = None
    if not chunks:
        chunks = ["No Hogan results yet."]
    if radar_path:
        await message.answer_photo(
            FSInputFile(radar_path),
            caption="<b>Hogan DSUSI-SF radar</b>",
        )
    for chunk in chunks:
        await message.answer(chunk)
    if keyboard:
        await message.answer("Need Hogan insights?", reply_markup=keyboard)
    await message.answer(
        "Back to menu anytime.",
        reply_markup=main_menu_keyboard(hexaco_ready, hogan_ready, svs_ready),
    )
    if radar_path:
        try:
            radar_path.unlink(missing_ok=True)
        except Exception:
            pass


@start_router.message(lambda m: m.text and m.text.lower() in RESET_COMMANDS)
@start_router.message(Command("reset"))
@start_router.message(Command("cancel"))
async def handle_reset(message: Message, state) -> None:
    storage = dependencies.storage_gateway
    if storage:
        try:
            await storage.clear_user_data(message.from_user.id)
        except Exception:
            # даже если очистка не удалась, всё равно сбросим состояние
            pass
    await state.clear()
    hexaco_ready = await _has_results(message.from_user.id, "HEXACO")
    hogan_ready = await _has_results(message.from_user.id, "HOGAN")
    svs_ready = await _has_results(message.from_user.id, "SVS")
    await message.answer("История очищена.")
    await message.answer(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard(hexaco_ready, hogan_ready, svs_ready),
    )


@start_router.message(lambda m: m.text and m.text.lower() in SVS_RESULTS_COMMANDS)
async def handle_show_svs_results(message: Message) -> None:
    storage = dependencies.storage_gateway
    if not storage:
        await message.answer("Storage is unavailable, please try again later.")
        return
    user_id = message.from_user.id
    hexaco_ready = await _has_results(user_id, "HEXACO")
    hogan_ready = await _has_results(user_id, "HOGAN")
    svs_ready = await _has_results(user_id, "SVS")

    results = await storage.fetch_latest_svs_results(message.from_user.id)
    public_results = [r for r in results if r.visibility == "public"]
    if not public_results:
        await message.answer(
            "No SVS results yet. Run the assessment first.",
            reply_markup=main_menu_keyboard(hexaco_ready, hogan_ready, False),
        )
        return
    value_results = [r for r in public_results if r.category == "value"]
    group_results = [r for r in public_results if r.category == "group"]
    await message.answer(
        format_svs_results_message(value_results, group_results),
        reply_markup=main_menu_keyboard(hexaco_ready, hogan_ready, svs_ready),
    )


async def _has_results(user_id: int, test_name: str) -> bool:
    storage = dependencies.storage_gateway
    if not storage:
        return False
    return await storage.has_results(user_id, test_name)
