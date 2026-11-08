import unittest
from http.client import HTTPConnection
from threading import Thread

from app.game_service import LearningGame
from app.server import create_server


class LearningGameTest(unittest.TestCase):
    def test_new_game_returns_five_legal_recommendations_for_the_human_turn(self):
        game = LearningGame(level=3, human_side="cho")

        state = game.state()

        self.assertEqual(state["turn"], "cho")
        self.assertEqual(len(state["recommendations"]), 5)
        legal_moves = {(tuple(move["from"]), tuple(move["to"])) for move in state["legalMoves"]}
        for recommendation in state["recommendations"]:
            self.assertIn((tuple(recommendation["from"]), tuple(recommendation["to"])), legal_moves)
            self.assertTrue(recommendation["reason"])

    def test_human_move_is_followed_by_a_legal_computer_move(self):
        game = LearningGame(level=2, human_side="cho")
        first_move = game.state()["recommendations"][0]

        state = game.play_human_move(first_move["from"], first_move["to"])

        self.assertEqual(len(state["moveHistory"]), 2)
        self.assertEqual(state["moveHistory"][0]["side"], "cho")
        self.assertEqual(state["moveHistory"][1]["side"], "han")
        self.assertEqual(state["turn"], "cho")
        self.assertEqual(len(state["recommendations"]), 5)

    def test_level_must_be_between_one_and_five(self):
        for invalid_level in (0, 6):
            with self.assertRaises(ValueError):
                LearningGame(level=invalid_level, human_side="cho")

    def test_server_serves_the_learning_screen(self):
        server = create_server("127.0.0.1", 0)
        thread = Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(self._stop_server, server, thread)

        connection = HTTPConnection("127.0.0.1", server.server_port)
        connection.request("GET", "/")
        response = connection.getresponse()
        page = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn("장기 배움터", page)

    def test_learning_screen_includes_piece_art_and_move_guides(self):
        server = create_server("127.0.0.1", 0)
        thread = Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(self._stop_server, server, thread)

        connection = HTTPConnection("127.0.0.1", server.server_port)
        connection.request("GET", "/app.js")
        script = connection.getresponse().read().decode("utf-8")
        connection.request("GET", "/style.css")
        stylesheet = connection.getresponse().read().decode("utf-8")

        self.assertIn("board-lines", script)
        self.assertIn("move-guides", script)
        self.assertIn("computer-move-guide", script)
        self.assertIn(".piece-image", stylesheet)

    def test_server_serves_the_attributed_janggi_piece_asset(self):
        server = create_server("127.0.0.1", 0)
        thread = Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(self._stop_server, server, thread)

        connection = HTTPConnection("127.0.0.1", server.server_port)
        connection.request("GET", "/pieces/kakao-blue-king.svg")
        response = connection.getresponse()

        self.assertEqual(response.status, 200)
        self.assertIn("image/svg+xml", response.getheader("Content-Type"))

    def test_learning_screen_discloses_association_rule_sources(self):
        server = create_server("127.0.0.1", 0)
        thread = Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(self._stop_server, server, thread)

        connection = HTTPConnection("127.0.0.1", server.server_port)
        connection.request("GET", "/")
        page = connection.getresponse().read().decode("utf-8")

        self.assertIn("대한장기협회 기준", page)
        self.assertIn("business3.php", page)
        self.assertIn("business5.php", page)
        self.assertIn("business6.php", page)
        self.assertIn("business7.php", page)

    @staticmethod
    def _stop_server(server, thread):
        server.shutdown()
        thread.join()
        server.server_close()
