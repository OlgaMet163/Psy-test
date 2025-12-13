from __future__ import annotations

import random
from typing import Dict, List

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, FSInputFile

from bot import dependencies
from bot.keyboards import (
    build_hexaco_keyboard,
    get_hexaco_label,
    build_main_inline_menu,
)
from bot.utils.text import build_progress_bar
from bot.utils.plot import build_hexaco_radar

hexaco_router = Router(name="hexaco")
CALLBACK_PREFIX = "hexaco"
HEXACO_ORDER = (
    "honesty_humility",
    "neurotism",
    "extraversion",
    "agreeableness",
    "conscientiousness",
    "openness",
)
HEXACO_TEXT_TRIGGERS = {
    "начать hexaco",
    "перепройти hexaco",
    "start hexaco",
    "restart hexaco",
    "hexaco",
    "🚀 start hexaco",
    "🔁 restart hexaco",
    "🚀 начать hexaco",
    "🔁 перепройти hexaco",
}


class HexacoStates(StatesGroup):
    answering = State()


async def _track_activity(user_id: int) -> None:
    storage = dependencies.storage_gateway
    if storage:
        await storage.record_user_activity(user_id)


async def _increment_undo(user_id: int) -> None:
    storage = dependencies.storage_gateway
    if storage:
        await storage.increment_undo(user_id)


def _ensure_engine():
    if dependencies.hexaco_engine is None:
        raise RuntimeError("HexacoEngine is not initialized.")
    return dependencies.hexaco_engine


def _ensure_storage():
    return dependencies.storage_gateway


