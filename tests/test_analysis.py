import unittest
from pathlib import Path
try:
    import chess
    import chess.engine
    from tal.analysis import parse_pgn, analyze_game, category
except ImportError:
    chess = None

@unittest.skipIf(chess is None, 'Instale requirements.txt para testar o motor')
class TestAnalysis(unittest.TestCase):
    def test_category(self):
        self.assertEqual(category(250, False), 'erro_grave')
        self.assertEqual(category(0, True), 'melhor')
        self.assertEqual(category(None, False, None, -1), 'permite_mate')

    def test_perspective_and_terminal(self):
        class Engine:
            id = {'name':'Fake UCI'}
            calls = 0
            def analyse(self, board, limit, **kwargs):
                self.calls += 1
                # White POV evaluations by ply; synthetic test, not actual chess values.
                s = [20, -80, -70, -300][board.ply()]
                return {'score': chess.engine.PovScore(chess.engine.Cp(s), chess.WHITE),
                        'pv': [next(iter(board.legal_moves))], 'depth': 6}
        game = parse_pgn((Path(__file__).resolve().parents[1] / 'examples/demo.pgn').read_text())
        e = Engine()
        result = analyze_game(game, e, 6, 'demoblack')
        self.assertEqual(e.calls, 4)
        self.assertEqual(len(result['moves']), 4)
        self.assertEqual(result['moves'][0]['centipawn_loss'], 100)
        self.assertEqual(result['moves'][1]['centipawn_loss'], 10)
        self.assertEqual(result['moves'][-1]['after_mover_pov']['mate_winner'], 'pov')
        self.assertEqual(result['summary']['plies'], 2)
        self.assertEqual(result['player_color'], 'black')
