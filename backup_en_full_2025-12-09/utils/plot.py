from __future__ import annotations

import math
import tempfile
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from bot.services.hogan import HoganScaleResult
from bot.services.hexaco import HexacoResult
from bot.services.svs import SvsResult


def build_hogan_radar(scales: Sequence[HoganScaleResult]) -> Path:
    """Строит радар-диаграмму по шкалам Hogan и возвращает путь к PNG."""
    if not scales:
        raise ValueError("Нет шкал для построения диаграммы.")

    # Берём только шкалы с видимостью public/internal (все), исключая IM.
    filtered = [s for s in scales if s.scale_id != "IM"]
    labels = [scale.title for scale in filtered]
    values = [max(0.0, min(100.0, scale.percent)) for scale in filtered]

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

    # Границы шкалы 0–100%.
    ax.set_ylim(0, 100)
    yticks = [0, 20, 40, 60, 80, 100]
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"{value}%" for value in yticks], color="white")

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


def build_hexaco_radar(results: Sequence[HexacoResult]) -> Path:
    """Строит радар-диаграмму по публичным шкалам HEXACO, возвращает путь к PNG."""
    if not results:
        raise ValueError("Нет результатов HEXACO для построения диаграммы.")

    # Берём только публичные домены.
    filtered = [r for r in results if r.visibility == "public"]
    if not filtered:
        raise ValueError("Нет публичных результатов HEXACO.")

    labels = [res.title for res in filtered]
    values = [max(0.0, min(100.0, res.percent)) for res in filtered]

    angles = [n / float(len(labels)) * 2 * math.pi for n in range(len(labels))]
    angles_closed = angles + angles[:1]
    values_closed = values + values[:1]

    face_color = "#1f2647"
    polygon_color = "#2ca8c2"  # отличающийся от Hogan
    point_palette = [
        "#f29f05",
        "#8a5be8",
        "#24c1f1",
        "#6bc06b",
        "#f47b94",
        "#4dd0e1",
    ]

    fig, ax = plt.subplots(subplot_kw={"polar": True}, figsize=(8, 8))
    fig.patch.set_facecolor(face_color)
    ax.set_facecolor(face_color)
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_ylim(0, 100)
    yticks = [0, 20, 40, 60, 80, 100]
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"{value}%" for value in yticks], color="white")

    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.5, color="white")
    ax.spines["polar"].set_color("white")

    ax.set_xticks(angles_closed[:-1])
    ax.set_xticklabels(labels, fontsize=10, color="white")

    ax.plot(
        angles_closed,
        values_closed,
        color=polygon_color,
        linewidth=2,
        linestyle="solid",
    )
    ax.fill(angles_closed, values_closed, color=polygon_color, alpha=0.35)

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

    ax.set_title(
        "HEXACO traits",
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


def build_svs_radar(results: Sequence[SvsResult]) -> Path:
    """Строит радар-диаграмму по ценностям SVS, возвращает путь к PNG."""
    if not results:
        raise ValueError("Нет результатов SVS для построения диаграммы.")

    values = [r for r in results if r.category == "value" and r.visibility == "public"]
    if not values:
        values = [r for r in results if r.visibility == "public"]
    if not values:
        raise ValueError("Нет публичных результатов SVS.")

    labels = [res.title for res in values]
    scores = [max(0.0, min(100.0, res.percent)) for res in values]

    angles = [n / float(len(labels)) * 2 * math.pi for n in range(len(labels))]
    angles_closed = angles + angles[:1]
    scores_closed = scores + scores[:1]

    face_color = "#1f2647"
    polygon_color = "#b14ba7"  # новый цвет, отличный от Hogan/HEXACO
    point_palette = [
        "#4dd0e1",
        "#f47b94",
        "#8a5be8",
        "#6bc06b",
        "#f29f05",
        "#24c1f1",
        "#ffa07a",
        "#7ac36a",
        "#c798f3",
        "#ffb347",
    ]

    fig, ax = plt.subplots(subplot_kw={"polar": True}, figsize=(8, 8))
    fig.patch.set_facecolor(face_color)
    ax.set_facecolor(face_color)
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_ylim(0, 100)
    yticks = [0, 20, 40, 60, 80, 100]
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"{value}%" for value in yticks], color="white")

    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.5, color="white")
    ax.spines["polar"].set_color("white")

    ax.set_xticks(angles_closed[:-1])
    ax.set_xticklabels(labels, fontsize=10, color="white")

    ax.plot(
        angles_closed,
        scores_closed,
        color=polygon_color,
        linewidth=2,
        linestyle="solid",
    )
    ax.fill(angles_closed, scores_closed, color=polygon_color, alpha=0.35)

    for idx, (angle, value) in enumerate(zip(angles, scores)):
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

    ax.set_title(
        "SVS values",
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
