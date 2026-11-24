import os
import time
from urllib.parse import urlparse
import requests

BASE = 'https://api.chess.com/pub'

class ChessComError(RuntimeError):
    pass

class ChessCom:
    def __init__(self, username, session=None):
        self.username = username
        self.session = session or requests.Session()
        contact = os.getenv('CHESSCOM_CONTACT', '').strip()
        agent = f'TAL/1.0 (username: {username}' + (f'; contact: {contact}' if contact else '') + ')'
        self.session.headers.update({'User-Agent': agent, 'Accept': 'application/json'})

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    def get(self, url):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.netloc != 'api.chess.com':
            raise ChessComError('URL de arquivo inesperada.')
        for attempt in range(3):
            try:
                response = self.session.get(url, timeout=30)
            except requests.RequestException as exc:
                if attempt == 2:
                    raise ChessComError(f'Falha de conexão: {exc}') from exc
                time.sleep(2 ** attempt)
                continue
            if response.status_code == 404:
                raise ChessComError('Usuário ou arquivo não encontrado (404). Confira o nickname.')
            if response.status_code == 403:
                raise ChessComError('Acesso negado (403). Confira o User-Agent/contato e tente novamente mais tarde.')
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 2:
                    raise ChessComError(f'Chess.com indisponível ou limitando requisições ({response.status_code}).')
                retry = response.headers.get('Retry-After', '')
                if retry.isdigit() and int(retry) > 30:
                    raise ChessComError(f'Chess.com solicitou aguardar {retry} segundos. Tente mais tarde.')
                time.sleep(max(2 ** attempt, int(retry) if retry.isdigit() else 0))
                continue
            if not response.ok:
                raise ChessComError(f'Chess.com retornou HTTP {response.status_code}.')
            try:
                return response.json()
            except ValueError as exc:
                raise ChessComError('Resposta JSON inválida.') from exc

    def profile(self):
        return self.get(f'{BASE}/player/{self.username}')

    def stats(self):
        return self.get(f'{BASE}/player/{self.username}/stats')

    def archives(self):
        return self.get(f'{BASE}/player/{self.username}/games/archives').get('archives', [])

    def recent_games(self, limit=10, time_class=None):
        """Percorre arquivos mensais do mais novo ao mais antigo, em série."""
        result, seen = [], set()
        for archive in sorted(self.archives(), reverse=True):
            games = self.get(archive).get('games', [])
            for game in sorted(games, key=lambda g: g.get('end_time', 0), reverse=True):
                if game.get('rules') != 'chess' or not game.get('pgn') or not game.get('end_time'):
                    continue
                if time_class and game.get('time_class') != time_class:
                    continue
                key = game.get('uuid') or game.get('url') or game['pgn']
                if key not in seen:
                    result.append(game)
                    seen.add(key)
                if len(result) >= limit:
                    return result
        return result
