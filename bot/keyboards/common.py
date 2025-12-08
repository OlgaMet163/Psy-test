from typing import Dict, Sequence

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

HEXACO_FREQUENCY_OPTIONS = [
    (5, "Almost always"),
    (4, "Often"),
    (3, "Sometimes"),
    (2, "Rarely"),
    (1, "Almost never"),
]
HEXACO_STRENGTH_OPTIONS = [
    (5, "Very strongly"),
    (4, "Strongly"),
    (3, "Somewhat"),
    (2, "Slightly"),
    (1, "Not at all"),
]
HEXACO_COMFORT_OPTIONS = [
    (5, "Very comfortable"),
    (4, "Comfortable"),
    (3, "Neutral"),
    (2, "Somewhat uneasy"),
    (1, "Very uncomfortable"),
]
HEXACO_EASE_OPTIONS = [
    (5, "Very easy"),
    (4, "Easy"),
    (3, "Manageable"),
    (2, "Somewhat hard"),
    (1, "Very hard"),
]
HEXACO_LIKELIHOOD_OPTIONS = [
    (5, "Very likely"),
    (4, "Likely"),
    (3, "Sometimes"),
    (2, "Unlikely"),
    (1, "Very unlikely"),
]
HEXACO_SPEED_OPTIONS = [
    (5, "Immediately"),
    (4, "Quickly"),
    (3, "After a pause"),
    (2, "Slowly"),
    (1, "Rarely reset"),
]
HEXACO_RELIABILITY_OPTIONS = [
    (5, "Always"),
    (4, "Mostly"),
    (3, "About half the time"),
    (2, "Occasionally"),
    (1, "Rarely"),
]
HEXACO_PREFERENCE_OPTIONS = [
    (5, "Prefer observing a lot"),
    (4, "Prefer observing"),
    (3, "Depends on context"),
    (2, "Prefer speaking sooner"),
    (1, "Want to speak right away"),
]
HEXACO_IMPACT_OPTIONS = [
    (5, "Huge impact"),
    (4, "Strong impact"),
    (3, "Moderate impact"),
    (2, "Small impact"),
    (1, "No impact"),
]

HEXACO_DEFAULT_OPTIONS = HEXACO_FREQUENCY_OPTIONS
HEXACO_CUSTOM_OPTIONS: Dict[int, Sequence[tuple[int, str]]] = {
    3: HEXACO_STRENGTH_OPTIONS,
    4: HEXACO_COMFORT_OPTIONS,
    6: HEXACO_EASE_OPTIONS,
    7: HEXACO_STRENGTH_OPTIONS,
    8: HEXACO_EASE_OPTIONS,
    9: HEXACO_COMFORT_OPTIONS,
    10: HEXACO_PREFERENCE_OPTIONS,
    13: HEXACO_EASE_OPTIONS,
    14: HEXACO_LIKELIHOOD_OPTIONS,
    15: HEXACO_SPEED_OPTIONS,
    17: HEXACO_RELIABILITY_OPTIONS,
    19: HEXACO_RELIABILITY_OPTIONS,
    23: HEXACO_IMPACT_OPTIONS,
}

HOGAN_OPTIONS = [
    (5, "Точно про меня"),
    (4, "Скорее про меня"),
    (3, "Немного про меня"),
    (2, "Скорее не про меня"),
    (1, "Точно не про меня"),
]

HOGAN_LABELS = {value: label for value, label in HOGAN_OPTIONS}

SVS_OPTIONS = [
    (1, "Not at all true of me"),
    (2, "Rarely true of me"),
    (3, "Occasionally true of me"),
    (4, "Sometimes true of me"),
    (5, "Often true of me"),
    (6, "Usually true of me"),
    (7, "Very true of me"),
]

ATLAS_DOMAINS = [
    ("lifestyle", "Lifestyle"),
    ("health", "Health"),
    ("romantic", "Romantic"),
    ("friendships", "Friendships"),
    ("hobbies", "Hobbies"),
    ("sports", "Sports"),
    ("business", "Business"),
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
    builder.button(text="Career", callback_data=f"hogan:career:{payload}")
    builder.button(
        text=ATLAS_DOMAIN_LABELS["business"],
        callback_data="hogan:atlas:business",
    )
    builder.button(text="Coaching", callback_data=f"hogan:coach:{payload}")
    builder.adjust(1)
    return builder.as_markup()


def main_menu_keyboard(
    has_hexaco_results: bool, has_hogan_results: bool, has_svs_results: bool = False
) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    if has_hexaco_results:
        builder.row(KeyboardButton(text="HEXACO results"))
        builder.row(KeyboardButton(text="Restart HEXACO"))
    else:
        builder.row(KeyboardButton(text="Start HEXACO"))
    if has_hogan_results:
        builder.row(KeyboardButton(text="Hogan results"))
        builder.row(KeyboardButton(text="Restart Hogan"))
    else:
        builder.row(KeyboardButton(text="Start Hogan"))
    if has_svs_results:
        builder.row(KeyboardButton(text="SVS results"))
        builder.row(KeyboardButton(text="Restart SVS"))
    else:
        builder.row(KeyboardButton(text="Start SVS"))
    return builder.as_markup(resize_keyboard=True)


def _build_answer_keyboard(
    prefix: str, options: Sequence[tuple[int, str]]
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value, label in options:
        builder.button(text=label, callback_data=f"{prefix}:{value}")
    builder.adjust(1)
    return builder.as_markup()
