from bot.keyboards.common import main_menu_keyboard


def _texts(markup):
    return [[button.text for button in row] for row in markup.keyboard]


def test_main_menu_keyboard_only_starts():
    kbd = main_menu_keyboard(False, False, False)
    rows = _texts(kbd)
    assert len(rows) == 1
    assert rows[0] == [
        "🚀 Начать HEXACO",
        "🚀 Начать Hogan",
        "🚀 Начать SVS",
    ]


def test_main_menu_keyboard_with_results():
    kbd = main_menu_keyboard(True, True, True)
    rows = _texts(kbd)
    # 3 pairs (results/restart) over two columns => 3 rows
    assert len(rows) == 3
    assert ["📊 Результаты HEXACO", "🔁 Перепройти HEXACO"] in rows
    assert ["📊 Результаты Hogan", "🔁 Перепройти Hogan"] in rows
    assert ["📊 Результаты SVS", "🔁 Перепройти SVS"] in rows
