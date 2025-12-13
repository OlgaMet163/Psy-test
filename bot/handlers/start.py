import asyncio
import datetime as dt
import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
)

from bot import dependencies
from bot.handlers.hexaco import format_results_message, start_hexaco
from bot.handlers.svs import format_group_results, format_value_results, start_svs
from bot.handlers.hogan import build_hogan_results_chunks, start_hogan
from bot.utils.text import build_progress_bar
from bot.keyboards.common import build_main_inline_menu
import re
from typing import Dict, List, Sequence, Optional
from bot.services.hogan import HoganReport, SCALE_DEFINITIONS
from bot.services.hexaco import HexacoResult
from bot.services.svs import SvsResult
from aiogram.types import FSInputFile
from bot.utils.plot import (
    build_hogan_radar,
    build_hexaco_radar,
    build_svs_radar,
    build_dark_triad_radar,
)

start_router = Router(name="start")

START_CALLBACK = "start:begin"
ROLE_PARTICIPANT = "start:role:participant"
ROLE_STAFF = "start:role:staff"
TEST_HEXACO = "start:test:hexaco"
TEST_SVS = "start:test:svs"
TEST_HOGAN = "start:test:hogan"
TEST_VIEW_PARTICIPANT = "start:test:view_participant"
MENU_PREFIX = "menu:"
STAFF_FIND_ANOTHER = "staff:find_another"
STAFF_RETURN_MENU = "staff:return_menu"


class StartStates(StatesGroup):
    awaiting_begin = State()
    choosing_role = State()
    waiting_email = State()
    waiting_participant_email = State()
    waiting_participant_lookup = State()
    choosing_test = State()
    admin_waiting_password = State()
    admin_active = State()


WELCOME_TEXT = (
    "Добро пожаловать! 🔮\n\n"
    "<b>Этот бот предлагает 3 психологических теста:</b>\n"
    "• Пятифакторная модель характера (Big Five)\n"
    "• Ценностный опросник Шварца (SVS)\n"
    "• Поведенческий стиль в стрессе (на базе Hogan)\n\n"
    "Все три суммарно занимают ~15–20 минут. Отвечайте, исходя из того, какое поведение "
    "характерно для вас в последние 2–3 месяца. После завершения тестов вы получите текстовые "
    "выводы о себе и графики по метрикам.\n\nПри прохождении теста можно делать паузы — "
    "ответы сохраняются, результаты всегда доступны в меню."
)

WELCOME_GIF_PATH = Path(__file__).resolve().parent.parent / "assets" / "welcome.gif"

HEXACO_RESULTS_COMMANDS = {
    "результаты big five",
    "big five results",
    "📊 big five results",
    "📊 результаты big five",
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
TEAM_SWITCH_COMMANDS = {"teamswitch"}
ADMIN_PASSWORD = "1337"
ADMIN_STATS = "admin:stats"
ADMIN_EXPORT = "admin:export"
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
DARK_TRIAD_ORDER = ("dt_machiavellianism", "dt_narcissism", "dt_psychopathy")


async def _track_activity(user_id: int, username: str | None = None) -> None:
    storage = dependencies.storage_gateway
    if storage:
        await storage.record_user_activity(user_id, username=username)


@start_router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    await _track_activity(message.from_user.id, message.from_user.username)
    # гарантированно убираем старую клавиатуру до любых ответов
    await message.answer("…", reply_markup=ReplyKeyboardRemove())
    current_state = await state.get_state()
    if current_state and not str(current_state).startswith("StartStates"):
        await message.answer(
            "Сейчас идёт тест. Завершите его или отправьте /reset, чтобы начать заново."
        )
        return
    await state.set_state(StartStates.awaiting_begin)
    await _send_welcome(message)


@start_router.message(Command("teamswitch"))
@start_router.message(
    lambda m: m.text and m.text.strip().lower() in TEAM_SWITCH_COMMANDS
)
async def handle_team_switch(message: Message, state: FSMContext) -> None:
    await _track_activity(message.from_user.id, message.from_user.username)
    await state.clear()
    await message.answer("…", reply_markup=ReplyKeyboardRemove())
    await state.set_state(StartStates.choosing_test)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔍 Посмотреть участника",
                    callback_data=TEST_VIEW_PARTICIPANT,
                )
            ]
        ]
    )
    menu_msg = await message.answer(
        "Режим сотрудника. Доступно: посмотреть участника.", reply_markup=kb
    )
    await state.update_data(test_menu_message_id=menu_msg.message_id)


