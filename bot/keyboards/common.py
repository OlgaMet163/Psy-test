from typing import Dict, Sequence

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

HEXACO_FREQUENCY_OPTIONS = [
    (5, "Почти всегда"),
    (4, "Часто"),
    (3, "Иногда"),
    (2, "Редко"),
    (1, "Почти никогда"),
]
HEXACO_IMPORTANCE_OPTIONS = [
    (5, "Очень важно"),
    (4, "Важно"),
    (3, "Умеренно важно"),
    (2, "Скорее не важно"),
    (1, "Совсем не важно"),
]
HEXACO_STRENGTH_OPTIONS = [
    (5, "Очень сильно"),
    (4, "Сильно"),
    (3, "Умеренно"),
    (2, "Слабо"),
    (1, "Совсем нет"),
]
HEXACO_COMFORT_OPTIONS = [
    (5, "Очень комфортно"),
    (4, "Комфортно"),
    (3, "Нейтрально"),
    (2, "Слегка некомфортно"),
    (1, "Очень некомфортно"),
]
HEXACO_EASE_OPTIONS = [
    (5, "Очень легко"),
    (4, "Легко"),
    (3, "По-разному"),
    (2, "Сложновато"),
    (1, "Очень сложно"),
]
HEXACO_LIKELIHOOD_OPTIONS = [
    (5, "Очень вероятно"),
    (4, "Вероятно"),
    (3, "Иногда"),
    (2, "Маловероятно"),
    (1, "Крайне маловероятно"),
]
HEXACO_SPEED_OPTIONS = [
    (5, "Сразу"),
    (4, "Быстро"),
    (3, "После паузы"),
    (2, "Медленно"),
    (1, "Редко восстанавливаюсь"),
]
HEXACO_RELIABILITY_OPTIONS = [
    (5, "Всегда"),
    (4, "Чаще всего"),
    (3, "Примерно половину времени"),
    (2, "Иногда"),
    (1, "Редко"),
]
HEXACO_EFFORT_OPTIONS = [
    (5, "Почти всегда приходится"),
    (4, "Часто приходится"),
    (3, "Иногда приходится"),
    (2, "Редко приходится"),
    (1, "Никогда не приходится"),
]
HEXACO_PREFERENCE_OPTIONS = [
    (5, "Предпочитаю долго наблюдать"),
    (4, "Предпочитаю наблюдать"),
    (3, "По-разному"),
    (2, "Хочу высказаться скорее"),
    (1, "Хочу говорить сразу"),
]
HEXACO_IMPACT_OPTIONS = [
    (5, "Очень сильное влияние"),
    (4, "Сильное влияние"),
    (3, "Умеренное влияние"),
    (2, "Небольшое влияние"),
    (1, "Нет влияния"),
]

HEXACO_DEFAULT_OPTIONS = HEXACO_FREQUENCY_OPTIONS
HEXACO_CUSTOM_OPTIONS: Dict[int, Sequence[tuple[int, str]]] = {
    3: HEXACO_IMPORTANCE_OPTIONS,
    4: HEXACO_COMFORT_OPTIONS,
    7: HEXACO_STRENGTH_OPTIONS,
    8: HEXACO_EASE_OPTIONS,
    9: HEXACO_COMFORT_OPTIONS,
    10: HEXACO_PREFERENCE_OPTIONS,
    13: HEXACO_EASE_OPTIONS,
    14: HEXACO_LIKELIHOOD_OPTIONS,
    15: HEXACO_SPEED_OPTIONS,
    17: HEXACO_RELIABILITY_OPTIONS,
    19: HEXACO_EFFORT_OPTIONS,
    23: HEXACO_IMPACT_OPTIONS,
}

HOGAN_OPTIONS = [
    (5, "Очень часто"),
    (4, "Часто"),
    (3, "Иногда"),
    (2, "Редко"),
    (1, "Никогда"),
]

HOGAN_LABELS = {value: label for value, label in HOGAN_OPTIONS}

SVS_OPTIONS = [
    (5, "Точно про меня"),
    (4, "Скорее про меня"),
    (3, "Отчасти про меня"),
    (2, "Скорее не про меня"),
    (1, "Совсем не про меня"),
]

