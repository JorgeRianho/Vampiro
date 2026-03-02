import random
import string
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generar_ciclo_unico(player_ids: list[str]) -> dict[str, str]:
    n = len(player_ids)
    if n < 2:
        raise ValueError("Se necesitan al menos 2 jugadores.")

    while True:
        perm = list(range(n))
        random.shuffle(perm)
        if any(i == perm[i] for i in range(n)):
            continue

        visitados = set()
        actual = 0
        for _ in range(n):
            visitados.add(actual)
            actual = perm[actual]

        if len(visitados) == n and actual == 0:
            return {player_ids[i]: player_ids[perm[i]] for i in range(n)}


def asignar_pruebas_validas(player_ids: list[str], pruebas_por_jugador: dict[str, list[str]]) -> dict[str, str]:
    pruebas_disponibles = []
    for pid in player_ids:
        for idx, txt in enumerate(pruebas_por_jugador.get(pid, []), start=1):
            texto = txt.strip()
            if texto:
                pruebas_disponibles.append({"id": f"{pid}-{idx}-{uuid.uuid4().hex[:6]}", "autor": pid, "texto": texto})

    if len(pruebas_disponibles) < len(player_ids):
        raise ValueError("No hay pruebas suficientes para repartir.")

    opciones: dict[str, list[int]] = {}
    for pid in player_ids:
        indices = [i for i, p in enumerate(pruebas_disponibles) if p["autor"] != pid]
        random.shuffle(indices)
        if not indices:
            raise ValueError("No hay una asignacion valida de pruebas.")
        opciones[pid] = indices

    asignada_a_prueba: dict[int, str] = {}

    def buscar(pid: str, visitadas: set[int]) -> bool:
        for idx in opciones[pid]:
            if idx in visitadas:
                continue
            visitadas.add(idx)
            if idx not in asignada_a_prueba or buscar(asignada_a_prueba[idx], visitadas):
                asignada_a_prueba[idx] = pid
                return True
        return False

    orden = list(player_ids)
    random.shuffle(orden)
    for pid in orden:
        if not buscar(pid, set()):
            raise ValueError("No se pudo generar una asignacion valida de pruebas.")

    prueba_por_jugador = {}
    for idx, pid in asignada_a_prueba.items():
        prueba_por_jugador[pid] = pruebas_disponibles[idx]["texto"]
    return prueba_por_jugador


@dataclass
class Player:
    id: str
    name: str


class Room:
    def __init__(self, code: str, host_token: str):
        self.code = code
        self.host_token = host_token
        self.created_at = utc_now_iso()
        self.phase = "lobby"
        self.challenge_count = 3

        self.players: dict[str, Player] = {}
        self.claimed_by_player: dict[str, str] = {}
        self.session_to_player: dict[str, str] = {}
        self.submitted_challenges: dict[str, list[str]] = {}

        self.target_by_player: dict[str, str] = {}
        self.challenge_by_player: dict[str, str] = {}
        self.alive: set[str] = set()
        self.winner_id: str | None = None

        self.events: list[dict[str, Any]] = []
        self._event_seq = 0

    def add_event(self, typ: str, message: str, extra: dict[str, Any] | None = None) -> None:
        self._event_seq += 1
        payload = {"id": self._event_seq, "type": typ, "message": message, "timestamp": utc_now_iso()}
        if extra:
            payload.update(extra)
        self.events.append(payload)

    def player_name(self, player_id: str | None) -> str:
        if not player_id or player_id not in self.players:
            return ""
        return self.players[player_id].name

    def public_state(self) -> dict[str, Any]:
        players = []
        for pid, p in self.players.items():
            players.append(
                {
                    "id": pid,
                    "name": p.name,
                    "claimed": pid in self.claimed_by_player,
                    "alive": pid in self.alive if self.phase in {"active", "finished"} else True,
                    "submitted_challenges": pid in self.submitted_challenges,
                }
            )

        return {
            "code": self.code,
            "created_at": self.created_at,
            "phase": self.phase,
            "challenge_count": self.challenge_count,
            "players": players,
            "events": self.events[-30:],
            "winner_name": self.player_name(self.winner_id),
        }

    def personal_state(self, session_token: str) -> dict[str, Any]:
        player_id = self.session_to_player.get(session_token)
        if not player_id or player_id not in self.players:
            return {
                "claimed": False,
                "player_id": None,
                "player_name": None,
                "alive": None,
                "target_name": None,
                "challenge": None,
            }

        target_id = self.target_by_player.get(player_id)
        return {
            "claimed": True,
            "player_id": player_id,
            "player_name": self.players[player_id].name,
            "alive": player_id in self.alive,
            "target_name": self.player_name(target_id),
            "challenge": self.challenge_by_player.get(player_id),
        }


class RoomManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}
        self.ws_by_room: dict[str, list[tuple[WebSocket, str]]] = {}

    def _new_code(self) -> str:
        while True:
            code = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            if code not in self.rooms:
                return code

    def create_room(self) -> tuple[Room, str]:
        code = self._new_code()
        host_token = uuid.uuid4().hex
        room = Room(code=code, host_token=host_token)
        room.add_event("room_created", "Partida creada.")
        self.rooms[code] = room
        return room, host_token

    def get_room(self, code: str) -> Room:
        room = self.rooms.get(code.upper())
        if not room:
            raise HTTPException(status_code=404, detail="Sala no encontrada")
        return room

    def ensure_host(self, room: Room, host_token: str) -> None:
        if room.host_token != host_token:
            raise HTTPException(status_code=403, detail="Token de host invalido")

    async def broadcast(self, room: Room) -> None:
        sockets = self.ws_by_room.get(room.code, [])
        vivos = []
        for ws, session_token in sockets:
            try:
                await ws.send_json(
                    {
                        "type": "room_update",
                        "room": room.public_state(),
                        "me": room.personal_state(session_token),
                    }
                )
                vivos.append((ws, session_token))
            except Exception:
                continue
        self.ws_by_room[room.code] = vivos


manager = RoomManager()
app = FastAPI(title="Vampiro Multiplayer")


class CreateRoomResponse(BaseModel):
    room_code: str
    host_token: str
    join_url: str


class JoinRoomRequest(BaseModel):
    pass


class JoinRoomResponse(BaseModel):
    session_token: str
    room: dict[str, Any]


class SetupPlayersRequest(BaseModel):
    host_token: str
    names: list[str] = Field(default_factory=list)


class ClaimPlayerRequest(BaseModel):
    session_token: str
    player_id: str


class SetChallengeCountRequest(BaseModel):
    host_token: str
    challenge_count: int


class SubmitChallengesRequest(BaseModel):
    session_token: str
    challenges: list[str]


class StartGameRequest(BaseModel):
    host_token: str


class ConfirmKillRequest(BaseModel):
    session_token: str


@app.post("/api/rooms", response_model=CreateRoomResponse)
async def create_room(base_url: str = Query(default="http://localhost:8000")):
    room, host_token = manager.create_room()
    join_url = f"{base_url.rstrip('/')}/?room={room.code}"
    return CreateRoomResponse(room_code=room.code, host_token=host_token, join_url=join_url)


@app.post("/api/rooms/{room_code}/join", response_model=JoinRoomResponse)
async def join_room(room_code: str, _: JoinRoomRequest):
    room = manager.get_room(room_code)
    session_token = uuid.uuid4().hex
    return JoinRoomResponse(session_token=session_token, room=room.public_state())


@app.post("/api/rooms/{room_code}/players/setup")
async def setup_players(room_code: str, req: SetupPlayersRequest):
    room = manager.get_room(room_code)
    manager.ensure_host(room, req.host_token)

    if room.phase not in {"lobby", "collecting_challenges"}:
        raise HTTPException(status_code=400, detail="No se puede cambiar jugadores en esta fase")

    cleaned = []
    seen = set()
    for raw in req.names:
        name = raw.strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(name)

    if len(cleaned) < 2:
        raise HTTPException(status_code=400, detail="Necesitas al menos 2 jugadores")

    new_players: dict[str, Player] = {}
    for name in cleaned:
        pid = uuid.uuid4().hex[:8]
        new_players[pid] = Player(id=pid, name=name)

    room.players = new_players
    room.claimed_by_player = {}
    room.session_to_player = {}
    room.submitted_challenges = {}
    room.phase = "lobby"
    room.add_event("players_setup", f"Jugadores configurados: {len(cleaned)}")
    await manager.broadcast(room)
    return {"ok": True, "room": room.public_state()}


@app.post("/api/rooms/{room_code}/players/claim")
async def claim_player(room_code: str, req: ClaimPlayerRequest):
    room = manager.get_room(room_code)
    if room.phase == "finished":
        raise HTTPException(status_code=400, detail="La partida ya termino")
    if req.player_id not in room.players:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")

    ocupado_por = room.claimed_by_player.get(req.player_id)
    if ocupado_por and ocupado_por != req.session_token:
        raise HTTPException(status_code=400, detail="Ese jugador ya esta reclamado")

    previo = room.session_to_player.get(req.session_token)
    if previo and previo != req.player_id:
        room.claimed_by_player.pop(previo, None)

    room.session_to_player[req.session_token] = req.player_id
    room.claimed_by_player[req.player_id] = req.session_token
    room.add_event("player_claimed", f"{room.players[req.player_id].name} esta conectado")
    await manager.broadcast(room)
    return {"ok": True, "room": room.public_state(), "me": room.personal_state(req.session_token)}