@start_router.message(Command("oracleadmin"))
@start_router.message(lambda m: m.text and m.text.strip().lower() == "/oracleadmin")
async def handle_oracle_admin(message: Message, state: FSMContext) -> None:
    await _track_activity(message.from_user.id, message.from_user.username)
    current_state = await state.get_state()
    # Если уже в админ-режиме, обновим таймер и покажем панель.
    if current_state == StartStates.admin_active:
        session_token = _make_admin_token(message)
        await state.update_data(admin_session_token=session_token)
        await _send_admin_panel(message)
        asyncio.create_task(
            _schedule_admin_timeout(
                message.bot, message.from_user.id, state, session_token
            )
        )
        return

    prev_state = current_state
    prev_data = await state.get_data()
    await state.set_state(StartStates.admin_waiting_password)
    await state.set_data(
        {
            "admin_prev_state": prev_state,
            "admin_prev_data": prev_data,
        }
    )
    await message.answer(
        "Введите пароль для доступа к админ-панели:", reply_markup=ReplyKeyboardRemove()
    )


@start_router.message(StartStates.admin_waiting_password)
async def handle_admin_password(message: Message, state: FSMContext) -> None:
    await _track_activity(message.from_user.id, message.from_user.username)
    if (message.text or "").strip() != ADMIN_PASSWORD:
        await message.answer("Пароль неверный. Попробуйте снова.")
        return
    await _activate_admin_session(message, state)


@start_router.callback_query(
    StartStates.admin_active, F.data.startswith("admin:")
)
async def handle_admin_actions(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id)
    action = callback.data
    if action == ADMIN_STATS:
        await _send_admin_stats(callback)
    elif action == ADMIN_EXPORT:
        await _send_admin_export(callback)
    else:
        await callback.answer()
        return
    await callback.answer()


def _make_admin_token(message: Message) -> str:
    return f"{message.message_id}-{int(dt.datetime.now(dt.timezone.utc).timestamp())}"


async def _activate_admin_session(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    prev_state = data.get("admin_prev_state")
    prev_data = data.get("admin_prev_data") or {}
    session_token = _make_admin_token(message)
    await state.set_state(StartStates.admin_active)
    await state.set_data(
        {
            "admin_prev_state": prev_state,
            "admin_prev_data": prev_data,
            "admin_session_token": session_token,
        }
    )
    await _send_admin_panel(message)
    asyncio.create_task(
        _schedule_admin_timeout(
            message.bot, message.from_user.id, state, session_token
        )
    )


async def _send_admin_panel(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Статистика", callback_data=ADMIN_STATS)],
            [InlineKeyboardButton(text="Выгрузка", callback_data=ADMIN_EXPORT)],
        ]
    )
    await message.answer("Админ-панель:", reply_markup=keyboard)


async def _schedule_admin_timeout(bot, user_id: int, state: FSMContext, token: str) -> None:
    try:
        await asyncio.sleep(600)
        data = await state.get_data()
        if data.get("admin_session_token") != token:
            return
        await _restore_previous_state(state)
        await bot.send_message(user_id, "Админ-сессия завершена.")
    except Exception:
        logging.exception("Failed to close admin session")


async def _restore_previous_state(state: FSMContext) -> None:
    data = await state.get_data()
    prev_state = data.get("admin_prev_state")
    prev_data = data.get("admin_prev_data") or {}
    await state.set_data(prev_data)
    if prev_state:
        await state.set_state(prev_state)
    else:
        await state.clear()


async def _send_admin_stats(callback: CallbackQuery) -> None:
    storage = dependencies.storage_gateway
    if not storage:
        await callback.message.answer("Хранилище недоступно, попробуйте позже.")
        return
    stats = await storage.fetch_admin_stats()
    avg_bs = stats.get("avg_bullshit")
    bs_text = f"{avg_bs}%" if avg_bs is not None else "—"
    text = (
        "<b>Статистика</b>\n"
        f"Пользователей: {stats.get('total_users', 0)}\n"
        f"Сегодня: {stats.get('today_users', 0)}\n"
        f"За неделю: {stats.get('week_users', 0)}\n"
        f"Прошли HEXACO: {stats.get('finished_hexaco', 0)}\n"
        f"Прошли SVS: {stats.get('finished_svs', 0)}\n"
        f"Прошли Hogan: {stats.get('finished_hogan', 0)}\n"
        f"Bullshit: {bs_text}"
    )
    await callback.message.answer(text)


