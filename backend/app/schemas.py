"""Pydantic schemas mirroring docs/api_contract.md. Request bodies forbid unknown fields."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Level = Literal["low", "moderate", "high", "very_high"]
Language = Literal["es", "en"]
Profile = Literal["producer", "resident"]
Threshold = Literal[30, 50, 70]
Channel = Literal["push", "email"]
Purpose = Literal["login", "notification_email"]


class StrictIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# Auth

class EmailRequestIn(StrictIn):
    email: EmailStr
    purpose: Purpose = "login"


class EmailVerifyIn(StrictIn):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")
    purpose: Purpose = "login"


class UserOut(BaseModel):
    id: str
    email: str
    name: str | None
    language: Language
    profile: Profile
    crops: list[str]
    livestock: list[str]
    default_threshold: Threshold
    notification_email: str
    onboarded: bool


class VerifyOut(BaseModel):
    session_token: str
    user: UserOut


class UserOnlyOut(BaseModel):
    user: UserOut


class UserPatchIn(StrictIn):
    name: str | None = Field(default=None, max_length=80)
    language: Language | None = None
    profile: Profile | None = None
    crops: list[str] | None = Field(default=None, max_length=20)
    livestock: list[str] | None = Field(default=None, max_length=20)
    default_threshold: Threshold | None = None
    onboarded: bool | None = None

    @field_validator("crops", "livestock")
    @classmethod
    def _tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        out = []
        for item in v:
            item = item.strip()
            if not (1 <= len(item) <= 40) or not all(c.isalnum() or c in " .-_" for c in item):
                raise ValueError("each item must be 1 to 40 letters, digits, spaces, dots or dashes")
            out.append(item)
        return out


class DeviceIn(StrictIn):
    expo_push_token: str = Field(min_length=10, max_length=200)


# Geo and risk

class Driver(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature: str = Field(min_length=1, max_length=80)
    effect: Literal["up", "down"]
    weight: float


class DriverGroup(BaseModel):
    theme: str
    label_es: str
    label_en: str
    effect: Literal["up", "down"]
    weight: float


class Reliability(BaseModel):
    model_config = ConfigDict(extra="forbid")
    range: tuple[float, float]
    observed_rate: float = Field(ge=0, le=1)
    n: int = Field(ge=0)


class Observed(BaseModel):
    frost: bool
    tmin_c: float


class CellOut(BaseModel):
    point_id: str
    name: str
    lat: float
    lon: float
    elevation_m: float
    probability: float
    level: Level
    top_drivers: list[Driver]
    driver_groups: list[DriverGroup]  # addition to the contract, see docs/backend_notes.md
    conditions_1800: dict[str, float]
    historical_reliability: Reliability
    observed: Observed | None = None


class MapOut(BaseModel):
    night_date: str
    data_source: str
    model_version: str
    cells: list[CellOut]


class NightsOut(BaseModel):
    latest: str
    available: list[str]


class PolygonIn(StrictIn):
    type: Literal["Polygon"]
    coordinates: list[list[tuple[float, float]]] = Field(min_length=1, max_length=1)


class Channels(StrictIn):
    push: bool
    email: bool


class AoiCreateIn(StrictIn):
    name: str = Field(min_length=1, max_length=80)
    polygon: PolygonIn
    threshold: Threshold
    channels: Channels


class AoiPatchIn(StrictIn):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    threshold: Threshold | None = None
    channels: Channels | None = None


class AoiCurrent(BaseModel):
    night_date: str
    probability: float
    level: Level
    cell_used: str
    distance_km: float


class AoiOut(BaseModel):
    id: str
    name: str
    polygon: dict
    threshold: Threshold
    channels: Channels
    current: AoiCurrent | None = None


# Alerts

class AlertSummary(BaseModel):
    id: str
    aoi_id: str
    aoi_name: str
    night_date: str
    level: Level
    probability: float
    channels_sent: list[Channel]
    sent_at: str
    read: bool
    headline: str


class ExplanationOut(BaseModel):
    headline: str
    why: str
    actions: list[str]
    caveats: list[str]


class AlertDetail(AlertSummary):
    explanation: ExplanationOut
    conditions_1800: dict[str, float]
    top_drivers: list[Driver]
    driver_groups: list[DriverGroup]
    historical_reliability: Reliability
    outcome: Observed | None
    model_card_summary: str
    data_source: str
    mode: str