@hexaco_router.message(Command("hexaco"))
@hexaco_router.message(lambda m: m.text and m.text.lower() in HEXACO_TEXT_TRIGGERS)
async def start_hexaco(message: Message, state: FSMContext) -> None:
    await _track_activity(message.from_user.id)
    current_state = await state.get_state()
    if current_state:
        # Если уже в Big Five — не перезапускаем, а просим продолжить.
        if str(current_state).startswith("HexacoStates"):
            await message.answer(
                "Big Five уже идёт. Продолжайте отвечать с помощью кнопок ниже."
            )
            return
        # Если другой тест — блокируем.
        await message.answer(
            "Сейчас идёт другой тест. Завершите его или отправьте /reset."
        )
        return
    engine = _ensure_engine()
    order = list(range(engine.total_questions()))
    random.shuffle(order)
    await state.set_state(HexacoStates.answering)
    intro = await message.answer(
        (
            "<b>Big Five</b>: оценивайте утверждения, исходя из своего обычного "
            "поведения."
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.update_data(
        index=0, answers={}, order=order, intro_message_id=intro.message_id
    )
    await _send_question(message, engine, order, 0, {})


@hexaco_router.callback_query(
    HexacoStates.answering, F.data.startswith(f"{CALLBACK_PREFIX}:")
)
async def handle_answer(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id)
    engine = _ensure_engine()
    state_data = await state.get_data()
    index = state_data.get("index", 0)
    answers: Dict[int, int] = state_data.get("answers", {})
    order: List[int] = state_data.get("order") or list(range(engine.total_questions()))
    if index >= len(order):
        await callback.answer("Ответы уже заполнены.", show_alert=True)
        return
    statement = engine.get_statement(order[index])

    payload = callback.data.split(":")[1] if ":" in callback.data else ""
    if payload == "back":
        await _go_prev_question(callback, state, engine)
        return
    try:
        raw_value = int(payload)
    except ValueError:
        await callback.answer()
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
            test_name="HEXACO",
            statement_id=statement.id,
            raw_value=raw_value,
            label=get_hexaco_label(statement.id, raw_value),
        )

    if index + 1 >= len(order):
        await _finish(callback, state, answers, engine)
        return

    await _send_question(callback.message, engine, order, index + 1, answers)


async def _send_question(
    message: Message,
    engine,
    order: List[int],
    index: int,
    answers: Dict[int, int] | None = None,
) -> None:
    statement = engine.get_statement(order[index])
    total = len(order)
    selected = (answers or {}).get(statement.id)
    await message.answer(
        f"<b>Вопрос {index + 1}/{total}</b>\n\n{statement.text}",
        reply_markup=build_hexaco_keyboard(
            CALLBACK_PREFIX, statement.id, selected_value=selected, add_back=True
        ),
    )


async def _go_prev_question(
    callback: CallbackQuery, state: FSMContext, engine
) -> None:
    await _increment_undo(callback.from_user.id)
    state_data = await state.get_data()
    answers: Dict[int, int] = state_data.get("answers", {})
    order: List[int] = state_data.get("order") or list(range(engine.total_questions()))
    if not order:
        await callback.answer("Тест недоступен, попробуйте позже.", show_alert=True)
        return
    index = state_data.get("index", 0)
    new_index = max(0, min(len(order) - 1, index - 1))
    await state.update_data(index=new_index, answers=answers, order=order)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _send_question(callback.message, engine, order, new_index, answers)
    await callback.answer()


async def _finish(
    callback: CallbackQuery, state: FSMContext, answers: Dict[int, int], engine
) -> None:
    results = engine.calculate(answers)
    public_results = sorted(
        [result for result in results if result.visibility == "public"],
        key=lambda item: item.percent,
        reverse=True,
    )
    visible_results = _filter_hexaco_domains(public_results, include_hh=False)
    if not visible_results:
        await callback.message.answer("Результатов Big Five пока нет.")
        await state.clear()
        return

    radar_results = _order_hexaco_for_radar(visible_results, include_hh=False)
    message_text = format_results_message(visible_results, include_hh=False)
    radar_path = None
    try:
        radar_path = build_hexaco_radar(radar_results)
    except Exception:
        radar_path = None

    storage = _ensure_storage()
    hogan_has_results = False
    svs_has_results = False
    if storage:
        await storage.save_results(callback.from_user.id, "HEXACO", results)
        hogan_has_results = await storage.has_results(callback.from_user.id, "HOGAN")
        svs_has_results = await storage.has_results(callback.from_user.id, "SVS")

    if radar_path:
        await callback.message.answer_photo(
            FSInputFile(radar_path),
            caption="<b>Диаграмма Big Five</b>",
        )

    # Удаляем вступительное сообщение, если оно устарело.
    intro_message_id = (await state.get_data()).get("intro_message_id")
    if intro_message_id:
        try:
            await callback.message.bot.delete_message(
                chat_id=callback.message.chat.id, message_id=intro_message_id
            )
        except Exception:
            pass

    await callback.message.answer(
        message_text,
        reply_markup=build_main_inline_menu(True, hogan_has_results, svs_has_results),
    )
    if radar_path:
        try:
            radar_path.unlink(missing_ok=True)
        except Exception:
            pass
    await state.clear()


def format_results_message(
    results: List["HexacoResult"], include_hh: bool = False
) -> str:
    filtered = _filter_hexaco_domains(results, include_hh=include_hh)
    if not filtered:
        return "Результатов Big Five пока нет."
    ordered = sorted(filtered, key=lambda item: item.percent, reverse=True)
    text_lines: list[str] = []
    for result in ordered:
        bar = build_progress_bar(result.percent, result.band_id)
        text_lines.append(
            f"• <b>{result.title}</b>: {result.percent}% ({result.band_label})\n"
            f"{bar}\n"
            f"{result.interpretation}"
        )
    return "\n\n".join(text_lines)


def _order_hexaco_for_radar(
    results: List["HexacoResult"], include_hh: bool = False
) -> List["HexacoResult"]:
    filtered = _filter_hexaco_domains(results, include_hh=include_hh)
    if not filtered:
        return []
    order_index = {domain_id: idx for idx, domain_id in enumerate(HEXACO_ORDER)}
    return sorted(
        filtered, key=lambda item: order_index.get(item.domain_id, len(HEXACO_ORDER))
    )


def _filter_hexaco_domains(
    results: List["HexacoResult"], include_hh: bool = False
) -> List["HexacoResult"]:
    if include_hh:
        return results
    return [
        result for result in results if getattr(result, "domain_id", "") != "honesty_humility"
    ]