async def _send_admin_export(callback: CallbackQuery) -> None:
    storage = dependencies.storage_gateway
    if not storage:
        await callback.message.answer("Хранилище недоступно, попробуйте позже.")
        return
    base_dir = Path(__file__).resolve().parents[2]
    exports_dir = base_dir / "exports"
    filename = f"users_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    export_path = exports_dir / filename
    try:
        export_path = await storage.export_users_csv(export_path)
    except Exception:
        logging.exception("Failed to build export")
        await callback.message.answer("Не удалось сформировать выгрузку, попробуйте позже.")
        return
    try:
        await callback.message.answer_document(
            document=FSInputFile(export_path),
            caption="Готовая выгрузка пользователей.",
        )
    finally:
        try:
            export_path.unlink(missing_ok=True)
        except Exception:
            pass


@start_router.callback_query(F.data.startswith(MENU_PREFIX))
async def handle_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id, callback.from_user.username)
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer()
        return
    _, action, test = parts
    await callback.answer()

    data = await state.get_data()
    participant_email = data.get("participant_email")
    menu_msg_id = data.get("test_menu_message_id")

    # удалить предыдущее меню
    if menu_msg_id:
        try:
            await callback.bot.delete_message(
                chat_id=callback.from_user.id, message_id=menu_msg_id
            )
        except Exception:
            pass

    # сбросим состояние перед действиями меню
    await state.clear()
    user_id = callback.from_user.id

    if action == "return":
        extra_msg_id = parts[2] or None
        chat_id = callback.from_user.id
        # удалить сообщение с кнопкой возврата
        try:
            await callback.message.delete()
        except Exception:
            pass
        # удалить сообщение с расширенными выводами, если передали id
        if extra_msg_id:
            try:
                await callback.bot.delete_message(
                    chat_id=chat_id, message_id=int(extra_msg_id)
                )
            except Exception:
                pass
        has_hexaco, has_hogan, has_svs = await _get_results_flags(
            chat_id, email=participant_email
        )
        menu = build_main_inline_menu(has_hexaco, has_hogan, has_svs)
        menu_msg = await callback.message.answer(
            "Выберите действие:", reply_markup=menu
        )
        await state.set_state(StartStates.choosing_test)
        await state.update_data(test_menu_message_id=menu_msg.message_id)
        return

    if action in {"start", "restart"}:
        if test == "hexaco":
            await start_hexaco(callback.message, state)  # type: ignore[arg-type]
        elif test == "hogan":
            await start_hogan(callback.message, state)  # type: ignore[arg-type]
        elif test == "svs":
            await start_svs(callback.message, state)  # type: ignore[arg-type]
        return

    if action == "results":
        if test == "hexaco":
            await handle_show_hexaco_results(
                callback.message, user_id=user_id, email=participant_email
            )
        elif test == "hogan":
            await handle_show_hogan_results(
                callback.message, user_id=user_id, email=participant_email
            )
        elif test == "svs":
            await handle_show_svs_results(
                callback.message, user_id=user_id, email=participant_email
            )
        return


