"""Хранилище в памяти и бизнес-правила.

В работе 3 это хранилище заменится на PostgreSQL, а правила останутся.
"""

import threading
from datetime import datetime

from schemas import Match, MatchCreate, MatchUpdate, Team, TeamCreate

# Порядок важен: статус может двигаться только вперёд по этому списку.
STATUSES = ("scheduled", "live", "finished")


class NotFoundError(Exception):
    """Объект не найден -> 404."""


class ConflictError(Exception):
    """Конфликт, например команда с таким названием уже есть -> 409."""


class RuleError(Exception):
    """Нарушено бизнес-правило -> 422."""


def _now() -> datetime:
    # Время с часовым поясом, чтобы в JSON было "...+03:00", как у модуля 2.
    return datetime.now().astimezone()


class Store:
    def __init__(self) -> None:
        # FastAPI выполняет обычные (не async) обработчики в нескольких потоках,
        # поэтому доступ к данным защищаем блокировкой.
        self._lock = threading.Lock()
        self._teams: dict[int, Team] = {}
        self._matches: dict[int, Match] = {}
        self._next_team_id = 1
        self._next_match_id = 1

    # ---------- Команды ----------

    def create_team(self, data: TeamCreate) -> Team:
        name = data.name.strip()
        if not name:
            raise RuleError("invalid team: name must not be empty")
        with self._lock:
            if any(t.name == name for t in self._teams.values()):
                raise ConflictError(f"team '{name}' already exists")
            team = Team(id=self._next_team_id, name=name)
            self._teams[team.id] = team
            self._next_team_id += 1
            return team

    def list_teams(self) -> list[Team]:
        with self._lock:
            return sorted(self._teams.values(), key=lambda t: t.id)

    def get_team(self, team_id: int) -> Team:
        with self._lock:
            team = self._teams.get(team_id)
        if team is None:
            raise NotFoundError(f"team {team_id} not found")
        return team

    # ---------- Матчи ----------

    def create_match(self, data: MatchCreate) -> Match:
        if data.team_a_id == data.team_b_id:
            raise RuleError("invalid match: a team cannot play against itself")
        with self._lock:
            team_a = self._teams.get(data.team_a_id)
            team_b = self._teams.get(data.team_b_id)
            if team_a is None:
                raise RuleError(f"invalid match: team {data.team_a_id} not found")
            if team_b is None:
                raise RuleError(f"invalid match: team {data.team_b_id} not found")
            match = Match(
                id=self._next_match_id,
                team_a=team_a.name,
                team_b=team_b.name,
                score_a=0,
                score_b=0,
                status="scheduled",
                version=1,
                updated_at=_now(),
            )
            self._matches[match.id] = match
            self._next_match_id += 1
            return match

    def list_matches(self) -> list[Match]:
        with self._lock:
            return sorted(self._matches.values(), key=lambda m: m.id)

    def get_match(self, match_id: int) -> Match:
        with self._lock:
            match = self._matches.get(match_id)
        if match is None:
            raise NotFoundError(f"match {match_id} not found")
        return match

    def update_match(self, match_id: int, upd: MatchUpdate) -> Match:
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                raise NotFoundError(f"match {match_id} not found")

            # Сначала все проверки (правило 5: атомарность) ...

            # Итоговый статус: новый, если передан, иначе текущий.
            new_status = upd.status if upd.status is not None else match.status

            # Правило 2: только допустимые статусы.
            if new_status not in STATUSES:
                raise RuleError(
                    f"invalid update: unknown status '{new_status}', "
                    f"expected one of {', '.join(STATUSES)}"
                )

            # Правило 3: статус только вперёд (повтор того же допустим).
            if STATUSES.index(new_status) < STATUSES.index(match.status):
                raise RuleError(
                    f"invalid update: status cannot go back "
                    f"from '{match.status}' to '{new_status}'"
                )

            # Правило 1: счёт не отрицательный.
            for field in ("score_a", "score_b"):
                value = getattr(upd, field)
                if value is not None and value < 0:
                    raise RuleError(f"invalid update: {field} must not be negative")

            # Правило 4: счёт меняется, только если итоговый статус live.
            score_given = upd.score_a is not None or upd.score_b is not None
            if score_given and new_status != "live":
                raise RuleError(
                    f"invalid update: score can only change when match is live "
                    f"(resulting status is '{new_status}')"
                )

            # ... потом все изменения.
            changes: dict = {"status": new_status}
            if upd.score_a is not None:
                changes["score_a"] = upd.score_a
            if upd.score_b is not None:
                changes["score_b"] = upd.score_b
            # Оставляем только то, что действительно отличается.
            changes = {k: v for k, v in changes.items() if getattr(match, k) != v}

            if not changes:
                return match  # ничего не изменилось — версию не трогаем

            # Правило 6: version растёт на 1 при каждом изменении.
            updated = match.model_copy(
                update={**changes, "version": match.version + 1, "updated_at": _now()}
            )
            self._matches[match_id] = updated
            return updated
