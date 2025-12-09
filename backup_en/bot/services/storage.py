from __future__ import annotations

import datetime as dt
from pathlib import Path
import csv
from typing import Iterable, List, Optional

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
            await db.commit()
        self._initialized = True

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
                impression = mean_score
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