@start_router.callback_query(StartStates.awaiting_begin, F.data == START_CALLBACK)
async def handle_begin(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id, callback.from_user.username)
    await state.set_state(StartStates.choosing_role)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Участник проекта", callback_data=ROLE_PARTICIPANT
                )
            ],
            [InlineKeyboardButton(text="Сотрудник проекта", callback_data=ROLE_STAFF)],
        ]
    )
    msg = await callback.message.answer("Я прохожу тесты как...", reply_markup=keyboard)
    await state.update_data(role_message_id=msg.message_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.answer()


@start_router.callback_query(StartStates.choosing_role, F.data == ROLE_PARTICIPANT)
async def handle_participant(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id, callback.from_user.username)
    data = await state.get_data()
    role_msg_id = data.get("role_message_id")
    if role_msg_id:
        try:
            await callback.bot.delete_message(
                chat_id=callback.from_user.id, message_id=role_msg_id
            )
        except Exception:
            pass
    await state.set_state(StartStates.waiting_participant_email)
    await callback.message.answer(
        "Введите почту, которую используете/собираетесь использовать в проекте.\n"
        "<b>Важно:</b> проверьте введённый адрес на ошибки, чтобы мы могли идентифицировать вас и отправить персонализированные результаты."
    )
    await callback.answer()


@start_router.callback_query(StartStates.choosing_role, F.data == ROLE_STAFF)
async def handle_staff(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id, callback.from_user.username)
    data = await state.get_data()
    role_msg_id = data.get("role_message_id")
    if role_msg_id:
        try:
            await callback.bot.delete_message(
                chat_id=callback.from_user.id, message_id=role_msg_id
            )
        except Exception:
            pass
    await state.set_state(StartStates.waiting_email)
    await callback.message.answer("Введи свою <b>корпоративную</b> почту")
    await callback.answer()


@start_router.message(StartStates.waiting_email)
async def handle_staff_email(message: Message, state: FSMContext) -> None:
    await _track_activity(message.from_user.id, message.from_user.username)
    email = (message.text or "").strip().lower()
    if "fizikl.org" not in email:
        await message.answer(
            "Домен твоей почты не соответствует корпоративному, попробуй снова или обратись к руководителю."
        )
        return

    user_id = message.from_user.id
    storage = dependencies.storage_gateway
    if storage:
        await storage.save_participant_email(user_id, email)
    await state.set_state(StartStates.choosing_test)
    menu = await _send_test_menu(
        message,
        participant=False,
        prefix="Почта подтверждена.\n<b>Выбери действие:</b>",
    )
    await state.update_data(test_menu_message_id=menu.message_id)


@start_router.message(StartStates.waiting_participant_email)
async def handle_participant_email(message: Message, state: FSMContext) -> None:
    await _track_activity(message.from_user.id, message.from_user.username)
    email = (message.text or "").strip()
    if not _is_email_valid(email):
        await message.answer("Некорректный адрес почты, попробуйте снова.")
        return
    await _remember_participant_email(message.from_user.id, email)
    await state.set_state(StartStates.choosing_test)
    menu = await _send_test_menu(message, participant=True, email=email)
    await state.update_data(
        test_menu_message_id=menu.message_id, participant_email=email.lower()
    )


async def _delete_msg(bot, chat_id: int, message_id: int | None) -> None:
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


@start_router.callback_query(StartStates.choosing_test, F.data == TEST_HEXACO)
async def handle_test_hexaco(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id, callback.from_user.username)
    data = await state.get_data()
    await _delete_msg(
        callback.bot, callback.from_user.id, data.get("test_menu_message_id")
    )
    await state.clear()
    await start_hexaco(callback.message, state)  # type: ignore[arg-type]
    await callback.answer()


@start_router.callback_query(StartStates.choosing_test, F.data == TEST_SVS)
async def handle_test_svs(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id, callback.from_user.username)
    data = await state.get_data()
    await _delete_msg(
        callback.bot, callback.from_user.id, data.get("test_menu_message_id")
    )
    await state.clear()
    await start_svs(callback.message, state)  # type: ignore[arg-type]
    await callback.answer()


@start_router.callback_query(StartStates.choosing_test, F.data == TEST_HOGAN)
async def handle_test_hogan(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id, callback.from_user.username)
    data = await state.get_data()
    await _delete_msg(
        callback.bot, callback.from_user.id, data.get("test_menu_message_id")
    )
    await state.clear()
    await start_hogan(callback.message, state)  # type: ignore[arg-type]
    await callback.answer()


@start_router.callback_query(StartStates.choosing_test, F.data == TEST_VIEW_PARTICIPANT)
async def handle_view_participant(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id, callback.from_user.username)
    data = await state.get_data()
    await _delete_msg(
        callback.bot, callback.from_user.id, data.get("test_menu_message_id")
    )
    await state.set_state(StartStates.waiting_participant_lookup)
    await callback.message.answer("Введи почту участника:")
    await callback.answer()


@start_router.message(StartStates.waiting_participant_lookup)
async def handle_view_participant_email(message: Message, state: FSMContext) -> None:
    await _track_activity(message.from_user.id, message.from_user.username)
    email = (message.text or "").strip()
    if not _is_email_valid(email):
        await message.answer("Некорректный адрес почты, попробуйте снова.")
        return
    user_id = await _find_user_by_email(email)
    if not user_id:
        await message.answer(
            "Не нашли участника с такой почтой. Проверь адрес или попроси участника отправить свою почту заново.",
            reply_markup=_build_staff_post_actions(),
        )
        return
    storage = dependencies.storage_gateway
    if not storage:
        await message.answer("Хранилище недоступно, попробуйте позже.", reply_markup=_build_staff_post_actions())
        return
    await _send_staff_results(message, user_id=user_id)
    await state.set_state(StartStates.choosing_test)


@start_router.message(lambda m: m.text and m.text.lower() in HEXACO_RESULTS_COMMANDS)
async def handle_show_hexaco_results(
    message: Message,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    include_hh: bool = False,
) -> None:
    await _track_activity(message.from_user.id, message.from_user.username)
    storage = dependencies.storage_gateway
    if not storage:
        await message.answer("Хранилище недоступно, попробуйте позже.")
        return
    target_user = await _resolve_user_id(user_id or message.from_user.id, email)
    if not target_user:
        await message.answer("Результатов Big Five пока нет.")
        return
    results = await storage.fetch_latest_hexaco_results(target_user)
    public_results = sorted(
        [r for r in results if r.visibility == "public"],
        key=lambda item: item.percent,
        reverse=True,
    )
    radar_results = _order_hexaco_for_radar(public_results, include_hh=include_hh)
    if not radar_results:
        await message.answer(
            "Результатов Big Five пока нет. Сначала пройдите тест.",
            reply_markup=None,
        )
        return
    message_text = format_results_message(public_results, include_hh=include_hh)
    radar_path = None
    try:
        radar_path = build_hexaco_radar(radar_results)
    except Exception as exc:  # pragma: no cover
        logging.exception("Failed to build Big Five radar: %s", exc)
        radar_path = None
    if radar_path:
        await message.answer_photo(
            FSInputFile(radar_path),
            caption="<b>Диаграмма Big Five</b>",
        )
    await message.answer(
        message_text,
        reply_markup=None,
    )
    if radar_path:
        try:
            radar_path.unlink(missing_ok=True)
        except Exception:
            pass


@start_router.message(lambda m: m.text and m.text.lower() in HOGAN_RESULTS_COMMANDS)
async def handle_show_hogan_results(
    message: Message, user_id: Optional[int] = None, email: Optional[str] = None
) -> None:
    await _track_activity(message.from_user.id, message.from_user.username)
    storage = dependencies.storage_gateway
    if not storage:
        await message.answer("Хранилище недоступно, попробуйте позже.")
        return
    target_user = await _resolve_user_id(user_id or message.from_user.id, email)
    if not target_user:
        await message.answer("Результатов Hogan пока нет. Сначала пройдите тест.")
        return
    report = await storage.fetch_latest_hogan_report(target_user)
    if not report or not report.scales:
        await message.answer(
            "Результатов Hogan пока нет. Сначала пройдите тест.",
            reply_markup=None,
        )
        return

    ordered_scales = sorted(report.scales, key=lambda item: item.percent, reverse=True)
    ordered_report = HoganReport(
        scales=ordered_scales, impression_management=report.impression_management
    )
    radar_scales = _order_hogan_for_radar(report.scales)
    chunks = build_hogan_results_chunks(ordered_report)
    chunks = _drop_im_lines(chunks)
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

    if radar_path:
        try:
            radar_path.unlink(missing_ok=True)
        except Exception:
            pass


@start_router.message(lambda m: m.text and m.text.lower() in RESET_COMMANDS)
@start_router.message(Command("reset"))
@start_router.message(Command("cancel"))
async def handle_reset(message: Message, state: FSMContext) -> None:
    await _track_activity(message.from_user.id, message.from_user.username)
    storage = dependencies.storage_gateway
    if storage:
        try:
            await storage.clear_user_data(message.from_user.id)
        except Exception:
            # даже если очистка не удалась, всё равно сбросим состояние
            pass
    await state.clear()
    await message.answer("История очищена.")
    await state.set_state(StartStates.awaiting_begin)
    await message.answer("…", reply_markup=ReplyKeyboardRemove())
    await _send_welcome(message)


@start_router.message(lambda m: m.text and m.text.lower() in SVS_RESULTS_COMMANDS)
async def handle_show_svs_results(
    message: Message, user_id: Optional[int] = None, email: Optional[str] = None
) -> None:
    await _track_activity(message.from_user.id, message.from_user.username)
    storage = dependencies.storage_gateway
    if not storage:
        await message.answer("Хранилище недоступно, попробуйте позже.")
        return
    target_user = await _resolve_user_id(user_id or message.from_user.id, email)
    if not target_user:
        await message.answer("Результатов SVS пока нет. Сначала пройдите тест.")
        return
    results = await storage.fetch_latest_svs_results(target_user)
    public_results = sorted(
        [r for r in results if r.visibility == "public"],
        key=lambda item: item.percent,
        reverse=True,
    )
    radar_results = _order_svs_for_radar(public_results)
    if not public_results:
        await message.answer(
            "Результатов SVS пока нет. Сначала пройдите тест.",
            reply_markup=None,
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

    for text in messages:
        await message.answer(text)
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


def _order_hexaco_for_radar(
    results: list[HexacoResult], include_hh: bool = False
) -> list[HexacoResult]:
    filtered = (
        results
        if include_hh
        else [
            r for r in results if getattr(r, "domain_id", "") != "honesty_humility"
        ]
    )
    order_index = {domain_id: idx for idx, domain_id in enumerate(HEXACO_ORDER)}
    return sorted(
        filtered, key=lambda item: order_index.get(item.domain_id, len(HEXACO_ORDER))
    )


def _order_dark_triad_for_radar(results: list[HexacoResult]) -> list[HexacoResult]:
    order_index = {domain_id: idx for idx, domain_id in enumerate(DARK_TRIAD_ORDER)}
    filtered = [r for r in results if r.domain_id in order_index]
    return sorted(filtered, key=lambda item: order_index.get(item.domain_id, 99))


def _filter_dark_triad(results: list[HexacoResult]) -> list[HexacoResult]:
    return [r for r in results if getattr(r, "domain_id", "") in DARK_TRIAD_ORDER]


def _format_dark_triad_results(results: list[HexacoResult]) -> str:
    if not results:
        return "Результатов Тёмной триады пока нет."
    ordered = sorted(results, key=lambda item: item.percent, reverse=True)
    lines = []
    for r in ordered:
        bar = build_progress_bar(r.percent, r.band_id)
        lines.append(
            f"• <b>{r.title}</b>: {r.percent}% ({r.band_label})\n{bar}\n{r.interpretation}"
        )
    return "\n\n".join(lines)


def _build_staff_post_actions() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найти другого участника", callback_data=STAFF_FIND_ANOTHER)],
            [InlineKeyboardButton(text="↩️ Вернуться в меню", callback_data=STAFF_RETURN_MENU)],
        ]
    )


