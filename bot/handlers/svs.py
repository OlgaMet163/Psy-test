from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot import dependencies
from bot.keyboards import build_svs_keyboard, get_svs_label, main_menu_keyboard
from bot.services.svs import SvsResult
from bot.utils.text import build_progress_bar

svs_router = Router(name="svs")
CALLBACK_PREFIX = "svs"
SVS_TEXT_TRIGGERS = {
    "начать svs",
    "перепройти svs",
    "start svs",
    "restart svs",
    "svs",
    "🚀 start svs",
    "🔁 restart svs",
}


class SvsStates(StatesGroup):
    answering = State()


def _ensure_engine():
    if dependencies.svs_engine is None:
        raise RuntimeError("SvsEngine не инициализирован.")
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
                "SVS уже идёт. Продолжайте отвечать через кнопки под вопросами."
            )
            return
        await message.answer(
            "Another assessment is already in progress. Finish it or send /reset."
        )
        return
    engine = _ensure_engine()
    await state.set_state(SvsStates.answering)
    await state.update_data(index=0, answers={})
    await message.answer(
        "Schwartz Value Survey (20 items, 1–7 scale). Rate how true each statement is for you.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await _send_question(message, engine, 0)


@svs_router.callback_query(
    SvsStates.answering, F.data.startswith(f"{CALLBACK_PREFIX}:")
)
async def handle_answer(callback: CallbackQuery, state: FSMContext) -> None:
    engine = _ensure_engine()
    state_data = await state.get_data()
    index = state_data.get("index", 0)
    answers: Dict[int, int] = state_data.get("answers", {})
    statement = engine.get_statement(index)

    try:
        raw_value = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Could not parse the answer.", show_alert=True)
        return

    answers[statement.id] = raw_value
    await state.update_data(index=index + 1, answers=answers)
    await callback.answer("Saved ✅")
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

    if index + 1 >= engine.total_questions():
        await _finish(callback, state, answers, engine)
        return

    await _send_question(callback.message, engine, index + 1)


async def _send_question(message: Message, engine, index: int) -> None:
    statement = engine.get_statement(index)
    total = engine.total_questions()
    await message.answer(
        f"Question {index + 1}/{total}\n\n{statement.text}",
        reply_markup=build_svs_keyboard(CALLBACK_PREFIX),
    )


async def _finish(
    callback: CallbackQuery, state: FSMContext, answers: Dict[int, int], engine
) -> None:
    results = engine.calculate(answers)
    value_results, group_results = _split_results(results)
    message_text = format_results_message(value_results, group_results)

    storage = _ensure_storage()
    hexaco_has_results = False
    hogan_has_results = False
    if storage:
        await storage.save_results(callback.from_user.id, "SVS", results)
        hexaco_has_results = await storage.has_results(callback.from_user.id, "HEXACO")
        hogan_has_results = await storage.has_results(callback.from_user.id, "HOGAN")

    await callback.message.answer(
        message_text,
        reply_markup=main_menu_keyboard(hexaco_has_results, hogan_has_results, True),
    )
    await state.clear()


def _split_results(
    results: Sequence[SvsResult],
) -> Tuple[List[SvsResult], List[SvsResult]]:
    values = [item for item in results if item.category == "value"]
    groups = [item for item in results if item.category == "group"]
    return values, groups


def format_results_message(
    values: Sequence[SvsResult], groups: Sequence[SvsResult]
) -> str:
    if not values and not groups:
        return "No SVS results yet."

    lines: List[str] = ["Schwartz Value Survey (SVS):"]
    if groups:
        lines.append("\nHigher-order themes:")
        for result in groups:
            bar = build_progress_bar(result.percent, result.band_id)
            lines.append(
                f"• <b>{result.title}</b>: {result.mean_score}/7 ({result.percent}% — {result.band_label})\n"
                f"{bar}\n"
                f"{result.interpretation}"
            )
    if values:
        lines.append("\nCore values:")
        for result in values:
            bar = build_progress_bar(result.percent, result.band_id)
            lines.append(
                f"• <b>{result.title} ({result.domain_id})</b>: {result.mean_score}/7 "
                f"({result.percent}% — {result.band_label})\n"
                f"{bar}\n"
                f"{result.interpretation}"
            )
    return "\n\n".join(lines)
