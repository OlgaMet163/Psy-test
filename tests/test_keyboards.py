from bot.keyboards.common import build_main_inline_menu


def _inline_texts(markup):
    return [button.text for row in markup.inline_keyboard for button in row]


def _inline_callbacks(markup):
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def test_inline_menu_only_starts():
    kbd = build_main_inline_menu(False, False, False)
    texts = _inline_texts(kbd)
    callbacks = _inline_callbacks(kbd)
    assert texts == [
        "🚀 Начать HEXACO",
        "🚀 Начать Hogan",
        "🚀 Начать SVS",
    ]
    assert callbacks == [
        "menu:start:hexaco",
        "menu:start:hogan",
        "menu:start:svs",
    ]


def test_inline_menu_with_results():
    kbd = build_main_inline_menu(True, True, True)
    texts = _inline_texts(kbd)
    callbacks = _inline_callbacks(kbd)
    # порядок: стартов нет (все есть), затем результаты, затем перепройти
    assert texts == [
        "📊 Результаты HEXACO",
        "📊 Результаты Hogan",
        "📊 Результаты SVS",
        "🔁 Перепройти HEXACO",
        "🔁 Перепройти Hogan",
        "🔁 Перепройти SVS",
    ]
    assert callbacks == [
        "menu:results:hexaco",
        "menu:results:hogan",
        "menu:results:svs",
        "menu:restart:hexaco",
        "menu:restart:hogan",
        "menu:restart:svs",
    ]