@start_router.callback_query(F.data == STAFF_FIND_ANOTHER)
async def handle_staff_find_another(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id)
    await state.set_state(StartStates.waiting_participant_lookup)
    await callback.message.answer("Введи почту участника:")
    await callback.answer()


@start_router.callback_query(F.data == STAFF_RETURN_MENU)
async def handle_staff_return_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await _track_activity(callback.from_user.id)
    await state.set_state(StartStates.choosing_test)
    menu = await _send_test_menu(callback.message, participant=False, prefix="Выбери действие:")
    await state.update_data(test_menu_message_id=menu.message_id)
    await callback.answer()


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


async def _send_dark_triad_results(
    message: Message, user_id: int
) -> None:
    storage = dependencies.storage_gateway
    if not storage:
        await message.answer("Результаты Тёмной триады недоступны.")
        return
    results = await storage.fetch_latest_hexaco_results(user_id)
    triad = _filter_dark_triad(results)
    if not triad:
        await message.answer("Результатов Тёмной триады пока нет.")
        return
    ordered = _order_dark_triad_for_radar(triad)
    radar_path = None
    try:
        radar_path = build_dark_triad_radar(ordered)
    except Exception as exc:  # pragma: no cover
        logging.exception("Failed to build Dark Triad radar: %s", exc)
        radar_path = None
    text = _format_dark_triad_results(ordered)
    if radar_path:
        await message.answer_photo(
            FSInputFile(radar_path),
            caption="<b>Тёмная триада</b>",
        )
    await message.answer(text)
    if radar_path:
        try:
            radar_path.unlink(missing_ok=True)
        except Exception:
            pass


