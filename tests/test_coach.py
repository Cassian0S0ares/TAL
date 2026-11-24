import unittest
from unittest.mock import patch, Mock
from tal.context import find_move, critical_moves, context
from tal.coach import ask
from tal.llm import LocalLLM, LLMError

R = {'headers': {'White': 'a', 'Black': 'b'}, 'player_color': 'black', 'moves': [
    {'move_number': 13, 'color': 'black', 'is_player': True, 'played_san': 'Nc5', 'best_san': 'Qb5', 'centipawn_loss': 415},
    {'move_number': 14, 'color': 'white', 'is_player': False, 'centipawn_loss': 999}]}

class TestCoach(unittest.TestCase):
    def test_selection(self):
        row = find_move(R, 13, 'black')
        self.assertEqual(critical_moves(R), [row])
        self.assertIn('Qb5', context(R, row))
        with self.assertRaises(ValueError):
            find_move(R, 99, 'black')
    def test_prompt(self):
        client = Mock()
        client.complete.return_value = ('teste', 'stop')
        self.assertEqual(ask(client, R, 'Por quê?', R['moves'][0]), ('teste', 'stop'))
        messages = client.complete.call_args.args[0]
        self.assertIn('Nc5', messages[1]['content'])
    @patch('tal.llm.requests.request')
    def test_api(self, request):
        request.return_value.json.return_value = {'choices': [{'message': {'content': 'Olá'}, 'finish_reason': 'stop'}]}
        client = LocalLLM()
        self.assertEqual(client.complete([{'role': 'user', 'content': 'Teste'}]), ('Olá', 'stop'))
        self.assertTrue(request.call_args.kwargs['json']['messages'][-1]['content'].endswith('/no_think'))
    @patch('tal.llm.requests.request')
    def test_missing_model(self, request):
        request.return_value.json.return_value = {'data': []}
        with self.assertRaises(LLMError):
            LocalLLM().doctor()
