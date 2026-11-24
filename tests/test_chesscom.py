import unittest
from unittest.mock import Mock, patch
from tal.chesscom import ChessCom, ChessComError
from tal.settings import username

class TestChessCom(unittest.TestCase):
    def test_recent(self):
        api = ChessCom('demo')
        api.archives = Mock(return_value=['https://api.chess.com/old', 'https://api.chess.com/new'])
        def g(i, kind='rapid', rules='chess'):
            return {'uuid': str(i), 'end_time': i, 'time_class': kind, 'rules': rules, 'pgn': 'pgn'}
        api.get = Mock(side_effect=[{'games':[g(2), g(4, 'blitz'), g(3), g(9, rules='chess960')]}, {'games':[g(2), g(1)]}])
        # Explicit archive dates reflect API ordering.
        api.archives.return_value = ['https://api.chess.com/2025/01', 'https://api.chess.com/2025/02']
        self.assertEqual([x['uuid'] for x in api.recent_games(3, 'rapid')], ['3','2','1'])
        api.session.close()

    def test_retry(self):
        session = Mock()
        bad = Mock(status_code=429, headers={'Retry-After':'0'})
        ok = Mock(status_code=200, ok=True)
        ok.json.return_value = {'username':'demo'}
        session.get.side_effect = [bad, ok]
        with patch('tal.chesscom.time.sleep'):
            self.assertEqual(ChessCom('demo', session).profile()['username'], 'demo')
        self.assertEqual(session.get.call_count, 2)

    def test_404(self):
        session = Mock()
        session.get.return_value = Mock(status_code=404)
        with self.assertRaises(ChessComError):
            ChessCom('demo', session).profile()

    def test_username(self):
        self.assertEqual(username('Demo-123'), 'demo-123')
        with self.assertRaises(ValueError):
            username('../invalid')
