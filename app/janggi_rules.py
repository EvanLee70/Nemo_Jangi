"""Official-style Janggi movement and check validation for the learning app.

Rules implemented from Korean Janggi Association guidance: piece movement,
palace diagonals, cannon restrictions, blocked horse/elephant paths, soldier
direction, and self-check prevention.
"""

from __future__ import annotations

from typing import Iterable

from third_party.pyjanggi.base.board import Board
from third_party.pyjanggi.base.camp import Camp
from third_party.pyjanggi.base.location import Location
from third_party.pyjanggi.base.piece import PieceType

Coord = tuple[int, int]
Action = tuple[Location, Location]

PALACE_PATHS = (
    ((0, 3), (1, 4), (2, 5)),
    ((0, 5), (1, 4), (2, 3)),
    ((7, 3), (8, 4), (9, 5)),
    ((7, 5), (8, 4), (9, 3)),
)
PIECE_VALUES = {
    PieceType.GUARD: 3,
    PieceType.HORSE: 5,
    PieceType.ELEPHANT: 3,
    PieceType.CHARIOT: 13,
    PieceType.CANNON: 7,
    PieceType.SOLDIER: 2,
    PieceType.GENERAL: 0,
}


class JanggiRules:
    """Generate legal actions for a Board without relying on UI concerns."""

    def __init__(self, board: Board, bottom_camp: Camp) -> None:
        self.board = board
        self.bottom_camp = bottom_camp

    def destinations(self, origin: Location) -> list[Location]:
        """Return movement-rule destinations; use legal_actions for self-check filtering."""
        piece = self.board.get(origin.row, origin.col)
        if piece is None:
            return []
        return [Location(row, col) for row, col in self._pseudo_destinations((origin.row, origin.col))]

    def legal_actions(self, side: Camp) -> list[Action]:
        actions: list[Action] = []
        for origin in self.board.get_piece_locations_for_camp(side):
            for destination in self.destinations(origin):
                if not self._leaves_general_in_check(origin, destination, side):
                    actions.append((origin, destination))
        return actions

    def is_in_check(self, side: Camp) -> bool:
        general = self._general_location(side)
        if general is None:
            return True
        enemy = side.opponent
        for origin in self.board.get_piece_locations_for_camp(enemy):
            if (general.row, general.col) in self._pseudo_destinations((origin.row, origin.col)):
                return True
        return False

    def _leaves_general_in_check(self, origin: Location, destination: Location, side: Camp) -> bool:
        simulated = self.board.copy()
        simulated.move(origin, destination)
        return JanggiRules(simulated, self.bottom_camp).is_in_check(side)

    def _general_location(self, side: Camp) -> Location | None:
        for location in self.board.get_piece_locations_for_camp(side):
            if self.board.get(location.row, location.col).piece_type == PieceType.GENERAL:
                return location
        return None

    def _pseudo_destinations(self, origin: Coord) -> list[Coord]:
        piece = self.board.get(*origin)
        if piece.piece_type in (PieceType.GENERAL, PieceType.GUARD):
            return self._palace_steps(origin, piece.camp)
        if piece.piece_type == PieceType.CHARIOT:
            return self._chariot_moves(origin)
        if piece.piece_type == PieceType.CANNON:
            return self._cannon_moves(origin)
        if piece.piece_type == PieceType.HORSE:
            return self._jump_moves(origin, ((-1, 0, -2, -1), (-1, 0, -2, 1), (1, 0, 2, -1), (1, 0, 2, 1), (0, -1, -1, -2), (0, -1, 1, -2), (0, 1, -1, 2), (0, 1, 1, 2)))
        if piece.piece_type == PieceType.ELEPHANT:
            return self._elephant_moves(origin)
        return self._soldier_moves(origin, piece.camp)

    def _palace_steps(self, origin: Coord, camp: Camp) -> list[Coord]:
        palace = self._palace_for(camp)
        if origin not in palace:
            return []
        rows, columns = origin
        destinations = []
        for row, column in ((rows - 1, columns), (rows + 1, columns), (rows, columns - 1), (rows, columns + 1)):
            if (row, column) in palace:
                destinations.append((row, column))
        for path in PALACE_PATHS:
            if origin in path:
                index = path.index(origin)
                for neighbor in (index - 1, index + 1):
                    if 0 <= neighbor < len(path):
                        destinations.append(path[neighbor])
        return self._without_allies(destinations, camp)

    def _chariot_moves(self, origin: Coord) -> list[Coord]:
        camp = self.board.get(*origin).camp
        paths = self._cardinal_rays(origin) + self._palace_rays(origin)
        destinations = []
        for path in paths:
            for destination in path:
                target = self.board.get(*destination)
                if target is None:
                    destinations.append(destination)
                    continue
                if target.camp != camp:
                    destinations.append(destination)
                break
        return destinations

    def _cannon_moves(self, origin: Coord) -> list[Coord]:
        camp = self.board.get(*origin).camp
        destinations = []
        for path in self._cardinal_rays(origin) + self._palace_rays(origin):
            jumped = False
            for destination in path:
                target = self.board.get(*destination)
                if target is None:
                    if jumped:
                        destinations.append(destination)
                    continue
                if target.piece_type == PieceType.CANNON:
                    break
                if not jumped:
                    jumped = True
                    continue
                if target.camp != camp:
                    destinations.append(destination)
                break
        return destinations

    def _jump_moves(self, origin: Coord, patterns: Iterable[tuple[int, int, int, int]]) -> list[Coord]:
        camp = self.board.get(*origin).camp
        row, column = origin
        destinations = []
        for first_row, first_column, delta_row, delta_column in patterns:
            blocker = (row + first_row, column + first_column)
            destination = (row + delta_row, column + delta_column)
            if self._inside(destination) and self.board.get(*blocker) is None:
                destinations.extend(self._without_allies([destination], camp))
        return destinations

    def _elephant_moves(self, origin: Coord) -> list[Coord]:
        camp = self.board.get(*origin).camp
        row, column = origin
        moves = []
        for first_row, first_column, diagonal_row, diagonal_column, end_row, end_column in (
            (-1, 0, -1, -1, -1, -1), (-1, 0, -1, 1, -1, 1),
            (1, 0, 1, -1, 1, -1), (1, 0, 1, 1, 1, 1),
            (0, -1, -1, -1, -1, -1), (0, -1, 1, -1, 1, -1),
            (0, 1, -1, 1, -1, 1), (0, 1, 1, 1, 1, 1),
        ):
            first = (row + first_row, column + first_column)
            second = (first[0] + diagonal_row, first[1] + diagonal_column)
            destination = (second[0] + end_row, second[1] + end_column)
            if self._inside(destination) and self.board.get(*first) is None and self.board.get(*second) is None:
                moves.extend(self._without_allies([destination], camp))
        return moves

    def _soldier_moves(self, origin: Coord, camp: Camp) -> list[Coord]:
        row, column = origin
        forward = -1 if camp == self.bottom_camp else 1
        destinations = [(row + forward, column), (row, column - 1), (row, column + 1)]
        for path in PALACE_PATHS:
            if origin in path:
                index = path.index(origin)
                for neighbor in (index - 1, index + 1):
                    if 0 <= neighbor < len(path):
                        target = path[neighbor]
                        if target[0] - row == forward:
                            destinations.append(target)
        return self._without_allies([destination for destination in destinations if self._inside(destination)], camp)

    def _cardinal_rays(self, origin: Coord) -> list[list[Coord]]:
        row, column = origin
        paths = []
        for delta_row, delta_column in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            path = []
            next_row, next_column = row + delta_row, column + delta_column
            while self._inside((next_row, next_column)):
                path.append((next_row, next_column))
                next_row += delta_row
                next_column += delta_column
            paths.append(path)
        return paths

    @staticmethod
    def _palace_rays(origin: Coord) -> list[list[Coord]]:
        paths = []
        for palace_path in PALACE_PATHS:
            if origin not in palace_path:
                continue
            index = palace_path.index(origin)
            paths.append(list(reversed(palace_path[:index])))
            paths.append(list(palace_path[index + 1:]))
        return [path for path in paths if path]

    def _palace_for(self, camp: Camp) -> set[Coord]:
        rows = range(7, 10) if camp == self.bottom_camp else range(0, 3)
        return {(row, column) for row in rows for column in range(3, 6)}

    def _without_allies(self, destinations: Iterable[Coord], camp: Camp) -> list[Coord]:
        return [destination for destination in destinations if self.board.get(*destination) is None or self.board.get(*destination).camp != camp]

    @staticmethod
    def _inside(location: Coord) -> bool:
        return 0 <= location[0] <= 9 and 0 <= location[1] <= 8