async def _send_staff_results(message: Message, user_id: int) -> None:
    storage = dependencies.storage_gateway
    if not storage:
        await message.answer("Хранилище недоступно, попробуйте позже.", reply_markup=_build_staff_post_actions())
        return

    diagrams: list[tuple[str, FSInputFile, str]] = []
    texts: list[tuple[str, str]] = []

    hexaco_present = False
    hogan_present = False

    # HEXACO / Big Five
    try:
        hexaco_results = await storage.fetch_latest_hexaco_results(user_id)
        public_results = sorted(
            [r for r in hexaco_results if r.visibility == "public"],
            key=lambda item: item.percent,
            reverse=True,
        )
        if public_results:
            hexaco_present = True
            radar_hexaco = None
            try:
                radar_hexaco = build_hexaco_radar(
                    _order_hexaco_for_radar(public_results, include_hh=True)
                )
            except Exception as exc:  # pragma: no cover
                logging.exception("Failed to build Big Five radar: %s", exc)
            if radar_hexaco:
                diagrams.append(
                    ("hexaco", FSInputFile(radar_hexaco), "<b>Диаграмма Big Five</b>")
                )
            texts.append(
                ("hexaco", format_results_message(public_results, include_hh=True))
            )

            triad = _filter_dark_triad(hexaco_results)
            if triad:
                try:
                    radar_tri = build_dark_triad_radar(
                        _order_dark_triad_for_radar(triad)
                    )
                except Exception as exc:  # pragma: no cover
                    logging.exception("Failed to build Dark Triad radar: %s", exc)
                    radar_tri = None
                if radar_tri:
                    diagrams.append(
                        ("triad", FSInputFile(radar_tri), "<b>Тёмная триада</b>")
                    )
                texts.append(("triad", _format_dark_triad_results(triad)))
    except Exception:
        logging.exception("Failed to build HEXACO staff output for user %s", user_id)
        texts.append(("hexaco", "Не удалось получить результаты Big Five, попробуйте позже."))

    # Hogan
    try:
        report = await storage.fetch_latest_hogan_report(user_id)
        if report and report.scales:
            hogan_present = True
            radar_hogan = None
            try:
                radar_hogan = build_hogan_radar(_order_hogan_for_radar(report.scales))
            except Exception as exc:  # pragma: no cover
                logging.exception("Failed to build Hogan radar: %s", exc)
            if radar_hogan:
                diagrams.append(
                    ("hogan", FSInputFile(radar_hogan), "<b>Диаграмма Hogan DSUSI-SF</b>")
                )

            chunks = build_hogan_results_chunks(report)
            chunks = _drop_im_lines(chunks)
            im_message = _build_im_message(report)
            hogan_text = []
            if im_message:
                hogan_text.append(im_message)
            hogan_text.extend(chunks)
            coach_sections = await _build_coach_sections(report)
            hogan_text.extend(coach_sections)
            texts.append(
                ("hogan", "\n\n".join(hogan_text) if hogan_text else "Результатов Hogan пока нет.")
            )
        else:
            texts.append(("hogan", "Результатов Hogan пока нет."))
    except Exception:
        logging.exception("Failed to build Hogan staff output for user %s", user_id)
        texts.append(("hogan", "Не удалось получить результаты Hogan, попробуйте позже."))

    # Определяем режим вывода
    tests_count = int(hexaco_present) + int(hogan_present)

    # Правила выдачи
    if tests_count <= 1:
        # выводим диаграммы того теста, затем тексты
        for _, file, caption in diagrams:
            try:
                await message.answer_photo(file, caption=caption)
            except Exception:
                logging.exception("Failed to send diagram")
        for _, text in texts:
            await _send_chunked_text(message, text)
    else:
        # сначала все диаграммы, затем все тексты
        for _, file, caption in diagrams:
            try:
                await message.answer_photo(file, caption=caption)
            except Exception:
                logging.exception("Failed to send diagram")
        for _, text in texts:
            await _send_chunked_text(message, text)

    # очистка временных файлов диаграмм
    for key, file, _ in diagrams:
        try:
            Path(file.path).unlink(missing_ok=True)
        except Exception:
            pass

    await message.answer("Готово. Что дальше?", reply_markup=_build_staff_post_actions())


