from dataclasses import dataclass, fields
from datetime import date
import re
import unicodedata


BUILDING_ALIASES = {
    "主教学楼": "主教学楼",
    "主教楼": "主教学楼",
    "主教": "主教学楼",
    "图书馆": "图书馆",
    "实验楼": "实验楼",
}
BUILDING_PATTERN = re.compile("|".join(map(re.escape, BUILDING_ALIASES)))
ROOM_PATTERN = re.compile(r"(?<![A-Z0-9])([A-Z]?\d{3,4}[A-Z]?)(?![A-Z0-9楼层])")


@dataclass(frozen=True)
class CampusLocation:
    building: str | None = None
    room: str | None = None


@dataclass(frozen=True)
class MatchFeatures:
    cosine_similarity: float
    date_gap_days: int
    date_missing: int
    building_match: int
    building_missing: int
    room_match: int
    room_missing: int


FEATURE_NAMES = tuple(field.name for field in fields(MatchFeatures))


def parse_location(value: str | None) -> CampusLocation:
    normalized = unicodedata.normalize("NFKC", value or "").strip().upper()
    building = BUILDING_PATTERN.search(normalized)
    room = ROOM_PATTERN.search(normalized)
    return CampusLocation(
        building=BUILDING_ALIASES[building.group()] if building else None,
        room=room.group(1) if room else None,
    )


def make_match_features(
    cosine_similarity: float,
    lost_on: date | None,
    lost_location: CampusLocation,
    found_on: date | None,
    found_location: CampusLocation,
) -> MatchFeatures:
    date_missing = lost_on is None or found_on is None
    date_gap_days = abs((lost_on - found_on).days) if not date_missing else 0

    building_missing = not (lost_location.building and found_location.building)
    building_match = not building_missing and lost_location.building == found_location.building
    room_missing = building_missing or not (lost_location.room and found_location.room)
    room_match = building_match and not room_missing and lost_location.room == found_location.room

    return MatchFeatures(
        cosine_similarity=cosine_similarity,
        date_gap_days=date_gap_days,
        date_missing=int(date_missing),
        building_match=int(building_match),
        building_missing=int(building_missing),
        room_match=int(room_match),
        room_missing=int(room_missing),
    )
