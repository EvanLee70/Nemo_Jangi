"""Vercel serverless API for the Janggi learning application."""

from __future__ import annotations

import json
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.game_service import LearningGame

GAMES: dict[str, LearningGame] = {}


class handler(BaseHTTPRequestHandler):
    """Serve a browser session from a Vercel Python function instance."""

    def do_GET(self) -> None:
        if self._endpoint() != "/state":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "요청한 기능을 찾을 수 없습니다."})
            return
        session_id, game, created = self._game()
        self._send_json(HTTPStatus.OK, game.state(), session_id if created else None)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            session_id, game, created = self._game()
            endpoint = self._endpoint()
            if endpoint == "/new":
                game = LearningGame(level=payload.get("level", 1), human_side=payload.get("humanSide", "cho"))
                GAMES[session_id] = game
                body = game.state()
            elif endpoint == "/move":
                body = game.play_human_move(payload["from"], payload["to"])
            elif endpoint == "/pass":
                body = game.pass_turn()
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "요청한 기능을 찾을 수 없습니다."}, session_id if created else None)
                return
            self._send_json(HTTPStatus.OK, body, session_id if created else None)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def _game(self) -> tuple[str, LearningGame, bool]:
        session_id = self._cookie_value("nemo_janggi_session")
        if session_id and session_id in GAMES:
            return session_id, GAMES[session_id], False
        session_id = secrets.token_urlsafe(24)
        game = LearningGame(level=1, human_side="cho")
        GAMES[session_id] = game
        return session_id, game, True

    def _cookie_value(self, name: str) -> str | None:
        for value in self.headers.get("Cookie", "").split(";"):
            key, separator, cookie_value = value.strip().partition("=")
            if separator and key == name:
                return cookie_value
        return None

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _endpoint(self) -> str:
        route = parse_qs(urlparse(self.path).query).get("route", [""])[0]
        return f"/{route.strip('/')}"

    def _send_json(self, status: HTTPStatus, body: dict[str, Any], session_id: str | None = None) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        if session_id:
            self.send_header("Set-Cookie", f"nemo_janggi_session={session_id}; Path=/; HttpOnly; SameSite=Lax")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, _format: str, *_args: object) -> None:
        return
