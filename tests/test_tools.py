import unittest
from unittest.mock import Mock
import chess
import chess.engine
from tal.tools import ChessTools

ROW = {'fen_before': 'rnbqkbnr/pp2pppp/8/3p4/2B5/5N2/PPPP1PPP/RNBQK2R b KQkq - 1 4',
       'move_number': 4, 'color': 'black', 'played_san': 'Nf6'}


class TestTools(unittest.TestCase):
    def setUp(self):
        self.engine = Mock()
        self.engine.analyse.side_effect = lambda board, *a, **kw: {
            'score': chess.engine.PovScore(chess.engine.Cp(36), chess.BLACK),
            'pv': [next(iter(board.legal_moves))], 'depth': 14}
        self.tools = ChessTools(ROW, engine_factory=lambda: self.engine)
        self.addCleanup(self.tools.__exit__)

    def test_board_and_square(self):
        self.assertEqual(self.tools.run('inspect_square', {'square': 'c4'})['peca'], 'bispo (brancas)')
        self.assertEqual(self.tools.run('get_board', {})['fen'], ROW['fen_before'])
        self.assertIn('dxc4', self.tools.run('get_legal_moves', {})['lances'])
        self.assertIn('Bb5+', self.tools.run('get_legal_moves', {'position': 'after'})['lances'])

    def test_capture_simulation_isolated(self):
        r = self.tools.run('simulate_move', {'move': 'dxc4'})
        self.assertIn('bispo (brancas)', r['movimento']['captura'])
        self.assertEqual(self.tools.run('inspect_square', {'square': 'c4', 'line': ['dxc4']})['peca'], 'peão (pretas)')
        self.assertEqual(self.tools.run('inspect_square', {'square': 'c4'})['peca'], 'bispo (brancas)')
        self.assertEqual(self.tools.run('get_attackers', {'square': 'c4'})['ataques_geometricos']['pretas'][0]['casa'], 'd5')

    def test_sequence_and_invalid(self):
        self.assertTrue(self.tools.run('validate_sequence', {'moves': ['dxc4', 'Na3']})['legal'])
        for name, args in [('simulate_move', {'move': 'Qh5'}), ('inspect_square', {'square': 'z9'}),
                           ('get_board', {'position': 'bad'}), ('get_board', {'line': ['e4']*9}),
                           ('get_board', {'unexpected': True}), ('shell', {})]:
            with self.subTest(name=name, args=args), self.assertRaises(ValueError):
                self.tools.run(name, args)

    def test_engine_pov_and_comparison(self):
        self.assertEqual(self.tools.run('analyze_position', {'position': 'after'})['avaliacao']['favor'], 'pretas')
        res = self.tools.run('compare_moves', {'move_a': 'Nf6', 'move_b': 'dxc4'})
        self.assertEqual(res['alternativa_b']['resultado']['avaliacao']['cp_de_quem_jogou'], 36)
        self.assertEqual(self.engine.analyse.call_count, 3)

    def test_terminal_mate(self):
        row = {'fen_before': '7k/5Q2/6K1/8/8/8/8/8 w - - 0 1', 'move_number': 1, 'color': 'white', 'played_san': 'Qf8#'}
        factory = Mock(side_effect=AssertionError('Terminal não deve iniciar engine'))
        with ChessTools(row, engine_factory=factory) as tools:
            r = tools.run('analyze_position', {'position': 'after'})
            self.assertTrue(r['terminal'])
            self.assertEqual(r['avaliacao'], {'mate_favor': 'brancas', 'mate_em': 0})
        factory.assert_not_called()
