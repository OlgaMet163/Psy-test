from pathlib import Path

from bot.services.hogan import HoganScaleResult
from bot.utils.plot import build_hogan_radar


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
