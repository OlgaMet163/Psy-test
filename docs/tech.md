# Техническая концепция

## Архитектура (факт)
- Telegram Bot API + aiogram 3, режим long polling.
- Локальная SQLite (`data/bot.db`) через `StorageGateway`; таблицы `hexaco_answers`, `hexaco_results`, `participant_emails`.
- Вся логика тестов в боте (handlers + services), хранилище состояний — `MemoryStorage` FSM.

## Обработка тестов
- Три теста: Big Five (24 вопросов + 6 скрытых вопросов Тёмной триады, результаты триады видит только сотрудник), SVS (20), Hogan DSUSI-SF (38).
- Подсчёт: в сервисах `bot/services/*` (percent/mean, band, интерпретации). Для Big Five/Триады используется общая таблица, в БД хранится только последний ответ на утверждение.
- Блокировка параллельных тестов: старт проверяет текущее FSM-состояние.
- `/reset` очищает ответы и результаты пользователя из БД и сбрасывает FSM.

## Визуализация
- Big Five, Hogan, SVS, Тёмная триада: PNG-радары на matplotlib (`bot/utils/plot.py`), отправляются при завершении теста и по запросу результатов. Ошибки логируются, текстовые результаты всегда отправляются. IM отображается только сотруднику; Тёмная триада — только сотруднику.

## Меню и команды
- Только inline-клавиатура. Порядок: «Начать» → «Результаты» → «Перепройти» по каждому тесту (если есть результаты).
- Участник вводит почту; доступность «Результаты/Перепройти» определяется по сохранённой почте. В каждой карточке вопроса есть кнопка «Назад» с подсветкой выбранного ответа и возможностью смены выбора.
- Сотрудник: `teamswitch` → кнопка «Посмотреть участника» (ввод почты участника, регистронезависимо). Если есть Big Five — сначала диаграммы Big Five + Тёмная триада, затем Hogan (если есть), затем тексты. После выдачи результатов — кнопки «Найти другого участника» / «Вернуться в меню».
- Параллельный запуск тестов блокируется FSM.

## Хранение и выгрузка
- Все ответы/результаты сохраняются в SQLite через `StorageGateway`; таблицы `hexaco_answers`/`hexaco_results` общие для всех тестов, `participant_emails` — маппинг почты на пользователя.
- Админский экспорт HEXACO: `python scripts/export_hexaco.py --output exports`.

## Безопасность и приватность
- Минимум PII: Telegram ID, без внешних идентификаторов.
- Пользователь может удалить свои данные `/reset`.

## Деплой / операции (факт)
- Окружение: Ubuntu 24.04, пользователь `deploy`, проект в `/home/deploy/bots/Psy-test`, Python 3.12, SQLite `data/bot.db`.
- Запуск: venv + systemd (`/etc/systemd/system/psybot.service`):
  ```
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
  Команды: `systemctl daemon-reload/enable/start/stop/status psybot`, логи `journalctl -u psybot -f`.
- Конфиг: `.env` из `config/env.template`, обязательный `TELEGRAM_BOT_TOKEN`; при необходимости `DATA_DIR/DATABASE_PATH`.
- SSH keepalive от обрывов: в `sshd_config` включены `ClientAliveInterval 60`, `ClientAliveCountMax 3`, `TCPKeepAlive yes`; на клиенте — `ServerAliveInterval 60`, `ServerAliveCountMax 3` в `~/.ssh/config`.
- Для работы в долгих сессиях — `tmux` (`tmux new -s work`, `tmux attach -t work`).
- Бэкап: копировать `data/bot.db` и `.env` (например, `tar czf backup.tgz data .env`).

## Кодстайл
- Максимальная длина строки кода — 88 символов (black совместим).
- В IDE/Problems длина строки считается нарушением только при превышении 88
  символов; до 88 предупреждений быть не должно.

## Планы
- Перейти на вебхуки/контейнеризацию, вынести расчёты/мэтчинг в backend.
- Расширить экспорт/админ-зону и тестовое покрытие (pytest уже подключён).

