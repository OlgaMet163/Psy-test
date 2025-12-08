#!/usr/bin/env python3
import argparse
import asyncio
from pathlib import Path

from bot.config import get_settings
from bot.services import StorageGateway


async def run(output_dir: Path) -> None:
    settings = get_settings()
    storage = StorageGateway(settings.database_path)
    await storage.init()

    answers_path = output_dir / "hexaco_answers.csv"
    results_path = output_dir / "hexaco_results.csv"

    exported_answers = await storage.export_table("hexaco_answers", answers_path)
    exported_results = await storage.export_table("hexaco_results", results_path)

    print(f"Ответы экспортированы в {exported_answers}")
    print(f"Результаты экспортированы в {exported_results}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Экспорт результатов HEXACO в CSV.")
    parser.add_argument(
        "--output",
        default="exports",
        help="Папка, куда складывать CSV (по умолчанию ./exports)",
    )
    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    asyncio.run(run(output_dir))


if __name__ == "__main__":
    main()

