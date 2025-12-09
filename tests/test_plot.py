from pathlib import Path

from bot.services.hogan import HoganScaleResult
from bot.services.hexaco import HexacoResult
from bot.services.svs import SvsResult
from bot.utils.plot import (
    build_hogan_radar,
    build_hexaco_radar,
    build_svs_radar,
)


def test_build_hogan_radar_creates_file(tmp_path: Path):
    scales = [
        HoganScaleResult(
            scale_id=f"id{i}",
            title=f"Scale {i}",
            hds_label=f"S{i}",
            mean_score=1 + i % 5,
            percent=20 * i,
            level_id="medium",
            level_label="Medium",
            interpretation="",
            visibility="public",
        )
        for i in range(10)
    ]
    path = build_hogan_radar(scales)
    assert path.exists()
    # Move to tmp to avoid clutter
    target = tmp_path / path.name
    path.replace(target)
    assert target.exists()


def test_build_hexaco_radar_creates_file(tmp_path: Path):
    results = [
        HexacoResult(
            domain_id=f"id{i}",
            title=f"Domain {i}",
            percent=10 * i,
            band_id="medium",
            band_label="Medium",
            interpretation="",
            visibility="public",
        )
        for i in range(1, 7)
    ]
    path = build_hexaco_radar(results)
    assert path.exists()
    target = tmp_path / path.name
    path.replace(target)
    assert target.exists()


def test_build_svs_radar_creates_file(tmp_path: Path):
    results = [
        SvsResult(
            domain_id=f"id{i}",
            title=f"Value {i}",
            mean_score=3.0,
            percent=10 * i,
            band_id="medium",
            band_label="Medium",
            interpretation="",
            visibility="public",
            category="value",
        )
        for i in range(1, 6)
    ]
    path = build_svs_radar(results)
    assert path.exists()
    target = tmp_path / path.name
    path.replace(target)
    assert target.exists()
