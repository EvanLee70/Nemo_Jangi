"""Dependency-free local web server for the Janggi learning program."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.game_service import LearningGame

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "public"


class LearningRequestHandler(BaseHTTPRequestHandler):
    game = LearningGame(level=1, human_side="cho")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            self._send_json(HTTPStatus.OK, self.game.state())
            return
        self._serve_static("index.html" if path == "/" else path.lstrip("/"))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/new":
                self.game = LearningGame(level=payload.get("level", 1), human_side=payload.get("humanSide", "cho"))
                self._send_json(HTTPStatus.OK, self.game.state())
            elif path == "/api/move":
                self._send_json(HTTPStatus.OK, self.game.play_human_move(payload["from"], payload["to"]))
            elif path == "/api/pass":
                self._send_json(HTTPStatus.OK, self.game.pass_turn())
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "요청한 기능을 찾을 수 없습니다."})
        except (KeyError, TypeError, ValueError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _serve_static(self, name: str) -> None:
        target = (STATIC_DIR / name).resolve()
        if STATIC_DIR not in target.parents or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, body: dict[str, Any]) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def create_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), LearningRequestHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="장기 배움터")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(f"장기 배움터: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
