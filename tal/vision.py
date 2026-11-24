"""Deterministic board facts for completed-game reports (standard chess)."""
import chess

PIECES = dict(enumerate(('', 'peão', 'cavalo', 'bispo', 'torre', 'dama', 'rei')))


def side(color):
    return 'brancas' if color else 'pretas'


def piece_name(piece):
    return f'{PIECES[piece.piece_type]} ({side(piece.color)})'


def board_from_fen(fen):
    board = chess.Board(fen)
    if not board.is_valid():
        raise ValueError('FEN inválido ou posição ilegal.')
    return board


def describe_move(board, san):
    # parse_san resolves the legal move; null moves are not allowed here.
    move = board.parse_san(san)
    if move not in board.legal_moves:
        raise ValueError(f'Lance ilegal: {san}')
    piece = board.piece_at(move.from_square)
    capture_square = move.to_square
    if board.is_en_passant(move):
        capture_square += -8 if board.turn else 8
    captured = board.piece_at(capture_square) if board.is_capture(move) else None
    out = {'san': board.san(move), 'peca': piece_name(piece),
           'origem': chess.square_name(move.from_square), 'destino': chess.square_name(move.to_square),
           'captura': f'{piece_name(captured)} em {chess.square_name(capture_square)}' if captured else None,
           'responde_a_xeque': board.is_check()}
    if board.is_castling(move):
        out['roque'] = 'pequeno' if board.is_kingside_castling(move) else 'grande'
    if move.promotion:
        out['promocao'] = PIECES[move.promotion]
    after = board.copy(stack=False)
    after.push(move)
    out['da_xeque'] = after.is_check()
    out['da_mate'] = after.is_checkmate()
    return out, after


def line_facts(board, line, limit=4):
    """Replay engine SAN in order, without changing the input board."""
    facts = []
    for san in (line or []):
        fact, board = describe_move(board, san)
        if len(facts) < limit:
            facts.append(fact)
    return facts


def evaluation(score, color):
    if not score:
        return None
    mover = side(color)
    other = side(not color)
    if score.get('mate') is not None:
        winner = score.get('mate_winner')
        if winner not in ('pov', 'opponent'):
            raise ValueError('Relatório de mate sem perspectiva válida.')
        return {'mate_favor': mover if winner == 'pov' else other,
                'mate_em': abs(score['mate'])}
    cp = score.get('cp')
    if cp is None:
        return None
    return {'cp_de_quem_jogou': cp, 'favor': mover if cp > 0 else other if cp < 0 else 'igual'}


def vision_facts(row):
    fen = row.get('fen_before')
    if not fen:
        return {'status': 'indisponível: relatório sem FEN'}
    board = board_from_fen(fen)
    if row.get('color') != ('white' if board.turn else 'black'):
        raise ValueError('Cor do lance não corresponde ao FEN.')
    if row.get('move_number') != board.fullmove_number:
        raise ValueError('Número do lance não corresponde ao FEN.')
    played, after = describe_move(board, row['played_san'])
    if row.get('fen_after') and after.fen() != board_from_fen(row['fen_after']).fen():
        raise ValueError('FEN posterior não corresponde ao lance realizado.')
    best = None
    if row.get('best_san'):
        best, _ = describe_move(board, row['best_san'])
    best_line = row.get('best_line_san') or []
    if best and best_line and board.parse_san(best_line[0]) != board.parse_san(row['best_san']):
        raise ValueError('Variante principal não começa pelo melhor lance.')
    pieces = {side(c): {PIECES[t]: [chess.square_name(sq) for sq in board.pieces(t, c)]
                        for t in range(1, 7)} for c in (chess.WHITE, chess.BLACK)}
    return {'lado': side(board.turn), 'tabuleiro_antes': pieces, 'jogado': played, 'melhor': best,
            'antes': evaluation(row.get('before_mover_pov'), board.turn),
            'depois': evaluation(row.get('after_mover_pov'), board.turn),
            'direitos_roque_apos': {side(c): [name for name, allowed in (
                ('pequeno', after.has_kingside_castling_rights(c)),
                ('grande', after.has_queenside_castling_rights(c))) if allowed] for c in (chess.WHITE, chess.BLACK)},
            'linha_melhor': line_facts(board, best_line, 3),
            'linha_resposta': line_facts(after, row.get('reply_line_san'), 3)}


def main():
    import argparse
    import json
    from .context import load_report, find_move, facts
    parser = argparse.ArgumentParser(description='Inspeciona fatos do tabuleiro sem chamar o LLM.')
    parser.add_argument('--report')
    parser.add_argument('--move', type=int, required=True)
    parser.add_argument('--color', choices=('white', 'black'), required=True)
    args = parser.parse_args()
    _, report = load_report(args.report)
    row = find_move(report, args.move, args.color)
    print(json.dumps(facts(row), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
