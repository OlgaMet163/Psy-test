from __future__ import annotations

import random
import re
from itertools import combinations
from typing import Dict, List, Sequence

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot import dependencies
from bot.keyboards import (
    HOGAN_LABELS,
    build_hogan_keyboard,
    hogan_insights_keyboard,
    main_menu_keyboard,
)
from bot.services.hogan import (
    HoganReport,
    HoganScaleResult,
    SCALE_DEFINITIONS,
    IM_ITEMS,
)
from aiogram.types import FSInputFile
from bot.utils.text import build_progress_bar
from bot.utils.plot import build_hogan_radar
from bot.utils.plot import build_hogan_radar

hogan_router = Router(name="hogan")
CALLBACK_PREFIX = "hogan"
INSIGHTS_SEPARATOR = ","
_HOGAN_TITLE_BY_ID = {scale.id: scale.title for scale in SCALE_DEFINITIONS}
_HOGAN_ORDER = [scale.id for scale in SCALE_DEFINITIONS]
HOGAN_TEXT_TRIGGERS = {
    "начать hogan",
    "перепройти hogan",
    "start hogan",
    "restart hogan",
    "hogan",
    "🚀 start hogan",
    "🔁 restart hogan",
    "🚀 начать hogan",
    "🔁 перепройти hogan",
}
ATLAS_DOMAIN_TITLES = {
    "business": "Hogan: бизнес",
    "friendships": "Hogan: дружба",
    "hobbies": "Hogan: хобби",
    "romantic": "Hogan: отношения",
    "lifestyle": "Hogan: образ жизни",
    "health": "Hogan: здоровье",
    "sports": "Hogan: спорт",
    "career": "Hogan: карьера",
}
ATLAS_DOMAIN_KEYS = set(ATLAS_DOMAIN_TITLES.keys())
_DOMAIN_PREFIX_PATTERN = re.compile(r"^- \*\*[^*]+\*\*\s*:?", re.IGNORECASE)
_NET_EFFECT_PATTERN = re.compile(
    r"(?:Net effect|Итог):\s*(.+)$", re.IGNORECASE | re.DOTALL
)
_REDUNDANT_STATEMENTS = {
    "stronger frequency/intensity, lower recovery, and higher downstream consequences"
}


class HoganStates(StatesGroup):
    answering = State()


