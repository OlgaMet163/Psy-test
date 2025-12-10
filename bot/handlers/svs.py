from __future__ import annotations

import random
from typing import Dict, List, Sequence, Tuple

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, FSInputFile

from bot import dependencies
from bot.keyboards import build_svs_keyboard, get_svs_label, main_menu_keyboard
from bot.services.svs import SvsResult
from bot.utils.text import build_progress_bar
from bot.utils.plot import build_svs_radar

svs_router = Router(name="svs")
CALLBACK_PREFIX = "svs"
SVS_VALUE_ORDER = ("SD", "ST", "HE", "AC", "PO", "SEC", "CO", "TR", "BE", "UN")
SVS_TEXT_TRIGGERS = {
    "начать svs",
    "перепройти svs",
    "start svs",
    "restart svs",
    "svs",
    "🚀 start svs",
    "🔁 restart svs",
    "🚀 начать svs",
    "🔁 перепройти svs",
}


class SvsStates(StatesGroup):
    answering = State()


def _ensure_engine():
    if dependencies.svs_engine is None:
        raise RuntimeError("SvsEngine is not initialized.")
    return dependencies.svs_engine


def _ensure_storage():
    return dependencies.storage_gateway


@svs_router.message(Command("svs"))
@svs_router.message(lambda m: m.text and m.text.lower() in SVS_TEXT_TRIGGERS)
async def start_svs(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state:
        if str(current_state).startswith("SvsStates"):
            await message.answer(
                "SVS уже идёт. Продолжайте отвечать с помощью кнопок ниже."
            )
            return
        await message.answer(
            "Сейчас идёт другой тест. Завершите его или отправьте /reset."
        )
        return
    engine = _ensure_engine()
    order = list(range(engine.total_questions()))
    random.shuffle(order)
    await state.set_state(SvsStates.answering)
    await state.update_data(index=0, answers={}, order=order)
    await message.answer(
        "Ценностный опросник Шварца (20 утверждений, шкала 1–7). Оцените, насколько каждое утверждение про вас.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await _send_question(message, engine, order, 0)


@svs_router.callback_query(
    SvsStates.answering, F.data.startswith(f"{CALLBACK_PREFIX}:")
)
async def handle_answer(callback: CallbackQuery, state: FSMContext) -> None:
    engine = _ensure_engine()
    state_data = await state.get_data()
    index = state_data.get("index", 0)
    answers: Dict[int, int] = state_data.get("answers", {})
    order: List[int] = state_data.get("order") or list(range(engine.total_questions()))
    if index >= len(order):
        await callback.answer("Ответы уже заполнены.", show_alert=True)
        return
    statement = engine.get_statement(order[index])

    try:
        raw_value = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Не удалось распознать ответ.", show_alert=True)
        return

    answers[statement.id] = raw_value
    await state.update_data(index=index + 1, answers=answers)
    await callback.answer("Сохранено ✅")
    try:
        await callback.message.delete()
    except Exception:
        pass

    storage = _ensure_storage()
    if storage:
        await storage.save_answer(
            user_id=callback.from_user.id,
            test_name="SVS",
            statement_id=statement.id,
            raw_value=raw_value,
            label=get_svs_label(raw_value),
        )

    if index + 1 >= len(order):
        await _finish(callback, state, answers, engine)
        return

    await _send_question(callback.message, engine, order, index + 1)


async def _send_question(
    message: Message, engine, order: List[int], index: int
) -> None:
    statement = engine.get_statement(order[index])
    total = len(order)
    await message.answer(
        f"Вопрос {index + 1}/{total}\n\n{statement.text}",
        reply_markup=build_svs_keyboard(CALLBACK_PREFIX),
    )


async def _finish(
    callback: CallbackQuery, state: FSMContext, answers: Dict[int, int], engine
) -> None:
    results = engine.calculate(answers)
    ordered_results = sorted(results, key=lambda item: item.percent, reverse=True)
    radar_results = _order_svs_for_radar(results)
    value_results, group_results = _split_results(ordered_results)
    message_text = format_results_message(value_results, group_results)
    radar_path = None
    try:
        radar_path = build_svs_radar(radar_results)
    except Exception:
        radar_path = None

    storage = _ensure_storage()
    hexaco_has_results = False
    hogan_has_results = False
    if storage:
        await storage.save_results(callback.from_user.id, "SVS", results)
        hexaco_has_results = await storage.has_results(callback.from_user.id, "HEXACO")
        hogan_has_results = await storage.has_results(callback.from_user.id, "HOGAN")

    if radar_path:
        await callback.message.answer_photo(
            FSInputFile(radar_path),
            caption="<b>Диаграмма SVS</b>",
        )

    await callback.message.answer(
        message_text,
        reply_markup=main_menu_keyboard(hexaco_has_results, hogan_has_results, True),
    )
    if radar_path:
        try:
            radar_path.unlink(missing_ok=True)
        except Exception:
            pass
    await state.clear()


def _split_results(
    results: Sequence[SvsResult],
) -> Tuple[List[SvsResult], List[SvsResult]]:
    values = [item for item in results if item.category == "value"]
    groups = [item for item in results if item.category == "group"]
    return values, groups


def _order_svs_for_radar(results: Sequence[SvsResult]) -> List[SvsResult]:
    order_index = {value_id: idx for idx, value_id in enumerate(SVS_VALUE_ORDER)}
    values = [item for item in results if item.category == "value"]
    others = [item for item in results if item.category != "value"]
    ordered_values = sorted(
        values, key=lambda item: order_index.get(item.domain_id, len(SVS_VALUE_ORDER))
    )
    return ordered_values + others


def format_results_message(
    values: Sequence[SvsResult], groups: Sequence[SvsResult]
) -> str:
    if not values and not groups:
        return "Результатов SVS пока нет."

    lines: List[str] = ["Ценностный опросник Шварца (SVS):"]
    if groups:
        lines.append("\nСводные группы:")
        ordered_groups = sorted(groups, key=lambda item: item.percent, reverse=True)
        for result in ordered_groups:
            bar = build_progress_bar(result.percent, result.band_id)
            lines.append(
                f"• <b>{result.title}</b>: {result.percent}% ({result.band_label})\n"
                f"{bar}\n"
                f"{result.interpretation}"
            )
    if values:
        lines.append("\nБазовые ценности:")
        ordered_values = sorted(values, key=lambda item: item.percent, reverse=True)
        for result in ordered_values:
            bar = build_progress_bar(result.percent, result.band_id)
            lines.append(
                f"• <b>{result.title} ({result.domain_id})</b>: {result.percent}% ({result.band_label})\n"
                f"{bar}\n"
                f"{result.interpretation}"
            )
    return "\n\n".join(lines)