@app.post("/api/rooms/{room_code}/settings/challenge-count")
async def set_challenge_count(room_code: str, req: SetChallengeCountRequest):
    room = manager.get_room(room_code)
    manager.ensure_host(room, req.host_token)
    if req.challenge_count < 1:
        raise HTTPException(status_code=400, detail="El numero de pruebas debe ser >= 1")

    room.challenge_count = req.challenge_count
    room.phase = "collecting_challenges"
    room.submitted_challenges = {}
    room.add_event("challenge_count", f"Cada jugador debe enviar {req.challenge_count} pruebas")
    await manager.broadcast(room)
    return {"ok": True, "room": room.public_state()}


@app.post("/api/rooms/{room_code}/challenges")
async def submit_challenges(room_code: str, req: SubmitChallengesRequest):
    room = manager.get_room(room_code)
    player_id = room.session_to_player.get(req.session_token)
    if not player_id:
        raise HTTPException(status_code=400, detail="Primero debes reclamar un jugador")
    if room.phase != "collecting_challenges":
        raise HTTPException(status_code=400, detail="Ahora no se estan recogiendo pruebas")

    challenges = [c.strip() for c in req.challenges if c.strip()]
    if len(challenges) < room.challenge_count:
        raise HTTPException(status_code=400, detail=f"Debes enviar al menos {room.challenge_count} pruebas")

    room.submitted_challenges[player_id] = challenges[: room.challenge_count]
    room.add_event("challenge_submitted", f"{room.players[player_id].name} envio sus pruebas")
    await manager.broadcast(room)
    return {"ok": True, "room": room.public_state(), "me": room.personal_state(req.session_token)}


@app.post("/api/rooms/{room_code}/start")
async def start_game(room_code: str, req: StartGameRequest):
    room = manager.get_room(room_code)
    manager.ensure_host(room, req.host_token)

    if len(room.players) < 2:
        raise HTTPException(status_code=400, detail="Necesitas al menos 2 jugadores")

    missing_claim = [pid for pid in room.players if pid not in room.claimed_by_player]
    if missing_claim:
        raise HTTPException(status_code=400, detail="Todos los jugadores deben estar conectados y reclamados")

    missing_challenges = [pid for pid in room.players if pid not in room.submitted_challenges]
    if missing_challenges:
        raise HTTPException(status_code=400, detail="Faltan jugadores por enviar pruebas")

    ids = list(room.players.keys())
    room.target_by_player = generar_ciclo_unico(ids)
    try:
        room.challenge_by_player = asignar_pruebas_validas(ids, room.submitted_challenges)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    room.alive = set(ids)
    room.winner_id = None
    room.phase = "active"
    room.add_event("game_started", "Partida iniciada")
    await manager.broadcast(room)
    return {"ok": True, "room": room.public_state()}


@app.post("/api/rooms/{room_code}/kill")
async def confirm_kill(room_code: str, req: ConfirmKillRequest):
    room = manager.get_room(room_code)
    if room.phase != "active":
        raise HTTPException(status_code=400, detail="La partida no esta activa")

    killer_id = room.session_to_player.get(req.session_token)
    if not killer_id:
        raise HTTPException(status_code=400, detail="Primero debes reclamar un jugador")
    if killer_id not in room.alive:
        raise HTTPException(status_code=400, detail="Tu jugador esta muerto")

    victim_id = room.target_by_player.get(killer_id)
    if not victim_id or victim_id not in room.alive:
        raise HTTPException(status_code=400, detail="No tienes objetivo valido")

    next_target = room.target_by_player.get(victim_id)
    if not next_target:
        raise HTTPException(status_code=400, detail="Estado de objetivos invalido")

    room.alive.remove(victim_id)
    room.target_by_player[killer_id] = next_target
    room.target_by_player.pop(victim_id, None)

    killer_name = room.player_name(killer_id)
    victim_name = room.player_name(victim_id)
    room.add_event("kill", f"{victim_name} ha sido eliminado", {"killer": killer_name, "victim": victim_name})

    if next_target == killer_id or len(room.alive) == 1:
        room.phase = "finished"
        room.winner_id = killer_id
        room.add_event("game_finished", f"Ganador: {killer_name}")

    await manager.broadcast(room)
    return {"ok": True, "room": room.public_state(), "me": room.personal_state(req.session_token)}


@app.get("/api/rooms/{room_code}/state")
async def room_state(room_code: str):
    room = manager.get_room(room_code)
    return {"room": room.public_state()}


@app.get("/api/rooms/{room_code}/me")
async def my_state(room_code: str, session_token: str):
    room = manager.get_room(room_code)
    return {"me": room.personal_state(session_token), "room": room.public_state()}


@app.websocket("/ws/{room_code}")
async def ws_room(websocket: WebSocket, room_code: str, session_token: str):
    room = manager.get_room(room_code)
    await websocket.accept()

    manager.ws_by_room.setdefault(room.code, []).append((websocket, session_token))
    await websocket.send_json({"type": "room_update", "room": room.public_state(), "me": room.personal_state(session_token)})

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        current = manager.ws_by_room.get(room.code, [])
        manager.ws_by_room[room.code] = [(ws, tok) for ws, tok in current if ws is not websocket]


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/healthz")
async def healthz():
    return {"ok": True}
