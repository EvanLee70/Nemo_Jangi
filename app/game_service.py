"""Learning-game state and a lightweight five-level Janggi opponent."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from third_party.pyjanggi.base.camp import Camp
from third_party.pyjanggi.base.formation import Formation
from third_party.pyjanggi.base.location import Location
from third_party.pyjanggi.base.piece import PieceType
from third_party.pyjanggi.game.janggi_game import JanggiGame

from app.janggi_rules import JanggiRules

SIDE_NAMES = {Camp.CHO: "cho", Camp.HAN: "han"}
PIECE_NAMES = {
    PieceType.GENERAL: "장",
    PieceType.GUARD: "사",
    PieceType.HORSE: "마",
    PieceType.ELEPHANT: "상",
    PieceType.CHARIOT: "차",
    PieceType.CANNON: "포",
    PieceType.SOLDIER: "졸",
}


@dataclass(frozen=True)
class Candidate:
    origin: Location
    destination: Location
    score: float


class LearningGame:
    """A single learner-versus-computer game with move recommendations."""

    def __init__(self, level: int, human_side: str) -> None:
        if level not in range(1, 6):
            raise ValueError("난이도는 1부터 5까지 선택할 수 있습니다.")
        if human_side not in ("cho", "han"):
            raise ValueError("사용자 진영은 cho 또는 han이어야 합니다.")

        self.level = level
        self.human_side = Camp.CHO if human_side == "cho" else Camp.HAN
        self.computer_side = self.human_side.opponent
        self.game = JanggiGame(
            self.human_side,
            Formation.OUTER_ELEPHANT,
            Formation.OUTER_ELEPHANT,
        )
        self.history: list[dict[str, Any]] = []
        self.game_over = False
        if self.game.turn == self.computer_side:
            self._play_computer_move()

    def state(self) -> dict[str, Any]:
        rules = self._rules(self.game)
        actions = rules.legal_actions(self.game.turn) if not self.game_over else []
        legal_moves = self._serialise_actions(actions)
        recommendations = self._recommendations() if self.game.turn == self.human_side and not self.game_over else []
        return {
            "level": self.level,
            "humanSide": SIDE_NAMES[self.human_side],
            "turn": SIDE_NAMES[self.game.turn],
            "gameOver": self.game_over,
            "board": self._board_state(),
            "legalMoves": legal_moves,
            "recommendations": recommendations,
            "moveHistory": self.history,
            "scores": {"cho": self.game.cho_score, "han": self.game.han_score},
            "inCheck": rules.is_in_check(self.game.turn),
            "canPass": not self.game_over and not actions and not rules.is_in_check(self.game.turn),
            "ruleMode": "친선대국: 빅장·반복수 허용",
        }

    def play_human_move(self, origin: list[int], destination: list[int]) -> dict[str, Any]:
        if self.game_over or self.game.turn != self.human_side:
            raise ValueError("현재는 둘 수 없는 차례입니다.")
        source = self._location(origin)
        target = self._location(destination)
        if (source, target) not in self._rules(self.game).legal_actions(self.game.turn):
            raise ValueError("규칙에 맞지 않는 수입니다.")
        self._play(source, target, self.human_side)
        if not self.game_over:
            self._play_computer_move()
        return self.state()

    def pass_turn(self) -> dict[str, Any]:
        rules = self._rules(self.game)
        if self.game_over or self.game.turn != self.human_side:
            raise ValueError("현재는 한 수 쉴 수 없는 차례입니다.")
        if rules.legal_actions(self.game.turn) or rules.is_in_check(self.game.turn):
            raise ValueError("둘 수 있는 수가 있거나 장군 상태에서는 한 수 쉴 수 없습니다.")
        self.history.append({"side": SIDE_NAMES[self.human_side], "pass": True})
        self.game.turn = self.game.turn.opponent
        self._play_computer_move()
        return self.state()

    def _location(self, raw: list[int]) -> Location:
        if len(raw) != 2 or not all(isinstance(value, int) for value in raw):
            raise ValueError("좌표는 [행, 열] 형식이어야 합니다.")
        return Location(raw[0], raw[1])

    def _play_computer_move(self) -> None:
        actions = self._rules(self.game).legal_actions(self.game.turn)
        if not actions:
            if self._rules(self.game).is_in_check(self.game.turn):
                self.game_over = True
            return
        choice = self._choose_computer_move(actions)
        self._play(choice.origin, choice.destination, self.computer_side)

    def _play(self, origin: Location, destination: Location, side: Camp) -> None:
        captured, game_over = self.game.make_action(origin, destination)
        self.history.append(
            {
                "side": SIDE_NAMES[side],
                "from": list(origin),
                "to": list(destination),
                "captured": captured,
            }
        )
        self.game_over = game_over
        if not self.game_over:
            next_rules = self._rules(self.game)
            if not next_rules.legal_actions(self.game.turn) and next_rules.is_in_check(self.game.turn):
                self.game_over = True

    def _choose_computer_move(self, actions: list[tuple[Location, Location]]) -> Candidate:
        ranked = self._rank_actions(self.game, actions, self.computer_side)
        if self.level == 1:
            return ranked[len(self.history) % len(ranked)]
        if self.level == 2:
            return ranked[0]
        depth = 1 if self.level == 3 else 2 if self.level == 4 else 3
        width = 8 if self.level == 3 else 12
        scored = [Candidate(item.origin, item.destination, self._search_after(item, depth, width)) for item in ranked[:width]]
        return max(scored, key=lambda item: item.score)

    def _search_after(self, candidate: Candidate, depth: int, width: int) -> float:
        simulated = deepcopy(self.game)
        simulated.make_action(candidate.origin, candidate.destination)
        return self._minimax(simulated, depth - 1, width)

    def _minimax(self, game: JanggiGame, depth: int, width: int) -> float:
        if depth <= 0:
            return self._evaluate(game)
        actions = self._rules(game).legal_actions(game.turn)
        if not actions:
            return self._evaluate(game)
        side = game.turn
        ranked = self._rank_actions(game, actions, side)[:width]
        values = []
        for action in ranked:
            next_game = deepcopy(game)
            _, game_over = next_game.make_action(action.origin, action.destination)
            value = self._evaluate(next_game) if game_over else self._minimax(next_game, depth - 1, width)
            values.append(value)
        return max(values) if side == self.computer_side else min(values)

    def _rank_actions(self, game: JanggiGame, actions: list[tuple[Location, Location]], side: Camp) -> list[Candidate]:
        ranked = []
        for origin, destination in actions:
            target = game.board.get(destination.row, destination.col)
            capture_score = target.value * 10 if target else 0
            center_score = 1.2 if 3 <= destination.col <= 5 else 0
            forward_score = 0.4 * ((origin.row - destination.row) * (1 if side == self.human_side else -1))
            ranked.append(Candidate(origin, destination, capture_score + center_score + forward_score))
        return sorted(ranked, key=lambda item: item.score, reverse=True)

    def _evaluate(self, game: JanggiGame) -> float:
        material = game.cho_score - game.han_score
        return material if self.computer_side == Camp.CHO else -material

    def _recommendations(self) -> list[dict[str, Any]]:
        ranked = self._rank_actions(self.game, self._rules(self.game).legal_actions(self.human_side), self.human_side)
        return [
            {
                "from": list(candidate.origin),
                "to": list(candidate.destination),
                "notation": self._notation(candidate.origin, candidate.destination),
                "reason": self._recommendation_reason(candidate),
            }
            for candidate in ranked[:5]
        ]

    def _recommendation_reason(self, candidate: Candidate) -> str:
        target = self.game.board.get(candidate.destination.row, candidate.destination.col)
        if target:
            return f"{PIECE_NAMES[target.piece_type]}을(를) 잡아 기물 우세를 만듭니다."
        if 3 <= candidate.destination.col <= 5:
            return "중앙을 점유해 다음 수의 선택지를 넓힙니다."
        return "기물을 전개해 공격과 수비의 연결을 준비합니다."

    def _notation(self, origin: Location, destination: Location) -> str:
        piece = self.game.board.get(origin.row, origin.col)
        return f"{PIECE_NAMES[piece.piece_type]} {origin.row + 1}{origin.col + 1} → {destination.row + 1}{destination.col + 1}"

    def _board_state(self) -> list[list[dict[str, str] | None]]:
        board = []
        for row in range(10):
            current_row = []
            for column in range(9):
                piece = self.game.board.get(row, column)
                current_row.append(
                    None
                    if piece is None
                    else {"side": SIDE_NAMES[piece.camp], "type": PIECE_NAMES[piece.piece_type]}
                )
            board.append(current_row)
        return board

    @staticmethod
    def _serialise_actions(actions: list[tuple[Location, Location]]) -> list[dict[str, list[int]]]:
        return [{"from": list(origin), "to": list(destination)} for origin, destination in actions]

    @staticmethod
    def _rules(game: JanggiGame) -> JanggiRules:
        return JanggiRules(game.board, game.board.bottom_camp)
