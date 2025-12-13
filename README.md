# Psy-test Bot

## О проекте
Телеграм-бот на aiogram 3 (long polling) для прохождения психологических тестов с мгновенной выдачей результатов и визуализацией. Доступны:
- Big Five (бывш. HEXACO) — 24 утверждения + 6 скрытых вопросов Тёмной триады (видны только сотруднику), проценты, интерпретации, PNG-радар.
- Schwartz Value Survey (SVS) — 20 утверждений (1–5), 10 ценностей + 4 группы, PNG-радар.
- Hogan DSUSI-SF — 38 утверждений (1–5), 11 шкал + Impression Management, PNG-радар.

## Текущее состояние
- Реализованы три теста; ответы и результаты сохраняются в локальную SQLite (`data/bot.db`) через `StorageGateway` (общие таблицы `hexaco_answers`, `hexaco_results`, `participant_emails`). В БД хранится только последний ответ на утверждение.
- Меню только inline: порядок кнопок — «Начать» → «Результаты» → «Перепройти» по каждому тесту; параллельные тесты запрещены.
- Прохождение вопросов: в каждой карточке есть кнопка «Назад», можно вернуть предыдущий вопрос, увидеть выбранный вариант с галочкой и изменить ответ (перезаписывается).
- Роль участника вводит почту; если почта уже есть в БД с результатами, показываются кнопки «Результаты»/«Перепройти», иначе только «Начать».
- Роль сотрудника: команда `teamswitch` (или текстом), далее кнопка «Посмотреть участника» с вводом почты участника (регистронезависимо); IM показывается только сотруднику.
- `/reset` удаляет историю пользователя (ответы, результаты, почту) и возвращает стартовое приветствие.
- Big Five, Hogan, SVS выдают PNG-радары при завершении и по запросу результатов; текст всегда отправляется даже при ошибке построения. Тёмная триада считается внутри Big Five и показывается только сотруднику при поиске участника.

## Установка и запуск
1. Python 3.11+, виртуальное окружение (рекомендуется).
2. Зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Скопируйте `config/env.template` в `.env`, заполните `TELEGRAM_BOT_TOKEN`; при необходимости задайте `DATA_DIR` и `DATABASE_PATH` (по умолчанию `data/bot.db`).
4. Запустите бота:
   ```bash
   python3 -m bot.main
   ```

## Деплой на сервер (пример RUVDS, Ubuntu 24.04)
1. Пользователь: `deploy`, проект в `/home/deploy/bots/Psy-test`, Python 3.12.
2. Клонирование и зависимости:
   ```bash
   git clone <repo> /home/deploy/bots/Psy-test
   cd /home/deploy/bots/Psy-test
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Настройка окружения:
   ```bash
   cp config/env.template .env
   # заполнить TELEGRAM_BOT_TOKEN, при необходимости DATA_DIR/DATABASE_PATH
   ```
4. systemd-сервис `/etc/systemd/system/psybot.service`:
   ```ini
   [Unit]
   Description=Psy-test Telegram bot
   After=network.target

   [Service]
   Type=simple
   WorkingDirectory=/home/deploy/bots/Psy-test
   ExecStart=/home/deploy/bots/Psy-test/.venv/bin/python -m bot.main
   User=deploy
   Restart=always
   Environment=PYTHONUNBUFFERED=1

   [Install]
   WantedBy=multi-user.target
   ```
   Команды управления:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable psybot
   sudo systemctl start psybot
   sudo systemctl status psybot
   journalctl -u psybot -f
   ```
5. SSH keepalive (от обрывов):
   ```bash
   sudo sh -c 'printf "\nClientAliveInterval 60\nClientAliveCountMax 3\nTCPKeepAlive yes\n" >> /etc/ssh/sshd_config'
   sudo systemctl restart ssh
   ```
6. Рекомендуется ставить `tmux` для работы сессий:
   ```bash
   sudo apt install -y tmux
   tmux new -s work   # повторное подключение: tmux attach -t work
   ```
7. Бэкап данных: файл SQLite `data/bot.db` (и `.env`) — копировать/архивировать периодически.

## Использование
1. `/start` — приветствие и inline-меню.
2. Участник: вводит почту → inline-кнопки тестов (по почте определяются доступные «Результаты»/«Перепройти»). Вопросы поддерживают «Назад» и смену ответа.
3. Сотрудник: `teamswitch` → кнопка «Посмотреть участника» → ввод почты участника → выдача доступных результатов. Порядок: если один тест — диаграммы этого теста, потом тексты; если есть Big Five — сначала диаграммы Big Five + Тёмная триада, затем Hogan (если есть), затем тексты. После результатов: «Найти другого участника» / «Вернуться в меню».
4. Кнопки «Результаты <тест>» возвращают последние результаты по почте/пользователю; «Перепройти» — запускают тест заново.
5. `/reset` — стереть свои ответы/результаты/почту и вернуть стартовое меню.

## Тесты и утилиты
- Юнит-тесты: `pytest` (радар, клавиатура).
- Экспорт HEXACO (админ): `python scripts/export_hexaco.py --output exports`.

## Структура
- `bot/` — код бота (handlers, services, keyboards, utils).
- `docs/` — продуктовая/техническая документация, методики тестов.
- `data/` — локальная SQLite-база (создаётся автоматически).
