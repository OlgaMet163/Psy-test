import logging
from pathlib import Path

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot import dependencies
from bot.handlers.hexaco import format_results_message
from bot.handlers.svs import format_group_results, format_value_results
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
    "Добро пожаловать! 🔮\n\n"
    "<b>Этот бот предлагает 3 психологических теста:</b>\n"
    "• HEXACO\n"
    "• Ценностный опросник Шварца (SVS)\n"
    "• Hogan DSUSI-SF\n\n"
    "Все три суммарно занимают ~15–20 минут. Отвечайте, исходя из того, какое поведение "
    "характерно для вас в последние 2–3 месяца. После завершения тестов вы получите текстовые "
    "выводы о себе и графики по метрикам.\n\nПри прохождении теста можно делать паузы — "
    "ответы сохраняются, результаты всегда доступны в меню."
)

WELCOME_GIF_PATH = Path(__file__).resolve().parent.parent / "assets" / "welcome.gif"

HEXACO_RESULTS_COMMANDS = {
    "результаты hexaco",
    "hexaco results",
    "📊 hexaco results",
    "📊 результаты hexaco",
}
HOGAN_RESULTS_COMMANDS = {
    "результаты hogan",
    "hogan results",
    "📊 hogan results",
    "📊 результаты hogan",
}
SVS_RESULTS_COMMANDS = {
    "результаты svs",
    "svs results",
    "📊 svs results",
    "📊 результаты svs",
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
    await _send_welcome(message, hexaco_ready, hogan_ready, svs_ready)


@start_router.message(lambda m: m.text and m.text.lower() in HEXACO_RESULTS_COMMANDS)
async def handle_show_hexaco_results(message: Message) -> None:
    storage = dependencies.storage_gateway
    if not storage:
        await message.answer("Хранилище недоступно, попробуйте позже.")
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
            "Результатов HEXACO пока нет. Сначала пройдите тест.",
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
            caption="<b>Диаграмма HEXACO</b>",
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
        await message.answer("Хранилище недоступно, попробуйте позже.")
        return
    user_id = message.from_user.id
    hexaco_ready = await _has_results(user_id, "HEXACO")
    hogan_ready = await _has_results(user_id, "HOGAN")
    svs_ready = await _has_results(user_id, "SVS")

    report = await storage.fetch_latest_hogan_report(message.from_user.id)
    if not report or not report.scales:
        await message.answer(
            "Результатов Hogan пока нет. Сначала пройдите тест.",
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
        chunks = ["Результатов Hogan пока нет."]
    if radar_path:
        await message.answer_photo(
            FSInputFile(radar_path),
            caption="<b>Диаграмма Hogan DSUSI-SF</b>",
        )
    for chunk in chunks:
        await message.answer(chunk)
    if keyboard:
        await message.answer("Расширенные выводы Hogan:", reply_markup=keyboard)
    await message.answer(
        "В любое время можно вернуться в меню.",
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
    await _send_welcome(message, hexaco_ready, hogan_ready, svs_ready)


@start_router.message(lambda m: m.text and m.text.lower() in SVS_RESULTS_COMMANDS)
async def handle_show_svs_results(message: Message) -> None:
    storage = dependencies.storage_gateway
    if not storage:
        await message.answer("Хранилище недоступно, попробуйте позже.")
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
            "Результатов SVS пока нет. Сначала пройдите тест.",
            reply_markup=main_menu_keyboard(hexaco_ready, hogan_ready, False),
        )
        return
    value_results = [r for r in public_results if r.category == "value"]
    group_results = [r for r in public_results if r.category == "group"]
    group_text = format_group_results(group_results)
    value_texts = format_value_results(value_results)
    radar_path = None
    try:
        radar_path = build_svs_radar(radar_results)
    except Exception as exc:  # pragma: no cover
        logging.exception("Failed to build SVS radar: %s", exc)
        radar_path = None
    if radar_path:
        await message.answer_photo(
            FSInputFile(radar_path),
            caption="<b>Диаграмма SVS</b>",
        )
    messages: List[str] = []
    if group_text:
        messages.append(group_text)
    messages.extend(value_texts)
    if not messages:
        messages.append("Результатов SVS пока нет.")

    last_idx = len(messages) - 1
    for idx, text in enumerate(messages):
        reply_markup = (
            main_menu_keyboard(hexaco_ready, hogan_ready, svs_ready)
            if idx == last_idx
            else None
        )
        await message.answer(text, reply_markup=reply_markup)
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


async def _send_welcome(
    message: Message, hexaco_ready: bool, hogan_ready: bool, svs_ready: bool
) -> None:
    keyboard = main_menu_keyboard(hexaco_ready, hogan_ready, svs_ready)
    if WELCOME_GIF_PATH.exists():
        await message.answer_animation(
            animation=FSInputFile(WELCOME_GIF_PATH),
            caption=WELCOME_TEXT,
            reply_markup=keyboard,
        )
    else:
        await message.answer(WELCOME_TEXT, reply_markup=keyboard)
