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
from bot.services.hogan import HoganReport, SCALE_DEFINITIONS
from bot.services.hexaco import HexacoResult
from bot.services.svs import SvsResult
from bot.keyboards import main_menu_keyboard
from aiogram.types import FSInputFile
from bot.utils.plot import (
    build_hogan_radar,
    build_hexaco_radar,
    build_svs_radar,
)

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
HEXACO_ORDER = (
    "honesty_humility",
    "neurotism",
    "extraversion",
    "agreeableness",
    "conscientiousness",
    "openness",
)
HOGAN_ORDER = [scale.id for scale in SCALE_DEFINITIONS]
SVS_VALUE_ORDER = ("SD", "ST", "HE", "AC", "PO", "SEC", "CO", "TR", "BE", "UN")


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
    public_results = sorted(
        [r for r in results if r.visibility == "public"],
        key=lambda item: item.percent,
        reverse=True,
    )
    radar_results = _order_hexaco_for_radar(public_results)
    if not public_results:
        await message.answer(
            "No HEXACO results yet. Run the assessment first.",
            reply_markup=main_menu_keyboard(False, hogan_ready, svs_ready),
        )
        return
    radar_path = None
    try:
        radar_path = build_hexaco_radar(radar_results)
    except Exception as exc:  # pragma: no cover
        logging.exception("Failed to build HEXACO radar: %s", exc)
        radar_path = None
    if radar_path:
        await message.answer_photo(
            FSInputFile(radar_path),
            caption="<b>HEXACO radar</b>",
        )
    await message.answer(
        format_results_message(public_results),
        reply_markup=main_menu_keyboard(hexaco_ready, hogan_ready, svs_ready),
    )
    if radar_path:
        try:
            radar_path.unlink(missing_ok=True)
        except Exception:
            pass


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

    ordered_scales = sorted(report.scales, key=lambda item: item.percent, reverse=True)
    ordered_report = HoganReport(
        scales=ordered_scales, impression_management=report.impression_management
    )
    radar_scales = _order_hogan_for_radar(report.scales)
    keyboard = build_hogan_results_keyboard(ordered_scales)
    chunks = build_hogan_results_chunks(ordered_report)
    radar_path = None
    try:
        radar_path = build_hogan_radar(radar_scales)
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
    await message.answer("History cleared.")
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
    public_results = sorted(
        [r for r in results if r.visibility == "public"],
        key=lambda item: item.percent,
        reverse=True,
    )
    radar_results = _order_svs_for_radar(public_results)
    if not public_results:
        await message.answer(
            "No SVS results yet. Run the assessment first.",
            reply_markup=main_menu_keyboard(hexaco_ready, hogan_ready, False),
        )
        return
    value_results = [r for r in public_results if r.category == "value"]
    group_results = [r for r in public_results if r.category == "group"]
    radar_path = None
    try:
        radar_path = build_svs_radar(radar_results)
    except Exception as exc:  # pragma: no cover
        logging.exception("Failed to build SVS radar: %s", exc)
        radar_path = None
    if radar_path:
        await message.answer_photo(
            FSInputFile(radar_path),
            caption="<b>SVS radar</b>",
        )
    await message.answer(
        format_svs_results_message(value_results, group_results),
        reply_markup=main_menu_keyboard(hexaco_ready, hogan_ready, svs_ready),
    )
    if radar_path:
        try:
            radar_path.unlink(missing_ok=True)
        except Exception:
            pass


async def _has_results(user_id: int, test_name: str) -> bool:
    storage = dependencies.storage_gateway
    if not storage:
        return False
    return await storage.has_results(user_id, test_name)


def _order_hexaco_for_radar(results: list[HexacoResult]) -> list[HexacoResult]:
    order_index = {domain_id: idx for idx, domain_id in enumerate(HEXACO_ORDER)}
    return sorted(
        results, key=lambda item: order_index.get(item.domain_id, len(HEXACO_ORDER))
    )


def _order_hogan_for_radar(scales) -> list:
    order_index = {scale_id: idx for idx, scale_id in enumerate(HOGAN_ORDER)}
    return sorted(
        [scale for scale in scales if scale.scale_id != "IM"],
        key=lambda item: order_index.get(item.scale_id, len(HOGAN_ORDER)),
    )


def _order_svs_for_radar(results: list[SvsResult]) -> list[SvsResult]:
    order_index = {value_id: idx for idx, value_id in enumerate(SVS_VALUE_ORDER)}
    values = [r for r in results if r.category == "value"]
    others = [r for r in results if r.category != "value"]
    ordered_values = sorted(
        values, key=lambda item: order_index.get(item.domain_id, len(SVS_VALUE_ORDER))
    )
    return ordered_values + others