async def _send_chunked_text(message: Message, text: str, limit: int = 3500) -> None:
    """Безопасная отправка длинных текстов частями."""
    if not text:
        return
    parts = _split_long_text(text, limit=limit)
    for idx, part in enumerate(parts):
        try:
            await message.answer(part)
        except Exception:
            logging.exception("Failed to send staff text chunk %s", idx)


def _split_long_text(text: str, limit: int = 3500) -> List[str]:
    if len(text) <= limit:
        return [text]
    # Пытаемся резать по абзацам
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    parts: List[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else current + "\n\n" + paragraph
        if len(candidate) > limit and current:
            parts.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        parts.append(current)
    # Если всё равно что-то длинное — режем по символам
    final_parts: List[str] = []
    for chunk in parts:
        if len(chunk) <= limit:
            final_parts.append(chunk)
            continue
        remaining = chunk
        while len(remaining) > limit:
            final_parts.append(remaining[:limit])
            remaining = remaining[limit:]
        if remaining:
            final_parts.append(remaining)
    return final_parts


async def _send_test_menu(
    message: Message,
    participant: bool,
    prefix: str | None = None,
    email: str | None = None,
):
    text = prefix or "Выберите действие"
    has_hexaco, has_hogan, has_svs = await _get_results_flags(
        message.from_user.id, email=email
    )
    menu = build_main_inline_menu(has_hexaco, has_hogan, has_svs)
    if not participant:
        builder = InlineKeyboardMarkup(
            inline_keyboard=[
                *menu.inline_keyboard,
                [
                    InlineKeyboardButton(
                        text="🔍 Посмотреть участника",
                        callback_data=TEST_VIEW_PARTICIPANT,
                    )
                ],
            ]
        )
        return await message.answer(text, reply_markup=builder)
    return await message.answer(text, reply_markup=menu)


def _is_email_valid(email: str) -> bool:
    if not email:
        return False
    # Простейшая проверка наличия @ и точки после него
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


async def _remember_participant_email(user_id: int, email: str) -> None:
    storage = dependencies.storage_gateway
    if not storage:
        return
    await storage.save_participant_email(user_id, email)


async def _find_user_by_email(email: str) -> Optional[int]:
    storage = dependencies.storage_gateway
    if not storage:
        return None
    return await storage.get_user_id_by_email(email)


async def _build_coach_text(report: HoganReport) -> str:
    insights = dependencies.hogan_insights
    if not insights:
        return ""
    trait_ids = _select_top_traits_for_coach(report.scales)
    if not trait_ids:
        return ""
    # Попытка получить объединённый текст
    combined = insights.build_coaching_guide(trait_ids)
    if combined:
        return combined
    sections: List[str] = []
    for trait_id in trait_ids:
        excerpt = insights.get_excerpt(trait_id, "coaching")
        if not excerpt:
            continue
        title = _get_scale_title(report.scales, trait_id)
        sections.append(f"<b>{title}</b>\n{excerpt}")
    if not sections:
        return ""
    return "\n\n".join(sections)


async def _build_coach_sections(report: HoganReport) -> List[str]:
    base_text = await _build_coach_text(report)
    if not base_text:
        return []
    # делим по пустым строкам на небольшие блоки
    parts = [p.strip() for p in base_text.split("\n\n") if p.strip()]
    sections: List[str] = []
    current = ""
    limit = 3500
    for part in parts:
        candidate = part if not current else current + "\n\n" + part
        if len(candidate) > limit:
            if current:
                sections.append(current)
                current = part
            else:
                # даже если одна секция длинная — режем
                sections.append(part[:limit])
                remaining = part[limit:]
                while remaining:
                    sections.append(remaining[:limit])
                    remaining = remaining[limit:]
                current = ""
        else:
            current = candidate
    if current:
        sections.append(current)
    return sections


def _select_top_traits_for_coach(scales: Sequence) -> List[str]:
    highs = [s for s in scales if getattr(s, "level_id", "") == "high"]
    highs.sort(key=lambda s: getattr(s, "mean_score", 0), reverse=True)
    return [s.scale_id for s in highs[:4]]


def _get_scale_title(scales: Sequence, trait_id: str) -> str:
    for s in scales:
        if getattr(s, "scale_id", "") == trait_id:
            return getattr(s, "title", trait_id)
    return trait_id


def _build_im_message(report: HoganReport) -> str:
    percent = round(report.impression_management * 100)
    if percent <= 30:
        note = "Ответам и выводам можно доверять."
    elif percent <= 60:
        note = "Ответы неоднозначны, не все выводы могут соответствовать реальности."
    else:
        note = (
            "Наиболее вероятно участник выбирал социально-положительные ответы, "
            "чтобы произвести хорошее впечатление. Выводы могут быть мимо."
        )
    return f"<b>Социально-одобряемые ответы</b>: {percent}%\n\n{note}"


def _drop_im_lines(chunks: List[str]) -> List[str]:
    cleaned: List[str] = []
    for chunk in chunks:
        lines = chunk.splitlines()
        filtered = [
            line
            for line in lines
            if not line.startswith("Социально-одобряемые ответы") and "IM ≥" not in line
        ]
        text = "\n".join(filtered).strip()
        if text:
            cleaned.append(text)
    return cleaned


async def _get_results_flags(
    user_id: int, email: str | None = None
) -> tuple[bool, bool, bool]:
    storage = dependencies.storage_gateway
    if not storage:
        return False, False, False
    target_user = await _resolve_user_id(user_id, email, allow_fallback=False)
    if not target_user:
        return False, False, False
    has_hexaco = await storage.has_results(target_user, "HEXACO")
    has_hogan = await storage.has_results(target_user, "HOGAN")
    has_svs = await storage.has_results(target_user, "SVS")
    return has_hexaco, has_hogan, has_svs


async def _resolve_user_id(
    fallback_user_id: int, email: str | None, allow_fallback: bool = True
) -> Optional[int]:
    if email:
        storage = dependencies.storage_gateway
        if storage:
            user_id = await storage.get_user_id_by_email(email.lower())
            if user_id:
                return user_id
        if not allow_fallback:
            return None
    return fallback_user_id


async def _send_welcome(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Приступим!", callback_data=START_CALLBACK)]
        ]
    )
    if WELCOME_GIF_PATH.exists():
        await message.answer_animation(
            animation=FSInputFile(WELCOME_GIF_PATH),
            caption=WELCOME_TEXT,
            reply_markup=keyboard,
        )
    else:
        await message.answer(WELCOME_TEXT, reply_markup=keyboard)
