import unittest

from app.janggi_rules import JanggiRules
from third_party.pyjanggi.base.board import Board
from third_party.pyjanggi.base.camp import Camp
from third_party.pyjanggi.base.formation import Formation
from third_party.pyjanggi.base.location import Location
from third_party.pyjanggi.base.piece import Piece, PieceType


def empty_board():
    return Board(Formation.UNDECIDED, Formation.UNDECIDED, Camp.CHO)


def place(board, row, column, camp, piece_type):
    piece = Piece(piece_type)
    piece.camp = camp
    board.put(row, column, piece)


class JanggiRulesTest(unittest.TestCase):
    def test_horse_cannot_move_when_its_first_step_is_blocked(self):
        board = empty_board()
        place(board, 5, 4, Camp.CHO, PieceType.HORSE)
        place(board, 4, 4, Camp.CHO, PieceType.SOLDIER)
        rules = JanggiRules(board, Camp.CHO)

        destinations = rules.destinations(Location(5, 4))

        self.assertNotIn(Location(3, 3), destinations)
        self.assertNotIn(Location(3, 5), destinations)
        self.assertIn(Location(4, 2), destinations)

    def test_elephant_uses_one_straight_and_two_diagonal_steps(self):
        board = empty_board()
        place(board, 5, 4, Camp.CHO, PieceType.ELEPHANT)
        rules = JanggiRules(board, Camp.CHO)

        destinations = rules.destinations(Location(5, 4))

        self.assertIn(Location(3, 1), destinations)
        self.assertIn(Location(2, 2), destinations)
        self.assertIn(Location(8, 6), destinations)

    def test_cannon_requires_one_non_cannon_screen_and_cannot_capture_cannon(self):
        board = empty_board()
        place(board, 5, 0, Camp.CHO, PieceType.CANNON)
        place(board, 5, 2, Camp.HAN, PieceType.CANNON)
        place(board, 5, 4, Camp.HAN, PieceType.CHARIOT)
        rules = JanggiRules(board, Camp.CHO)

        self.assertNotIn(Location(5, 4), rules.destinations(Location(5, 0)))

        board.remove(5, 2)
        place(board, 5, 2, Camp.HAN, PieceType.SOLDIER)
        self.assertIn(Location(5, 4), rules.destinations(Location(5, 0)))

        board.remove(5, 4)
        place(board, 5, 4, Camp.HAN, PieceType.CANNON)
        self.assertNotIn(Location(5, 4), rules.destinations(Location(5, 0)))

    def test_chariot_can_follow_an_unblocked_palace_diagonal(self):
        board = empty_board()
        place(board, 0, 3, Camp.CHO, PieceType.CHARIOT)
        rules = JanggiRules(board, Camp.CHO)

        self.assertIn(Location(1, 4), rules.destinations(Location(0, 3)))
        self.assertIn(Location(2, 5), rules.destinations(Location(0, 3)))

    def test_soldier_cannot_retreat_and_can_use_forward_palace_diagonal(self):
        board = empty_board()
        place(board, 1, 4, Camp.CHO, PieceType.SOLDIER)
        rules = JanggiRules(board, Camp.CHO)

        destinations = rules.destinations(Location(1, 4))

        self.assertNotIn(Location(2, 4), destinations)
        self.assertIn(Location(0, 3), destinations)
        self.assertIn(Location(0, 5), destinations)

    def test_move_that_leaves_own_general_in_check_is_not_legal(self):
        board = empty_board()
        place(board, 9, 4, Camp.CHO, PieceType.GENERAL)
        place(board, 7, 4, Camp.CHO, PieceType.CHARIOT)
        place(board, 0, 4, Camp.HAN, PieceType.CHARIOT)
        rules = JanggiRules(board, Camp.CHO)

        actions = rules.legal_actions(Camp.CHO)

        self.assertNotIn((Location(7, 4), Location(7, 3)), actions)
        self.assertIn((Location(7, 4), Location(6, 4)), actions)


if __name__ == "__main__":
    unittest.main()
