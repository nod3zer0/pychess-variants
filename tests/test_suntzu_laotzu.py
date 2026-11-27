from __future__ import annotations

import unittest

import test_logger
from fairy.fairy_board import FairyBoard, get_fog_fen
from test_embassy_castling_pgn import make_game

test_logger.init_test_logger()


class DoubleFischerRandomStartTestCase(unittest.TestCase):
    def test_white_and_black_back_ranks_are_drawn_independently(self):
        # Mirrored chess960 would always produce matching letters at a given
        # file for both colors; the double-random setup should not, at least
        # over enough draws to make a coincidental match implausible.
        mismatched = False
        for _ in range(50):
            for variant in ("suntzu", "laotzu"):
                fen = FairyBoard.start_fen(variant, True)
                rows = fen.split()[0].split("/")
                black_rank, white_rank = rows[0], rows[-1]
                if black_rank != white_rank.lower():
                    mismatched = True
        self.assertTrue(mismatched)

    def test_start_position_is_legal_and_has_crazyhouse_hand(self):
        for variant in ("suntzu", "laotzu"):
            with self.subTest(variant=variant):
                fen = FairyBoard.start_fen(variant, True)
                self.assertIn("[]", fen)
                board = FairyBoard(variant, fen, True)
                self.assertTrue(board.has_legal_move())


class VisibleDropSquaresTestCase(unittest.TestCase):
    def test_drops_limited_to_squares_reachable_by_non_drop_moves(self):
        # White has a pawn in hand but has only moved pawns on the queenside,
        # so only ranks 3-4 on files a-d are visible through ordinary moves.
        fen = "nrqbbnkr/pppppppp/8/8/8/8/PPPPPPPP/QRBNKBRN[P] w BGbh - 0 1"
        board = FairyBoard("laotzu", fen, True)
        visible = board.visible_drop_squares()
        self.assertIn("a3", visible)
        self.assertIn("d4", visible)
        self.assertNotIn("a5", visible)
        self.assertNotIn("h6", visible)

        drop_moves = [move for move in board.legal_moves() if "@" in move]
        allowed = [move for move in drop_moves if move[2:4] in visible]
        blocked = [move for move in drop_moves if move[2:4] not in visible]
        self.assertTrue(allowed)
        self.assertTrue(blocked)

    def test_suntzu_allows_drops_beyond_visible_drop_squares(self):
        # Sun Tzu allows dropping anywhere, unlike Lao Tzu: the engine's own
        # (unfiltered) legal move list covers squares visible_drop_squares()
        # would not include, since that helper only reflects non-drop moves.
        fen = "nrqbbnkr/pppppppp/8/8/8/8/PPPPPPPP/QRBNKBRN[P] w BGbh - 0 1"
        board = FairyBoard("suntzu", fen, True)
        drop_destinations = {move[2:4] for move in board.legal_moves() if "@" in move}
        self.assertFalse(drop_destinations <= board.visible_drop_squares())


class FogViewMatchesDropVisibilityTestCase(unittest.TestCase):
    def test_laotzu_fog_does_not_reveal_drop_only_terrain(self):
        # Sun Tzu's fog view reveals empty squares a held piece could be
        # dropped on (fog_area() counts drop destinations as visible); Lao
        # Tzu must not, since those squares aren't actually legal drop
        # targets there. Otherwise the fog view would show "visible terrain"
        # the player isn't allowed to act on.
        fen = "nrqbbnkr/pppppppp/8/8/8/8/PPPPPPPP/QRBNKBRN[P] w BGbh - 0 1"

        suntzu_fog = get_fog_fen(fen, 0, "suntzu", True, False)
        laotzu_fog = get_fog_fen(fen, 0, "laotzu", True, True)

        suntzu_ranks = suntzu_fog.split()[0].split("/")
        laotzu_ranks = laotzu_fog.split()[0].split("/")

        # Rank 5 (index 3 from the top) is drop-only terrain: visible to Sun
        # Tzu (holding a pawn reveals it as an empty drop target) but still
        # fogged for Lao Tzu.
        self.assertEqual(suntzu_ranks[3], "8")
        self.assertEqual(laotzu_ranks[3], "********")

        # Both players' own back rank must remain visible either way.
        self.assertEqual(suntzu_ranks[-1], laotzu_ranks[-1])
        self.assertNotIn("*", suntzu_ranks[-1])
        self.assertNotIn("*", laotzu_ranks[-1])

    def test_laotzu_fog_preserves_holdings_and_turn(self):
        fen = "nrqbbnkr/pppppppp/8/8/8/8/PPPPPPPP/QRBNKBRN[P] w BGbh - 0 1"
        fog = get_fog_fen(fen, 0, "laotzu", True, True)
        fields = fog.split()
        self.assertTrue(fields[0].endswith("[P]"))
        self.assertEqual(fields[1], "w")


class GameChess960ForcingTestCase(unittest.TestCase):
    def test_suntzu_and_laotzu_games_are_always_chess960(self):
        for variant, expected_server_name, expected_drops_require_visibility in (
            ("suntzu", "suntzu960", False),
            ("laotzu", "laotzu960", True),
        ):
            with self.subTest(variant=variant):
                game = make_game(f"{variant}-game", variant, "")
                self.assertTrue(game.chess960)
                self.assertEqual(game.server_variant.server_name, expected_server_name)
                self.assertTrue(game.server_variant.hidden_info)
                self.assertEqual(
                    game.server_variant.drops_require_visibility,
                    expected_drops_require_visibility,
                )
                self.assertTrue(game.fow)

    def test_pgn_does_not_crash_for_always_chess960_variants(self):
        # Regression test: self.chess960 is always True for these variants
        # (there's no plain, non-960 form a client can actually reach), so
        # `pgn` always takes the VARIANT_960_TO_PGN branch. A missing entry
        # there raised KeyError on resign/board-view/invite-page requests.
        for variant, expected_tag in (("suntzu", "Sun Tzu"), ("laotzu", "Lao Tzu")):
            with self.subTest(variant=variant):
                game = make_game(f"{variant}-pgn", variant, "")
                game.steps[0]["fen"] = game.board.initial_fen
                self.assertIn(f'[Variant "{expected_tag}"]', game.pgn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
