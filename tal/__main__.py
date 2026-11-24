import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from .settings import DATA, username, positive_int
from .chesscom import ChessCom, ChessComError


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def positive(value):
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError('Informe um inteiro positivo.')
    return n


def fmt(score):
    if score['mate'] is not None:
        sign = '+' if score['mate_winner'] == 'pov' else '-'
        return f'#{sign}{abs(score["mate"])}'
    return f'{score["cp"]/100:+.2f}' if score['cp'] is not None else '?'


def print_move(row):
    mark = '*' if row['is_player'] else ' '
    label = f'{row["move_number"]}{"." if row["color"] == "white" else "..."}'
    print(f'{mark} {label:>5} {row["played_san"]:7} melhor: {row["best_san"] or "-":7} '
          f'{fmt(row["before_mover_pov"]):>7} -> {fmt(row["after_mover_pov"]):>7}  {row["classification"]}', flush=True)


def review(pgn, depth, player, output, metadata=None):
    from .analysis import parse_pgn, open_engine, analyze_game
    game = parse_pgn(pgn)
    engine = open_engine()
    try:
        print(f'Engine: {engine.id.get("name", "UCI")} | profundidade {depth}')
        print(f'{game.headers.get("White")} x {game.headers.get("Black")} | {game.headers.get("Result")}')
        print('Avaliações na perspectiva de quem jogou. * = jogador selecionado.')
        report = analyze_game(game, engine, depth, player, print_move)
    finally:
        engine.quit()
    if metadata:
        report['source'] = {k: metadata.get(k) for k in ('url', 'uuid', 'end_time', 'time_class', 'rated')}
    save_json(output, report)
    print('\nResumo:', json.dumps(report['summary'], ensure_ascii=False))
    print(f'Relatório: {output}')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='TAL', description='Análise de xadrez pós-partida — v1.1')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('doctor', 'games', 'analyze'):
        p = sub.add_parser(name)
        p.add_argument('--user', help='Nickname Chess.com; substitui .env')
        if name == 'doctor':
            p.add_argument('--only', choices=['chesscom', 'stockfish', 'llm', 'all'], default='all')
        else:
            p.add_argument('--limit', type=positive, default=10)
            p.add_argument('--time-class', choices=['bullet', 'blitz', 'rapid', 'daily'])
        if name == 'analyze':
            p.add_argument('--game', type=positive, default=1, help='Índice da lista de partidas recentes, começando em 1')
            p.add_argument('--depth', type=positive)
    p = sub.add_parser('pgn', help='Analisa o primeiro jogo de um PGN local já finalizado')
    p.add_argument('file', type=Path)
    p.add_argument('--depth', type=positive)
    p.add_argument('--player', help='Nome exatamente como consta no PGN')
    p = sub.add_parser('chat', help='Treinador sobre relatório pós-partida')
    p.add_argument('--report', type=Path)
    p.add_argument('--latest', action='store_true', help='Usa relatório mais recente (padrão)')
    p = sub.add_parser('explain', help='Explica um lance de um relatório')
    p.add_argument('--report', type=Path)
    p.add_argument('--move', type=positive, required=True)
    p.add_argument('--color', choices=['white', 'black'], required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'chat':
            from .coach import run_chat
            run_chat(args.report)
            return 0
        if args.command == 'explain':
            from .coach import show_answer
            from .context import load_report, find_move
            from .llm import LocalLLM
            _, report = load_report(args.report)
            show_answer(LocalLLM(), report, 'Explique este lance e a melhor alternativa.', find_move(report, args.move, args.color))
            return 0
        if args.command == 'doctor':
            failed = False
            if args.only in ('all', 'chesscom'):
                try:
                    with ChessCom(username(args.user)) as api:
                        profile = api.profile()
                        archives = api.archives()
                    print(f'[OK] Chess.com: {profile.get("username")} | {len(archives)} arquivos mensais')
                except (ChessComError, ValueError) as exc:
                    failed = True
                    print(f'[ERRO] Chess.com: {exc}', file=sys.stderr)
            if args.only in ('all', 'stockfish'):
                try:
                    import chess
                    import chess.engine
                    from .analysis import open_engine
                    engine = open_engine()
                    try:
                        info = engine.analyse(chess.Board(), chess.engine.Limit(depth=6))
                        print(f'[OK] Stockfish: {engine.id.get("name")} | lance: {info["pv"][0].uci()}')
                    finally:
                        engine.quit()
                except (OSError, ValueError, RuntimeError, ImportError) as exc:
                    failed = True
                    print(f'[ERRO] Stockfish: {exc}', file=sys.stderr)
            if args.only in ('llm', 'all'):
                try:
                    from .llm import LocalLLM
                    print(f'[OK] LLM: {LocalLLM().doctor()}')
                except (ValueError, RuntimeError) as exc:
                    failed = True
                    print(f'[ERRO] LLM: {exc}', file=sys.stderr)
            return int(failed)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        if args.command == 'pgn':
            review(args.file.read_text(encoding='utf-8-sig'), args.depth or positive_int('STOCKFISH_DEPTH', 14),
                   args.player, DATA / 'reports' / f'local-{stamp}.json')
            return 0
        name = username(args.user)
        with ChessCom(name) as api:
            games = api.recent_games(max(args.limit, getattr(args, 'game', 1)), args.time_class)
        if not games:
            raise ValueError('Nenhuma partida finalizada encontrada para esse filtro.')
        if args.command == 'games':
            for i, g in enumerate(games, 1):
                white, black = g.get('white', {}), g.get('black', {})
                date = datetime.fromtimestamp(g['end_time'], timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
                print(f'{i:2}. {date} | {white.get("username")} x {black.get("username")} | '
                      f'{white.get("result")}/{black.get("result")} | {g.get("time_class")} | {g.get("url")}')
            return 0
        if args.game > len(games):
            raise ValueError(f'Índice {args.game} não encontrado; apenas {len(games)} partidas.')
        game = games[args.game - 1]
        output = DATA / 'reports' / f'{name}-{stamp}.json'
        pgn_path = DATA / 'pgn' / f'{name}-{stamp}.pgn'
        pgn_path.parent.mkdir(parents=True, exist_ok=True)
        pgn_path.write_text(game['pgn'], encoding='utf-8')
        print(f'PGN salvo: {pgn_path}')
        review(game['pgn'], args.depth or positive_int('STOCKFISH_DEPTH', 14), name, output, game)
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nAnálise interrompida.', file=sys.stderr)
        return 130

if __name__ == '__main__':
    sys.exit(main())
