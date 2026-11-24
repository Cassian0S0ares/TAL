import unittest
import chess
from tal.vision import describe_move, vision_facts, line_facts, evaluation


def position(moves):
    b = chess.Board()
    for san in moves.split():
        b.push_san(san)
    return b


def row(board, played, best, **extra):
    after = board.copy(); after.push_san(played)
    return dict(fen_before=board.fen(), fen_after=after.fen(),
                color='white' if board.turn else 'black', move_number=board.fullmove_number,
                played_san=played, best_san=best, **extra)


class TestVision(unittest.TestCase):
    def test_bishop_capture(self):
        b = position('e4 c6 Bc4 d5 exd5 cxd5 Nf3')
        v = vision_facts(row(b, 'Nf6', 'dxc4'))
        self.assertEqual(v['melhor']['captura'], 'bispo (brancas) em c4')
        self.assertIsNone(v['jogado']['captura'])
        self.assertEqual(b.piece_at(chess.C4), chess.Piece(chess.BISHOP, chess.WHITE))

    def test_roque_e_variante(self):
        b = position('e4 c6 Bc4 d5 exd5 cxd5 Nf3 Nf6 Ne5 Bf5 Bb5+ Nbd7 d4 Qa5+ Nc3 e6 Bg5')
        v = vision_facts(row(b, 'O-O-O', 'a6', reply_line_san=['Nxf7', 'Rg8', 'Nxd8']))
        self.assertEqual(v['jogado']['roque'], 'grande')
        self.assertEqual(v['direitos_roque_apos']['pretas'], [])
        self.assertEqual(v['linha_resposta'][2]['captura'], 'torre (pretas) em d8')

    def test_king_capture_and_pov(self):
        b = position('e4 c6 Bc4 d5 exd5 cxd5 Nf3 Nf6 Ne5 Bf5 Bb5+ Nbd7 d4 Qa5+ Nc3 e6 Bg5 O-O-O Nxf7 Rg8 Nxd8 Qxd8 Bxf6 Qxf6 Bxd7+')
        v = vision_facts(row(b, 'Kxd7', 'Kxd7', after_mover_pov={'cp': -234, 'mate': None}))
        self.assertEqual(v['jogado']['captura'], 'bispo (brancas) em d7')
        self.assertTrue(v['jogado']['responde_a_xeque'])
        self.assertEqual(v['depois']['favor'], 'brancas')
        self.assertEqual(v['direitos_roque_apos']['pretas'], [])

    def test_mate_and_zero(self):
        b = position('f3 e5 g4')
        v = vision_facts(row(b, 'Qh4#', 'Qh4#', after_mover_pov={'mate': 0, 'mate_winner':'pov'}))
        self.assertTrue(v['jogado']['da_mate'])
        self.assertEqual(v['depois'], {'mate_favor':'pretas', 'mate_em':0})
        self.assertEqual(evaluation({'mate':-2,'mate_winner':'opponent'}, chess.BLACK)['mate_favor'], 'brancas')

    def test_real_mate_allowed_and_final(self):
        b = position('e4 c6 Bc4 d5 exd5 cxd5 Nf3 Nf6 Ne5 Bf5 Bb5+ Nbd7 d4 Qa5+ Nc3 e6 Bg5 O-O-O Nxf7 Rg8 Nxd8 Qxd8 Bxf6 Qxf6 Bxd7+ Kxd7 O-O Qg6 b4 Be4 Nxe4 Qxe4 Rc1 Bxb4 c4 dxc4 Rxc4 Bd6 Qc1 Rc8 d5 Qxc4 Qg5 Qf4 Qxg7+ Kd8 Qg8+ Kc7 Qxh7+ Kb6 Rb1+')
        v = vision_facts(row(b, 'Ka6', 'Ka5', reply_line_san=['Qxb7+'],
                            after_mover_pov={'mate':-2,'mate_winner':'opponent'}))
        self.assertEqual(v['depois'], {'mate_favor':'brancas', 'mate_em':2})
        self.assertTrue(v['linha_resposta'][0]['da_xeque'])
        self.assertFalse(v['linha_resposta'][0]['da_mate'])
        for san in 'Ka6 dxe6 Rc1+ Rxc1'.split(): b.push_san(san)
        v = vision_facts(row(b, 'Qxc1#', 'Qxc1#'))
        self.assertEqual(v['jogado']['captura'], 'torre (brancas) em c1')
        self.assertTrue(v['jogado']['da_mate'])

    def test_en_passant(self):
        b = position('e4 a6 e5 d5')
        v, _ = describe_move(b, 'exd6')
        self.assertEqual(v['captura'], 'peão (pretas) em d5')

    def test_illegal_and_bad_report(self):
        b = chess.Board()
        with self.assertRaises(ValueError): line_facts(b, ['e4', 'e5', 'O-O'])
        with self.assertRaises(ValueError): vision_facts(dict(row(b, 'e4','e4'), color='black'))
        with self.assertRaises(ValueError): vision_facts(dict(row(b, 'e4','e4'), fen_after=b.fen()))

    def test_missing_fen(self):
        self.assertIn('indisponível', vision_facts({})['status'])
