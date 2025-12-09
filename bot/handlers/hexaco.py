from __future__ import annotations

from typing import Dict, List

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot import dependencies
from bot.keyboards import build_hexaco_keyboard, get_hexaco_label, main_menu_keyboard
from bot.utils.text import build_progress_bar

hexaco_router = Router(name="hexaco")
CALLBACK_PREFIX = "hexaco"
HEXACO_TEXT_TRIGGERS = {
    "начать hexaco",
    "перепройти hexaco",
    "start hexaco",
    "restart hexaco",
    "hexaco",
    "🚀 start hexaco",
    "🔁 restart hexaco",
}


class HexacoStates(StatesGroup):
    answering = State()


def _ensure_engine():
    if dependencies.hexaco_engine is None:
        raise RuntimeError("HexacoEngine не инициализирован.")
    return dependencies.hexaco_engine


def _ensure_storage():
    return dependencies.storage_gateway


@hexaco_router.message(Command("hexaco"))
@hexaco_router.message(lambda m: m.text and m.text.lower() in HEXACO_TEXT_TRIGGERS)
async def start_hexaco(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state:
        # Если уже в HEXACO — не перезапускаем, а просим продолжить.
        if str(current_state).startswith("HexacoStates"):
            await message.answer(
                "HEXACO уже идёт. Продолжайте отвечать через кнопки под вопросами."
            )
            return
        # Если другой тест — блокируем.
        await message.answer(
            "Another assessment is already in progress. Finish it or send /reset."
        )
        return
    engine = _ensure_engine()
    await state.set_state(HexacoStates.answering)
    await state.update_data(index=0, answers={})
    await message.answer(
        (
            "HEXACO two-facet form: answer how often each statement is true for you, "
            "using the buttons below based on your typical behavior."
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    await _send_question(message, engine, 0)


@hexaco_router.callback_query(
    HexacoStates.answering, F.data.startswith(f"{CALLBACK_PREFIX}:")
)
async def handle_answer(callback: CallbackQuery, state: FSMContext) -> None:
    engine = _ensure_engine()
    state_data = await state.get_data()
    index = state_data.get("index", 0)
    answers: Dict[int, int] = state_data.get("answers", {})
    statement = engine.get_statement(index)

    raw_value = int(callback.data.split(":")[1])
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
            test_name="HEXACO",
            statement_id=statement.id,
            raw_value=raw_value,
            label=get_hexaco_label(statement.id, raw_value),
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
        reply_markup=build_hexaco_keyboard(CALLBACK_PREFIX, statement.id),
    )


async def _finish(
    callback: CallbackQuery, state: FSMContext, answers: Dict[int, int], engine
) -> None:
    results = engine.calculate(answers)
    public_results = [result for result in results if result.visibility == "public"]
    message_text = format_results_message(public_results)

    storage = _ensure_storage()
    hogan_has_results = False
    svs_has_results = False
    if storage:
        await storage.save_results(callback.from_user.id, "HEXACO", results)
        hogan_has_results = await storage.has_results(callback.from_user.id, "HOGAN")
        svs_has_results = await storage.has_results(callback.from_user.id, "SVS")

    await callback.message.answer(
        message_text,
        reply_markup=main_menu_keyboard(True, hogan_has_results, svs_has_results),
    )
    await state.clear()


def format_results_message(results: List["HexacoResult"]) -> str:
    if not results:
        return "No HEXACO results yet."
    text_lines = ["HEXACO results:"]
    for result in results:
        bar = build_progress_bar(result.percent, result.band_id)
        text_lines.append(
            f"• <b>{result.title}</b>: {result.percent}% ({result.band_label})\n"
            f"{bar}\n"
            f"{result.interpretation}"
        )
    return "\n\n".join(text_lines)
