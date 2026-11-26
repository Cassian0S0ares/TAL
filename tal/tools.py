"""Bounded, read-only tools for a selected position in a completed game."""
import chess
import chess.engine
from .analysis import open_engine, evaluate, pv_san, score_data
from .vision import board_from_fen, describe_move, piece_name, side, evaluation

from .tool_specs import MAX_LINE, SCHEMAS


def parse_line(board, line):
    if not isinstance(line, list) or len(line) > MAX_LINE or any(not isinstance(s, str) or not 1 <= len(s) <= 16 for s in line):
        raise ValueError('Sequência SAN inválida; máximo de 8 lances.')
    facts = []
    for san in line:
        fact, board = describe_move(board, san)
        facts.append(fact)
    return board, facts


def state(board):
    return {'fen': board.fen(), 'vez': side(board.turn), 'xeque': board.is_check(),
            'mate': board.is_checkmate(), 'terminal': board.is_game_over(),
            'direitos_roque': board.castling_xfen()}


class ChessTools:
    def __init__(self, row, depth=14, engine_factory=open_engine):
        if not 1 <= depth <= 18:
            raise ValueError('Profundidade deve estar entre 1 e 18.')
        self.before = board_from_fen(row['fen_before'])
        self.pov = self.before.turn
        if row.get('color') != ('white' if self.pov else 'black') or row.get('move_number') != self.before.fullmove_number:
            raise ValueError('Posição não corresponde ao lance selecionado.')
        _, self.after = describe_move(self.before, row['played_san'])
        if row.get('fen_after') and self.after.fen() != board_from_fen(row['fen_after']).fen():
            raise ValueError('FEN posterior inconsistente.')
        self.depth = depth
        self.engine_factory = engine_factory
        self.engine = None
        self.token = object()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.engine is not None:
            self.engine.quit()

    def analyze(self, board):
        # Terminal positions do not need a process at all.
        if not board.is_game_over() and self.engine is None:
            self.engine = self.engine_factory()
        info = evaluate(self.engine, board, self.depth, self.token)
        score = score_data(info['score'].pov(self.pov))
        pv = pv_san(board, info.get('pv', []))
        return {'perspectiva': side(self.pov), 'avaliacao': evaluation(score, self.pov),
                'profundidade': info.get('depth'), 'melhor_lance': pv[0] if pv else None,
                'variante': pv, 'terminal': board.is_game_over(), 'vez': side(board.turn)}

    def run(self, name, args):
        if name not in SCHEMAS or not isinstance(args, dict):
            raise ValueError('Ferramenta ou argumentos inválidos.')
        spec = SCHEMAS[name]
        if set(args) - set(spec['properties']) or not set(spec['required']) <= set(args):
            raise ValueError('Argumentos desconhecidos ou ausentes.')
        position = args.get('position', 'before')
        if position not in ('before', 'after'):
            raise ValueError('position deve ser before ou after.')
        for key in ('move', 'move_a', 'move_b'):
            if key in args and (not isinstance(args[key], str) or not 1 <= len(args[key]) <= 16):
                raise ValueError('Movimento SAN inválido.')
        board, _ = parse_line((self.before if position == 'before' else self.after).copy(stack=False), args.get('line', []))
        if name == 'get_board':
            return {**state(board), 'pecas': {chess.square_name(s): p.symbol() for s, p in board.piece_map().items()},
                    'legenda': 'maiúsculas brancas, minúsculas pretas; P peão N cavalo B bispo R torre Q dama K rei'}
        if name in ('inspect_square', 'get_attackers'):
            sq = args['square']
            if not isinstance(sq, str) or sq not in chess.SQUARE_NAMES:
                raise ValueError('Casa inválida; use a1 a h8.')
            square = chess.parse_square(sq)
            if name == 'inspect_square':
                piece = board.piece_at(square)
                return {'casa': sq, 'peca': piece_name(piece) if piece else None, 'vez': side(board.turn)}
            return {'casa': sq, 'ataques_geometricos': {side(c): [
                {'casa': chess.square_name(s), 'peca': piece_name(board.piece_at(s))}
                for s in board.attackers(c, square)] for c in (chess.WHITE, chess.BLACK)},
                'nota': 'Peças cravadas podem aparecer; ataque geométrico não implica captura legal.'}
        if name == 'get_legal_moves':
            return {'vez': side(board.turn), 'lances': [board.san(m) for m in board.legal_moves]}
        if name == 'simulate_move':
            fact, after = describe_move(board, args['move'])
            return {'movimento': fact, 'depois': state(after)}
        if name == 'validate_sequence':
            if not args['moves']:
                raise ValueError('Informe pelo menos um lance.')
            after, facts = parse_line(board, args['moves'])
            return {'legal': True, 'lances': facts, 'final': state(after), 'nota': 'Legalidade não prova mate forçado.'}
        if name == 'analyze_position':
            return self.analyze(board)
        if name == 'compare_moves':
            a, ba = describe_move(board, args['move_a'])
            b, bb = describe_move(board, args['move_b'])
            return {'alternativa_a': {'movimento': a, 'resultado': self.analyze(ba)},
                    'alternativa_b': {'movimento': b, 'resultado': self.analyze(bb)},
                    'nota': 'Avaliações das posições após cada alternativa; mesma perspectiva e profundidade solicitada.'}
        raise ValueError('Ferramenta indisponível.')
