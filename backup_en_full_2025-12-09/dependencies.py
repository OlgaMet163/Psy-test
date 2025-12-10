from __future__ import annotations

from typing import Optional

from bot.services import (
    HexacoEngine,
    HoganAtlasInsights,
    HoganEngine,
    HoganInsights,
    SvsEngine,
    StorageGateway,
)

hexaco_engine: Optional[HexacoEngine] = None
hogan_engine: Optional[HoganEngine] = None
hogan_insights: Optional[HoganInsights] = None
hogan_atlas: Optional[HoganAtlasInsights] = None
svs_engine: Optional[SvsEngine] = None
storage_gateway: Optional[StorageGateway] = None


def init(
    hexaco: HexacoEngine,
    hogan: HoganEngine,
    svs: SvsEngine,
    storage: StorageGateway,
    insights: HoganInsights,
    atlas: HoganAtlasInsights,
) -> None:
    global hexaco_engine, hogan_engine, hogan_insights, hogan_atlas, svs_engine, storage_gateway
    hexaco_engine = hexaco
    hogan_engine = hogan
    hogan_insights = insights
    hogan_atlas = atlas
    svs_engine = svs
    storage_gateway = storage
