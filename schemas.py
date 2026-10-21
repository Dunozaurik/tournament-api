"""Схемы данных (что приходит в запросах и что уходит в ответах)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ---------- Команды ----------

class TeamCreate(BaseModel):
    """Тело POST /teams."""
    model_config = ConfigDict(extra="forbid")  # неизвестные поля -> 400

    name: str


class Team(BaseModel):
    id: int
    name: str


# ---------- Матчи ----------

class MatchCreate(BaseModel):
    """Тело POST /matches."""
    model_config = ConfigDict(extra="forbid")

    team_a_id: int
    team_b_id: int


class MatchUpdate(BaseModel):
    """Тело PATCH /matches/{id}: все поля необязательные."""
    model_config = ConfigDict(extra="forbid")

    score_a: int | None = None
    score_b: int | None = None
    # Статус намеренно строка, а не Enum: недопустимый статус —
    # это нарушение бизнес-правила (422), как в модуле 2, а не кривой запрос (400).
    status: str | None = None


class Match(BaseModel):
    """Матч в том виде, как его ждёт модуль 2 (табло)."""
    id: int
    team_a: str          # названия команд, не id
    team_b: str
    score_a: int
    score_b: int
    status: str          # scheduled | live | finished
    version: int         # +1 при каждом изменении, начальное значение 1
    updated_at: datetime  # отдаётся в формате RFC 3339
