from __future__ import annotations

import datetime as dt
from pathlib import Path

# flake8: noqa: E501
import csv
from typing import Dict, Iterable, List, Optional, Sequence

import aiosqlite

from bot.services.hexaco import HexacoResult
from bot.services.hogan import HoganReport, HoganScaleResult, SCALE_DEFINITIONS
from bot.services.svs import SvsResult

ResultLike = HexacoResult | HoganScaleResult | SvsResult
HOGAN_LABELS = {definition.id: definition.hds_label for definition in SCALE_DEFINITIONS}


class StorageGateway:
    """Асинхронное хранилище на SQLite для ответов и результатов."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._initialized = False

    async def init(self) -> None:
        if self._initialized:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS hexaco_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    test_name TEXT NOT NULL,
                    statement_id INTEGER NOT NULL,
                    raw_value INTEGER NOT NULL,
                    label TEXT
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS hexaco_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    test_name TEXT NOT NULL,
                    domain_id TEXT NOT NULL,
                    domain_title TEXT NOT NULL,
                    percent REAL NOT NULL,
                    band_id TEXT NOT NULL,
                    band_label TEXT NOT NULL,
                    visibility TEXT NOT NULL,
                    interpretation TEXT
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS participant_emails (
                    email TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    undo_count INTEGER NOT NULL DEFAULT 0,
                    username TEXT
                )
                """
            )
            await db.commit()
            await self._backfill_user_stats(db)
            await self._ensure_user_stats_username(db)
        self._initialized = True

    async def _ensure_user_stats_username(self, db: aiosqlite.Connection) -> None:
        # Добавляем колонку username, если её ещё нет (обратная совместимость).
        try:
            await db.execute("ALTER TABLE user_stats ADD COLUMN username TEXT")
            await db.commit()
        except Exception:
            # колонка уже существует
            pass

    async def _backfill_user_stats(self, db: aiosqlite.Connection) -> None:
        # Заполняем user_stats по историческим данным, если там ещё пусто.
        await db.execute(
            """
            INSERT OR IGNORE INTO user_stats (user_id, first_seen, last_seen, undo_count)
            SELECT user_id, MIN(created_at), MAX(created_at), 0
            FROM (
                SELECT user_id, created_at FROM hexaco_answers
                UNION ALL
                SELECT user_id, created_at FROM hexaco_results
            )
            GROUP BY user_id
            """
        )
        await db.commit()

    async def save_answer(
        self,
        user_id: int,
        test_name: str,
        statement_id: int,
        raw_value: int,
        label: str,
        timestamp: dt.datetime | None = None,
    ) -> None:
        await self.init()
        timestamp = timestamp or dt.datetime.now(dt.timezone.utc)
        async with aiosqlite.connect(self.db_path) as db:
            # храним только последний ответ на утверждение для пользователя/теста
            await db.execute(
                """
                DELETE FROM hexaco_answers
                WHERE user_id = ? AND test_name = ? AND statement_id = ?
                """,
                (user_id, test_name, statement_id),
            )
            await db.execute(
                """
                INSERT INTO hexaco_answers (created_at, user_id, test_name, statement_id, raw_value, label)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp.isoformat(),
                    user_id,
                    test_name,
                    statement_id,
                    raw_value,
                    label,
                ),
            )
            await db.commit()

    async def save_results(
        self,
        user_id: int,
        test_name: str,
        results: Iterable[ResultLike],
        timestamp: dt.datetime | None = None,
    ) -> None:
        await self.init()
        timestamp = timestamp or dt.datetime.now(dt.timezone.utc)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """
                INSERT INTO hexaco_results (
                    created_at,
                    user_id,
                    test_name,
                    domain_id,
                    domain_title,
                    percent,
                    band_id,
                    band_label,
                    visibility,
                    interpretation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        timestamp.isoformat(),
                        user_id,
                        test_name,
                        result.domain_id,
                        result.title,
                        result.percent,
                        result.band_id,
                        result.band_label,
                        result.visibility,
                        result.interpretation,
                    )
                    for result in results
                ],
            )
            await db.commit()

    async def has_results(self, user_id: int, test_name: str) -> bool:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM hexaco_results WHERE user_id = ? AND test_name = ? LIMIT 1",
                (user_id, test_name),
            )
            row = await cursor.fetchone()
            return row is not None

    async def has_hexaco_results(self, user_id: int, test_name: str = "HEXACO") -> bool:
        return await self.has_results(user_id, test_name)

    async def fetch_latest_hexaco_results(
        self, user_id: int, test_name: str = "HEXACO"
    ) -> List[HexacoResult]:
        rows = await self._fetch_latest_rows(user_id, test_name)
        results: List[HexacoResult] = []
        for row in rows:
            results.append(
                HexacoResult(
                    domain_id=row["domain_id"],
                    title=row["domain_title"],
                    percent=row["percent"],
                    band_id=row["band_id"],
                    band_label=row["band_label"],
                    interpretation=row["interpretation"],
                    visibility=row["visibility"],
                )
            )
        return results

    async def fetch_latest_hogan_report(
        self, user_id: int, test_name: str = "HOGAN"
    ) -> Optional[HoganReport]:
        rows = await self._fetch_latest_rows(user_id, test_name)
        if not rows:
            return None
        scales: List[HoganScaleResult] = []
        impression = 0.0
        for row in rows:
            percent = row["percent"]
            mean_score = round((percent / 100) * 4 + 1, 2)
            scale_id = row["domain_id"]
            if scale_id == "IM":
                impression = round(percent / 100, 2)
                continue
            scales.append(
                HoganScaleResult(
                    scale_id=scale_id,
                    title=row["domain_title"],
                    hds_label=HOGAN_LABELS.get(scale_id, scale_id),
                    mean_score=mean_score,
                    percent=percent,
                    level_id=row["band_id"],
                    level_label=row["band_label"],
                    interpretation=row["interpretation"] or "",
                    visibility=row["visibility"],
                )
            )
        return HoganReport(scales=scales, impression_management=impression)

    async def fetch_latest_svs_results(
        self, user_id: int, test_name: str = "SVS"
    ) -> List[SvsResult]:
        rows = await self._fetch_latest_rows(user_id, test_name)
        results: List[SvsResult] = []
        for row in rows:
            percent = row["percent"]
            mean_score = round((percent / 100) * 6 + 1, 2)
            category = (
                "group" if str(row["domain_id"]).startswith("group_") else "value"
            )
            results.append(
                SvsResult(
                    domain_id=row["domain_id"],
                    title=row["domain_title"],
                    mean_score=mean_score,
                    percent=percent,
                    band_id=row["band_id"],
                    band_label=row["band_label"],
                    interpretation=row["interpretation"] or "",
                    visibility=row["visibility"],
                    category=category,
                )
            )
        return results

    async def export_table(self, table_name: str, output_path: Path) -> Path:
        """Выгружает указанную таблицу в CSV и возвращает путь к файлу."""
        await self.init()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"SELECT * FROM {table_name} ORDER BY created_at ASC"
            )
            rows = await cursor.fetchall()
        if not rows:
            # создаём пустой файл только с заголовком
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in await cursor.fetchall()]
        else:
            columns = rows[0].keys()

        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([row[column] for column in columns])
        return output_path

    async def clear_user_data(self, user_id: int) -> None:
        """Полностью удаляет ответы и результаты пользователя."""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM hexaco_answers WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM hexaco_results WHERE user_id = ?", (user_id,))
            await db.commit()

    async def save_participant_email(self, user_id: int, email: str) -> None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO participant_emails (email, user_id)
                VALUES (?, ?)
                """,
                (email.lower(), user_id),
            )
            await db.commit()

    async def get_user_id_by_email(self, email: str) -> Optional[int]:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id FROM participant_emails WHERE email = ? LIMIT 1",
                (email.lower(),),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def _fetch_latest_rows(
        self, user_id: int, test_name: str
    ) -> List[aiosqlite.Row]:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT MAX(created_at) FROM hexaco_results WHERE user_id = ? AND test_name = ?",
                (user_id, test_name),
            )
            row = await cursor.fetchone()
            if not row or row[0] is None:
                return []
            latest_ts = row[0]
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT domain_id, domain_title, percent, band_id, band_label, visibility, interpretation
                FROM hexaco_results
                WHERE user_id = ? AND test_name = ? AND created_at = ?
                ORDER BY domain_title
                """,
                (user_id, test_name, latest_ts),
            )
            rows = await cursor.fetchall()
        return rows

    async def record_user_activity(
        self,
        user_id: int,
        username: str | None = None,
        timestamp: dt.datetime | None = None,
    ) -> None:
        """Фиксирует время первого/последнего посещения пользователя."""
        await self.init()
        ts = (timestamp or dt.datetime.now(dt.timezone.utc)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO user_stats (user_id, first_seen, last_seen, undo_count, username)
                VALUES (?, ?, ?, 0, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET
                    last_seen=excluded.last_seen,
                    username=COALESCE(excluded.username, user_stats.username)
                """,
                (user_id, ts, ts, username),
            )
            await db.commit()

    async def increment_undo(
        self,
        user_id: int,
        timestamp: dt.datetime | None = None,
        username: str | None = None,
    ) -> None:
        """Увеличивает счётчик нажатий «Назад» и обновляет last_seen."""
        await self.init()
        ts = (timestamp or dt.datetime.now(dt.timezone.utc)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO user_stats (user_id, first_seen, last_seen, undo_count, username)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET
                    last_seen=excluded.last_seen,
                    undo_count=user_stats.undo_count + 1,
                    username=COALESCE(excluded.username, user_stats.username)
                """,
                (user_id, ts, ts, username),
            )
            await db.commit()

    async def fetch_admin_stats(
        self, now: dt.datetime | None = None
    ) -> Dict[str, float | int]:
        """Возвращает агрегированную статистику для админ-панели."""
        await self.init()
        now = now or dt.datetime.now(dt.timezone.utc)
        start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - dt.timedelta(days=7)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM user_stats")
            total_users = (await cursor.fetchone() or [0])[0]

            cursor = await db.execute(
                "SELECT COUNT(*) FROM user_stats WHERE last_seen >= ?",
                (start_today.isoformat(),),
            )
            today_users = (await cursor.fetchone() or [0])[0]

            cursor = await db.execute(
                "SELECT COUNT(*) FROM user_stats WHERE last_seen >= ?",
                (week_ago.isoformat(),),
            )
            week_users = (await cursor.fetchone() or [0])[0]

            cursor = await db.execute(
                """
                SELECT COUNT(DISTINCT user_id)
                FROM hexaco_results
                WHERE test_name = 'HEXACO'
                """
            )
            finished_hexaco = (await cursor.fetchone() or [0])[0]

            cursor = await db.execute(
                """
                SELECT COUNT(DISTINCT user_id)
                FROM hexaco_results
                WHERE test_name = 'SVS'
                """
            )
            finished_svs = (await cursor.fetchone() or [0])[0]

            cursor = await db.execute(
                """
                SELECT COUNT(DISTINCT user_id)
                FROM hexaco_results
                WHERE test_name = 'HOGAN'
                """
            )
            finished_hogan = (await cursor.fetchone() or [0])[0]

            cursor = await db.execute(
                """
                SELECT AVG(hr.percent)
                FROM hexaco_results hr
                JOIN (
                    SELECT user_id, MAX(created_at) AS ts
                    FROM hexaco_results
                    WHERE test_name = 'HOGAN'
                    GROUP BY user_id
                ) latest ON latest.user_id = hr.user_id AND latest.ts = hr.created_at
                WHERE hr.test_name = 'HOGAN' AND hr.domain_id = 'IM'
                """
            )
            avg_im_row = await cursor.fetchone()
            avg_bullshit = avg_im_row[0] if avg_im_row else None

        return {
            "total_users": total_users,
            "today_users": today_users,
            "week_users": week_users,
            "finished_hexaco": finished_hexaco,
            "finished_svs": finished_svs,
            "finished_hogan": finished_hogan,
            "avg_bullshit": round(avg_bullshit, 2) if avg_bullshit is not None else None,
        }

    async def export_users_csv(self, output_path: Path) -> Path:
        """Формирует CSV по пользователям с результатами и статистикой."""
        await self.init()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        hexaco_domains = (
            "honesty_humility",
            "neurotism",
            "extraversion",
            "agreeableness",
            "conscientiousness",
            "openness",
            "dt_machiavellianism",
            "dt_narcissism",
            "dt_psychopathy",
        )
        svs_values = ("SD", "ST", "HE", "AC", "PO", "SEC", "CO", "TR", "BE", "UN")
        svs_groups = (
            "group_openness_change",
            "group_self_enhancement",
            "group_conservation",
            "group_self_transcendence",
        )
        hogan_scales = [definition.id for definition in SCALE_DEFINITIONS]

        header = [
            "tg_id",
            "tg_name",
            "Email",
            "Date",
            "Tests finished",
            *hexaco_domains,
            *svs_values,
            *svs_groups,
            *hogan_scales,
            "Bullshit",
            "Undo",
        ]

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id, first_seen, undo_count, username FROM user_stats ORDER BY first_seen"
            )
            users = await cursor.fetchall()

            with output_path.open("w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(header)

                for row in users:
                    user_id = row["user_id"]
                    first_seen = row["first_seen"]
                    undo_count = row["undo_count"]
                    username = row["username"] or ""
                    tg_name = f"@{username}" if username else ""
                    email = await self._fetch_email_by_user_id(db, user_id)

                    hexaco_map = await self._fetch_latest_results_map(
                        db, user_id, "HEXACO"
                    )
                    hogan_map = await self._fetch_latest_results_map(
                        db, user_id, "HOGAN"
                    )
                    svs_map = await self._fetch_latest_results_map(db, user_id, "SVS")

                    tests_finished = (
                        "yes"
                        if hexaco_map and hogan_map and svs_map
                        else "no"
                    )
                    bullshit_percent = hogan_map.get("IM", "")

                    row_values: List[Sequence[float | str | int]] = [
                        [user_id],
                        [tg_name],
                        [email or ""],
                        [first_seen.split("T")[0] if first_seen else ""],
                        [tests_finished],
                        [hexaco_map.get(key, "") for key in hexaco_domains],
                        [svs_map.get(key, "") for key in svs_values],
                        [svs_map.get(key, "") for key in svs_groups],
                        [hogan_map.get(key, "") for key in hogan_scales],
                        [bullshit_percent],
                        [undo_count],
                    ]

                    flat: List[float | str | int] = []
                    for chunk in row_values:
                        flat.extend(chunk)
                    writer.writerow(flat)

        return output_path

    async def _fetch_latest_results_map(
        self, db: aiosqlite.Connection, user_id: int, test_name: str
    ) -> Dict[str, float]:
        cursor = await db.execute(
            "SELECT MAX(created_at) FROM hexaco_results WHERE user_id = ? AND test_name = ?",
            (user_id, test_name),
        )
        row = await cursor.fetchone()
        if not row or row[0] is None:
            return {}
        ts = row[0]
        cursor = await db.execute(
            """
            SELECT domain_id, percent
            FROM hexaco_results
            WHERE user_id = ? AND test_name = ? AND created_at = ?
            """,
            (user_id, test_name, ts),
        )
        rows = await cursor.fetchall()
        return {domain_id: percent for domain_id, percent in rows}

    async def _fetch_email_by_user_id(
        self, db: aiosqlite.Connection, user_id: int
    ) -> Optional[str]:
        cursor = await db.execute(
            "SELECT email FROM participant_emails WHERE user_id = ? LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else None
