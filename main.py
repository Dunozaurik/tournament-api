"""Модуль 1: REST API регистрации команд и матчей."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from schemas import Match, MatchCreate, MatchUpdate, Team, TeamCreate
from store import ConflictError, NotFoundError, RuleError, Store

app = FastAPI(title="Tournament API", version="0.1")
store = Store()


# ---------- Ошибки в едином формате {"error": "..."} ----------

def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@app.exception_handler(NotFoundError)
async def handle_not_found(request: Request, exc: NotFoundError):
    return _error(404, str(exc))


@app.exception_handler(ConflictError)
async def handle_conflict(request: Request, exc: ConflictError):
    return _error(409, str(exc))


@app.exception_handler(RuleError)
async def handle_rule(request: Request, exc: RuleError):
    return _error(422, str(exc))


@app.exception_handler(RequestValidationError)
async def handle_bad_request(request: Request, exc: RequestValidationError):
    # Невалидный JSON, неизвестное поле, неверный тип, id не число -> 400.
    first = exc.errors()[0]
    where = ".".join(str(p) for p in first["loc"] if p != "body")
    return _error(400, f"bad request: {where}: {first['msg']}")


@app.exception_handler(StarletteHTTPException)
async def handle_http(request: Request, exc: StarletteHTTPException):
    # Например, несуществующий маршрут или неподдерживаемый метод.
    return _error(exc.status_code, str(exc.detail))


# ---------- Служебное ----------

@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"


# ---------- Команды ----------

@app.post("/teams", response_model=Team, status_code=201)
def create_team(data: TeamCreate):
    return store.create_team(data)


@app.get("/teams", response_model=list[Team])
def list_teams():
    return store.list_teams()


@app.get("/teams/{team_id}", response_model=Team)
def get_team(team_id: int):
    return store.get_team(team_id)


# ---------- Матчи ----------

@app.post("/matches", response_model=Match, status_code=201)
def create_match(data: MatchCreate):
    return store.create_match(data)


@app.get("/matches", response_model=list[Match])
def list_matches():
    return store.list_matches()


@app.get("/matches/{match_id}", response_model=Match)
def get_match(match_id: int):
    return store.get_match(match_id)


@app.patch("/matches/{match_id}", response_model=Match)
def update_match(match_id: int, upd: MatchUpdate):
    return store.update_match(match_id, upd)
