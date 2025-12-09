from __future__ import annotations

import math
import tempfile
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from bot.services.hogan import HoganScaleResult


def build_hogan_radar(scales: Sequence[HoganScaleResult]) -> Path:
    """Строит радар-диаграмму по шкалам Hogan и возвращает путь к PNG."""
    if not scales:
        raise ValueError("Нет шкал для построения диаграммы.")

    # Берём только шкалы с видимостью public/internal (все), исключая IM.
    filtered = [s for s in scales if s.scale_id != "IM"]
    labels = [scale.title for scale in filtered]
    values = [scale.mean_score for scale in filtered]

    # Углы для N шкал и закрытый контур.
    angles = [n / float(len(labels)) * 2 * math.pi for n in range(len(labels))]
    angles_closed = angles + angles[:1]
    labels_closed = labels + [labels[0]]
    values_closed = values + [values[0]]

    # Цвета в стиле референса.
    face_color = "#1f2647"  # тёмный фон
    polygon_color = "#d6a23e"
    point_palette = [
        "#e64b3c",  # red
        "#8a5be8",  # purple
        "#24c1f1",  # cyan
        "#6bc06b",  # green
        "#f29f05",  # amber
        "#f47b94",  # pink
        "#4dd0e1",  # light teal
        "#ffb347",  # light orange
        "#7ac36a",  # light green
        "#c798f3",  # light purple
        "#ffa07a",  # light salmon (reserve)
    ]

    fig, ax = plt.subplots(subplot_kw={"polar": True}, figsize=(8, 8))
    fig.patch.set_facecolor(face_color)
    ax.set_facecolor(face_color)
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    # Границы шкалы 1–5.
    ax.set_ylim(0, 5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], color="white")

    # Гриды светлые.
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.5, color="white")
    ax.spines["polar"].set_color("white")

    # Подписи шкал.
    ax.set_xticks(angles_closed[:-1])
    ax.set_xticklabels(labels, fontsize=10, color="white")

    # Линия и заливка.
    ax.plot(
        angles_closed,
        values_closed,
        color=polygon_color,
        linewidth=2,
        linestyle="solid",
    )
    ax.fill(angles_closed, values_closed, color=polygon_color, alpha=0.35)

    # Цветные точки по вершинам (без дублирующей последней).
    for idx, (angle, value) in enumerate(zip(angles, values)):
        color = point_palette[idx % len(point_palette)]
        ax.scatter(
            angle,
            value,
            color=color,
            s=70,
            edgecolors="white",
            linewidths=1,
            zorder=3,
        )

    # Заголовок.
    ax.set_title(
        "Hogan traits",
        color="white",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )

    fig.tight_layout()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp_path = Path(tmp.name)
    tmp.close()
    fig.savefig(tmp_path, dpi=150)
    plt.close(fig)
    return tmp_path