@hogan_router.message(Command("hogan"))
@hogan_router.message(lambda m: m.text and m.text.lower() in HOGAN_TEXT_TRIGGERS)
async def start_hogan(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state:
        if str(current_state).startswith("HoganStates"):
            await message.answer(
                "Hogan уже идёт. Продолжайте отвечать с помощью кнопок ниже."
            )
            return
        await message.answer(
            "Сейчас идёт другой тест. Завершите его или отправьте /reset."
        )
        return
    engine = _ensure_engine()
    order = _build_question_order(engine)
    await state.set_state(HoganStates.answering)
    await state.update_data(index=0, answers={}, order=order)
    await message.answer(
        "Hogan DSUSI-SF: вспомните последние 2–3 месяца под давлением и отвечайте, как это было на практике.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await _send_question(message, engine, order, 0)


@hogan_router.callback_query(
    HoganStates.answering, F.data.startswith(f"{CALLBACK_PREFIX}:")
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
            test_name="HOGAN",
            statement_id=statement.id,
            raw_value=raw_value,
            label=HOGAN_LABELS.get(raw_value, ""),
        )

    if index + 1 >= len(order):
        await _finish(callback, state, answers, engine)
        return

    await _send_question(callback.message, engine, order, index + 1)


@hogan_router.callback_query(F.data.startswith("hogan:coach:"))
async def handle_coaching_insight(callback: CallbackQuery) -> None:
    await _send_insight(callback, "coaching")


@hogan_router.callback_query(F.data.startswith("hogan:career:"))
async def handle_career_insight(callback: CallbackQuery) -> None:
    await _send_insight(callback, "career")


@hogan_router.callback_query(F.data.startswith("hogan:atlas:"))
async def handle_atlas_domain(callback: CallbackQuery) -> None:
    try:
        domain = callback.data.split(":", 2)[2]
    except IndexError:
        await callback.answer("Unable to parse request.", show_alert=True)
        return
    if domain not in ATLAS_DOMAIN_KEYS - {"career"}:
        await callback.answer("Unknown domain.", show_alert=True)
        return
    text = await _get_atlas_domain_message(callback.from_user.id, domain)
    if not text:
        await callback.answer("No matching trait combinations found.", show_alert=True)
        return
    await _send_text_chunks(callback.message, _split_text(text))
    await callback.answer()


def build_hogan_results_chunks(report: HoganReport, limit: int = 3500) -> List[str]:
    blocks: List[str] = ["Результаты Hogan DSUSI-SF:"]
    im_percent = _im_percent(report.impression_management)
    im_threshold_mean = 0.8  # доля максимальных ответов (>=80%)
    im_threshold_percent = _im_percent(im_threshold_mean)
    im_flag = report.impression_management >= im_threshold_mean
    im_line = f"Управление впечатлением: {im_percent}%"
    if im_flag:
        im_line += " ⚠️"
    blocks.append(im_line)
    if im_flag:
        blocks.append(
            f"IM ≥ {im_threshold_percent}% может говорить о социально-желательных ответах; трактуйте низкие шкалы осторожно."
        )
    ordered_scales = sorted(report.scales, key=lambda item: item.percent, reverse=True)
    for scale in ordered_scales:
        bar = build_progress_bar(scale.percent, scale.level_id)
        blocks.append(
            f"• <b>{scale.title}</b> ({scale.hds_label}) — {scale.percent}% ({scale.level_label})\n"
            f"{bar}\n"
            f"{scale.interpretation}"
        )
    return _combine_blocks(blocks, limit)


def build_hogan_results_keyboard(scales: Sequence[HoganScaleResult]):
    trait_ids = _select_top_traits(scales)
    if not trait_ids:
        return None
    return hogan_insights_keyboard(trait_ids)


async def _send_question(
    message: Message, engine, order: Sequence[int], index: int
) -> None:
    statement = engine.get_statement(order[index])
    total = len(order)
    await message.answer(
        f"Вопрос {index + 1}/{total}\n\n{statement.text}",
        reply_markup=build_hogan_keyboard(CALLBACK_PREFIX),
    )


async def _finish(
    callback: CallbackQuery, state: FSMContext, answers: Dict[int, int], engine
) -> None:
    report = engine.calculate(answers)
    ordered_scales = sorted(report.scales, key=lambda item: item.percent, reverse=True)
    radar_scales = _order_hogan_for_radar(report.scales)
    ordered_report = HoganReport(
        scales=ordered_scales, impression_management=report.impression_management
    )
    keyboard = build_hogan_results_keyboard(ordered_scales)
    chunks = build_hogan_results_chunks(ordered_report)
    radar_path = None
    try:
        radar_path = build_hogan_radar(radar_scales)
    except Exception as exc:  # pragma: no cover - diagnostics
        import logging

        logging.exception("Failed to build Hogan radar: %s", exc)
        radar_path = None

    storage = _ensure_storage()
    hexaco_has_results = False
    svs_has_results = False
    if storage:
        payload = [*ordered_report.scales]
        payload.append(_build_im_result(report))
        await storage.save_results(callback.from_user.id, "HOGAN", payload)
        hexaco_has_results = await storage.has_results(callback.from_user.id, "HEXACO")
        svs_has_results = await storage.has_results(callback.from_user.id, "SVS")

    if not chunks:
        chunks = ["Результатов Hogan пока нет."]
    if radar_path:
        await callback.message.answer_photo(
            FSInputFile(radar_path),
            caption="<b>Диаграмма Hogan DSUSI-SF</b>",
        )
    for chunk in chunks:
        await callback.message.answer(chunk)
    if keyboard:
        await callback.message.answer(
            "Расширенные выводы Hogan:",
            reply_markup=keyboard,
        )
    await callback.message.answer(
        "Можно вернуться в меню или выбрать другой тест в любой момент.",
        reply_markup=main_menu_keyboard(hexaco_has_results, True, svs_has_results),
    )
    if radar_path:
        try:
            radar_path.unlink(missing_ok=True)
        except Exception:
            pass
    await state.clear()


async def _send_insight(callback: CallbackQuery, context: str) -> None:
    insights = _ensure_insights()
    try:
        payload = callback.data.split(":", 2)[2]
    except IndexError:
        await callback.answer("Не удалось обработать запрос.", show_alert=True)
        return
    trait_ids = [trait for trait in payload.split(INSIGHTS_SEPARATOR) if trait]
    if not trait_ids:
        await callback.answer("Нет данных для пояснений.", show_alert=True)
        return

    sections: List[str] = []

    if context == "coaching":
        combined = insights.build_coaching_guide(trait_ids)
        if combined:
            sections.append(combined)
        else:
            sections.extend(_build_individual_insights(insights, trait_ids, context))
    else:
        sections.extend(_build_individual_insights(insights, trait_ids, context))
        if context == "career":
            atlas_text = await _get_atlas_domain_message(
                callback.from_user.id, "career"
            )
            if atlas_text:
                sections.append(atlas_text)

    if not sections:
        await callback.answer("Нет текста для этих шкал.", show_alert=True)
        return

    context_label = "Коучинг" if context == "coaching" else "Карьера"
    message_text = f"{context_label}: выдержки по высоким шкалам\n\n" + "\n\n".join(
        sections
    )
    await _send_text_chunks(callback.message, _split_text(message_text))
    await callback.answer()


def _build_individual_insights(
    insights, trait_ids: Sequence[str], context: str
) -> List[str]:
    sections: List[str] = []
    for trait_id in trait_ids:
        excerpt = insights.get_excerpt(trait_id, context)
        if not excerpt:
            continue
        title = _HOGAN_TITLE_BY_ID.get(trait_id, trait_id)
        sections.append(f"<b>{title}</b>\n{excerpt}")
    return sections


def _ensure_engine():
    if dependencies.hogan_engine is None:
        raise RuntimeError("HoganEngine is not initialized.")
    return dependencies.hogan_engine


def _ensure_storage():
    return dependencies.storage_gateway


def _ensure_insights():
    if dependencies.hogan_insights is None:
        raise RuntimeError("HoganInsights is not initialized.")
    return dependencies.hogan_insights


def _ensure_atlas():
    return dependencies.hogan_atlas


async def _fetch_latest_report(user_id: int) -> HoganReport | None:
    storage = _ensure_storage()
    if not storage:
        return None
    return await storage.fetch_latest_hogan_report(user_id)


async def _resolve_matching_combos(user_id: int) -> List[tuple[str, str]]:
    report = await _fetch_latest_report(user_id)
    if not report:
        return []
    return _select_atlas_combos_from_report(report)


def _select_atlas_combos_from_report(report: HoganReport) -> List[tuple[str, str]]:
    atlas = _ensure_atlas()
    if not atlas:
        return []
    high_scales = [scale for scale in report.scales if scale.level_id == "high"]
    if not high_scales:
        return []
    high_scales.sort(key=lambda item: item.mean_score, reverse=True)
    max_size = min(4, len(high_scales))
    type_map = {1: "single", 2: "pair", 3: "triple", 4: "quadruple"}
    combos: List[tuple[str, str]] = []
    for size in range(max_size, 0, -1):
        for combo in combinations(high_scales, size):
            ids = sorted(scale.scale_id for scale in combo)
            key = ids[0] if size == 1 else "+".join(ids)
            combo_type = type_map[size]
            if atlas.has_combo(combo_type, key):
                combos.append((combo_type, key))
    return combos


async def _get_atlas_domain_message(user_id: int, domain: str) -> str | None:
    combos = await _resolve_matching_combos(user_id)
    atlas = _ensure_atlas()
    if not combos or not atlas:
        return None
    entries: List[tuple[str, str]] = []
    for combo_type, combo_key in combos:
        snippet = atlas.get_domain_text(combo_type, combo_key, domain)
        if not snippet:
            continue
        entries.append((combo_key, snippet))
    if not entries:
        return None
    title = ATLAS_DOMAIN_TITLES.get(domain, f"Hogan {domain.title()}")
    return _compose_atlas_domain_text(title, entries)


def _compose_atlas_domain_text(
    title: str, entries: Sequence[tuple[str, str]]
) -> str | None:
    seen_statements: set[str] = set()
    ordered_statements: List[str] = []

    for _, snippet in entries:
        description, _ = _split_domain_snippet(snippet)
        if not description:
            continue
        statements = _extract_statements(description)
        for statement in statements:
            normalized = _normalize_statement(statement)
            if (
                not normalized
                or normalized in seen_statements
                or normalized in _REDUNDANT_STATEMENTS
            ):
                continue
            seen_statements.add(normalized)
            formatted = _format_statement(statement)
            if formatted:
                ordered_statements.append(formatted)

    if not ordered_statements:
        return None

    bullet_lines = [f"• {statement}" for statement in ordered_statements]
    return f"<b>{title}</b>\n\n" + "\n".join(bullet_lines)


def _split_domain_snippet(snippet: str) -> tuple[str, List[str]]:
    if not snippet:
        return "", []
    text = snippet.strip()
    text = _DOMAIN_PREFIX_PATTERN.sub("", text, count=1).strip()

    effects: List[str] = []
    match = _NET_EFFECT_PATTERN.search(text)
    if match:
        effect_body = match.group(1).strip()
        if effect_body:
            effects.append(_collapse_spaces(effect_body).rstrip("."))
        text = text[: match.start()].rstrip(" -;,.\n\t")

    description = _collapse_spaces(text)
    return description, effects


def _collapse_spaces(text: str) -> str:
    return " ".join(text.split())


def _extract_statements(description: str) -> List[str]:
    if not description:
        return []
    parts = re.split(r";|\.\s+(?=[A-ZА-Я])", description)
    statements: List[str] = []
    for part in parts:
        clean = part.strip(" -—;,.")
        if clean:
            statements.append(clean)
    return statements


def _format_statement(statement: str) -> str:
    text = _collapse_spaces(statement.strip(" -—;,."))
    if not text:
        return ""
    if text[-1] in ".;":
        text = text[:-1]
    if text and text[0].isalpha():
        text = text[0].upper() + text[1:]
    return text


def _normalize_statement(statement: str) -> str:
    return _collapse_spaces(statement).strip(" -—.;,").lower()


def _build_question_order(engine) -> List[int]:
    total = engine.total_questions()
    indices = list(range(total))
    random.shuffle(indices)
    return indices


def _select_top_traits(scales: Sequence[HoganScaleResult]) -> List[str]:
    high = [scale.scale_id for scale in scales if scale.level_id == "high"]
    if high:
        return high[:3]
    sorted_scales = sorted(scales, key=lambda item: item.mean_score, reverse=True)
    return [scale.scale_id for scale in sorted_scales[:2]]


def _build_im_result(report: HoganReport) -> HoganScaleResult:
    percent = _im_percent(report.impression_management)
    im_threshold_percent = 80.0
    return HoganScaleResult(
        scale_id="IM",
        title="Управление впечатлением",
        hds_label="IM",
        mean_score=report.impression_management,
        percent=percent,
        level_id="im",
        level_label="Управление впечатлением",
        interpretation=(
            f"Доля максимальных («идеальных») ответов на проверочные пункты (≥{im_threshold_percent}% может указывать на управление впечатлением)."
        ),
        visibility="internal",
    )


def _order_hogan_for_radar(
    scales: Sequence[HoganScaleResult],
) -> List[HoganScaleResult]:
    order_index = {scale_id: idx for idx, scale_id in enumerate(_HOGAN_ORDER)}
    return sorted(
        [scale for scale in scales if scale.scale_id != "IM"],
        key=lambda item: order_index.get(item.scale_id, len(_HOGAN_ORDER)),
    )


def _mean_to_percent(mean_score: float) -> float:
    return round(((mean_score - 1) / 4) * 100, 2)


def _im_percent(mean_score: float) -> float:
    return round(mean_score * 100, 2)


def _combine_blocks(blocks: Sequence[str], limit: int = 3500) -> List[str]:
    normalized: List[str] = []
    for block in blocks:
        normalized.extend(_split_long_block(block.strip(), limit))
    chunks: List[str] = []
    current = ""
    for block in normalized:
        if not block:
            continue
        candidate = block if not current else f"{current}\n\n{block}"
        if len(candidate) > limit and current:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _split_long_block(block: str, limit: int) -> List[str]:
    if not block:
        return []
    if len(block) <= limit:
        return [block]
    pieces: List[str] = []
    remaining = block
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut == -1:
            cut = remaining.rfind(" ", 0, limit)
        if cut == -1:
            cut = limit
        pieces.append(remaining[:cut].strip())
        remaining = remaining[cut:].lstrip("\n ")
    if remaining:
        pieces.append(remaining)
    return pieces


def _split_text(text: str, limit: int = 3500) -> List[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        return []
    return _combine_blocks(paragraphs, limit)


async def _send_text_chunks(
    message: Message, chunks: Sequence[str], reply_markup=None
) -> None:
    for idx, chunk in enumerate(chunks):
        markup = reply_markup if idx == 0 else None
        await message.answer(chunk, reply_markup=markup)
