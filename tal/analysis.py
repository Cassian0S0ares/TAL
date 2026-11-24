import io
import chess
import chess.engine
import chess.pgn
from .settings import engine_path, positive_int


def open_engine():
    engine = chess.engine.SimpleEngine.popen_uci(engine_path(), timeout=60)
    try:
        options = {}
        for name, key, default in [('Threads', 'STOCKFISH_THREADS', 2), ('Hash', 'STOCKFISH_HASH_MB', 64)]:
            if name in engine.options:
                opt = engine.options[name]
                n = positive_int(key, default)
                options[name] = max(opt.min, min(opt.max, n))
        if options:
            engine.configure(options)
        return engine
    except Exception:
        engine.quit()
        raise


def parse_pgn(pgn):
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None or game.errors:
        raise ValueError('PGN vazio ou inválido.')
    if type(game.board()) is not chess.Board or game.board().chess960:
        raise ValueError('TAL v1 suporta apenas xadrez padrão.')
    if not any(game.mainline_moves()):
        raise ValueError('PGN sem movimentos.')
    return game


def score_data(score):
    return {'cp': score.score(), 'mate': score.mate(),
            'mate_winner': ('pov' if score > chess.engine.Cp(0) else 'opponent') if score.is_mate() else None}


def category(loss, played_best, before_mate=None, after_mate=None):
    if played_best:
        return 'melhor'
    if before_mate is not None or after_mate is not None:
        if (before_mate is None or before_mate >= 0) and after_mate is not None and after_mate < 0:
            return 'permite_mate'
        if before_mate is not None and before_mate > 0 and (after_mate is None or after_mate < 0):
            return 'perde_mate_forcado'
        return 'linha_de_mate'
    if loss is None:
        return 'sem_classificacao'
    if loss < 20:
        return 'excelente'
    if loss < 50:
        return 'bom'
    if loss < 100:
        return 'imprecisao'
    if loss < 200:
        return 'erro'
    return 'erro_grave'


def pv_san(board, pv, max_moves=8):
    copy = board.copy()
    result = []
    for move in pv[:max_moves]:
        result.append(copy.san(move))
        copy.push(move)
    return result


def evaluate(engine, board, depth, game_token):
    if board.is_game_over():
        outcome = board.outcome()
        score = chess.engine.Mate(0) if board.is_checkmate() else chess.engine.Cp(0)
        return {'score': chess.engine.PovScore(score, board.turn), 'pv': [], 'depth': None,
                'terminal': outcome.termination.name if outcome else None}
    return engine.analyse(board, chess.engine.Limit(depth=depth), game=game_token)


def analyze_game(game, engine, depth=14, player=None, on_move=None):
    """Avalia N+1 posições e reutiliza a avaliação posterior no próximo lance."""
    board = game.board()
    token = object()
    before = evaluate(engine, board, depth, token)
    moves = []
    player_color = None
    if player:
        for key, color in [('White', chess.WHITE), ('Black', chess.BLACK)]:
            if game.headers.get(key, '').casefold() == player.casefold():
                player_color = color
    for ply, move in enumerate(game.mainline_moves(), 1):
        color = board.turn
        fen = board.fen()
        number = board.fullmove_number
        san = board.san(move)
        pv = before.get('pv', [])
        best = pv[0] if pv else None
        best_san = board.san(best) if best else None
        line = pv_san(board, pv)
        previous = before['score'].pov(color)
        board.push(move)
        after = evaluate(engine, board, depth, token)
        current = after['score'].pov(color)
        a, b = previous.score(), current.score()
        loss = max(0, a - b) if a is not None and b is not None else None
        # Mate(0) means checkmated, MateGiven.mate() also returns 0; distinguish by score ordering.
        def mate_kind(s):
            m = s.mate()
            if m == 0:
                return 1 if s > chess.engine.Cp(0) else -1
            return m
        tag = category(loss, move == best, mate_kind(previous), mate_kind(current))
        row = {
            'ply': ply, 'move_number': number, 'color': 'white' if color else 'black',
            'is_player': color == player_color if player_color is not None else None,
            'fen_before': fen, 'fen_after': board.fen(), 'played_san': san, 'played_uci': move.uci(),
            'best_san': best_san, 'best_uci': best.uci() if best else None,
            'best_line_san': line, 'reply_line_san': pv_san(board, after.get('pv', [])),
            'before_mover_pov': score_data(previous), 'after_mover_pov': score_data(current),
            'before_white_pov': score_data(before['score'].white()),
            'after_white_pov': score_data(after['score'].white()),
            'centipawn_loss': loss, 'classification': tag,
            'depth_before': before.get('depth'), 'depth_after': after.get('depth'),
            'terminal_after': after.get('terminal'),
        }
        moves.append(row)
        if on_move:
            on_move(row)
        before = after
    from collections import Counter
    relevant = [m for m in moves if m['is_player']] if player_color is not None else moves
    losses = [m['centipawn_loss'] for m in relevant if m['centipawn_loss'] is not None]
    return {'schema_version': 1, 'headers': dict(game.headers), 'engine': engine.id.get('name', 'UCI'),
            'depth': depth, 'player': player, 'player_color': ('white' if player_color else 'black') if player_color is not None else None,
            'summary': {'scope': 'player' if player_color is not None else 'both', 'plies': len(relevant),
                        'mean_centipawn_loss': round(sum(losses) / len(losses), 2) if losses else None,
                        'cp_sample_size': len(losses), 'classifications': dict(Counter(m['classification'] for m in relevant))},
            'moves': moves}