ATLAS_DOMAINS = [
    ("lifestyle", "Образ жизни"),
    ("health", "Здоровье"),
    ("romantic", "Отношения"),
    ("friendships", "Дружба"),
    ("hobbies", "Хобби"),
    ("sports", "Спорт"),
    ("business", "Бизнес"),
]
ATLAS_DOMAIN_LABELS = {key: title for key, title in ATLAS_DOMAINS}


def build_hexaco_keyboard(
    prefix: str, statement_id: int | None = None
) -> InlineKeyboardMarkup:
    return _build_answer_keyboard(prefix, _get_hexaco_options(statement_id))


def get_hexaco_label(statement_id: int | None, value: int) -> str:
    options = _get_hexaco_options(statement_id)
    label_map = {option_value: label for option_value, label in options}
    return label_map.get(value, "")


def _get_hexaco_options(statement_id: int | None) -> Sequence[tuple[int, str]]:
    if statement_id is None:
        return HEXACO_DEFAULT_OPTIONS
    return HEXACO_CUSTOM_OPTIONS.get(statement_id, HEXACO_DEFAULT_OPTIONS)


def build_hogan_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return _build_answer_keyboard(prefix, HOGAN_OPTIONS)


def build_svs_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return _build_answer_keyboard(prefix, SVS_OPTIONS)


def get_svs_label(value: int) -> str:
    label_map = {option_value: label for option_value, label in SVS_OPTIONS}
    return label_map.get(value, "")


def hogan_insights_keyboard(trait_ids: Sequence[str]) -> InlineKeyboardMarkup:
    payload = ",".join(trait_ids)
    builder = InlineKeyboardBuilder()
    ordered_domain_keys = [
        "lifestyle",
        "health",
        "romantic",
        "friendships",
        "hobbies",
        "sports",
    ]
    for domain_key in ordered_domain_keys:
        title = ATLAS_DOMAIN_LABELS[domain_key]
        builder.button(text=title, callback_data=f"hogan:atlas:{domain_key}")
    builder.button(text="Карьера", callback_data=f"hogan:career:{payload}")
    builder.button(
        text=ATLAS_DOMAIN_LABELS["business"],
        callback_data="hogan:atlas:business",
    )
    builder.button(text="Кураторам", callback_data=f"hogan:coach:{payload}")
    builder.adjust(1)
    return builder.as_markup()


def main_menu_keyboard(
    has_hexaco_results: bool, has_hogan_results: bool, has_svs_results: bool = False
) -> ReplyKeyboardMarkup:
    start_emoji = "🚀"
    restart_emoji = "🔁"
    results_emoji = "📊"
    builder = ReplyKeyboardBuilder()

    # Start buttons — одной строкой, упорядочены: HEXACO, Hogan, SVS.
    start_buttons: list[KeyboardButton] = []
    if not has_hexaco_results:
        start_buttons.append(KeyboardButton(text=f"{start_emoji} Начать HEXACO"))
    if not has_hogan_results:
        start_buttons.append(KeyboardButton(text=f"{start_emoji} Начать Hogan"))
    if not has_svs_results:
        start_buttons.append(KeyboardButton(text=f"{start_emoji} Начать SVS"))
    if start_buttons:
        builder.row(*start_buttons)

    # Results / Restart pairs per test
    if has_hexaco_results:
        builder.row(
            KeyboardButton(text=f"{results_emoji} Результаты HEXACO"),
            KeyboardButton(text=f"{restart_emoji} Перепройти HEXACO"),
        )
    if has_hogan_results:
        builder.row(
            KeyboardButton(text=f"{results_emoji} Результаты Hogan"),
            KeyboardButton(text=f"{restart_emoji} Перепройти Hogan"),
        )
    if has_svs_results:
        builder.row(
            KeyboardButton(text=f"{results_emoji} Результаты SVS"),
            KeyboardButton(text=f"{restart_emoji} Перепройти SVS"),
        )

    return builder.as_markup(
        resize_keyboard=True, input_field_placeholder="Выберите действие"
    )


def _build_answer_keyboard(
    prefix: str, options: Sequence[tuple[int, str]]
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value, label in options:
        builder.button(text=label, callback_data=f"{prefix}:{value}")
    builder.adjust(1)
    return builder.as_markup()
