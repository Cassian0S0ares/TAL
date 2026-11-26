import json
import unittest
from unittest.mock import Mock
from tal.agent import run_agent
from tal.llm import LLMError


def call(name='inspect_square', args='{"square":"c4"}', cid='call1'):
    return {'choices': [{'finish_reason': 'tool_calls', 'message': {'content': '', 'tool_calls': [
        {'id': cid, 'type': 'function', 'function': {'name': name, 'arguments': args}}]}}]}


def answer(content='Bispo branco.', finish='stop'):
    return {'choices': [{'finish_reason': finish, 'message': {'content': content}}]}


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.client = Mock(model='tal-base', temperature=0.2, max_tokens=512)
        self.tools = Mock()
        self.tools.run.return_value = {'peca': 'bispo (brancas)'}
        self.messages = [{'role': 'user', 'content': 'Qual peça está em c4?'}]

    def test_round_trip(self):
        self.client.request.side_effect = [call(), answer()]
        trace = Mock()
        self.assertEqual(run_agent(self.client, self.tools, self.messages, 1, trace), ('Bispo branco.', 'stop', 1))
        self.tools.run.assert_called_once_with('inspect_square', {'square': 'c4'})
        sent = self.client.request.call_args.kwargs['json']
        self.assertEqual(sent['tool_choice'], 'none')
        self.assertEqual(sent['messages'][-1]['tool_call_id'], 'call1')
        self.assertTrue(json.loads(sent['messages'][-1]['content'])['ok'])
        self.assertEqual(len(self.messages), 1)
        trace.assert_called_once()

    def test_reject_no_tool(self):
        self.client.request.return_value = answer()
        with self.assertRaises(LLMError):
            run_agent(self.client, self.tools, self.messages)

    def test_error_then_recovery(self):
        self.client.request.side_effect = [call(args='{'), call(cid='call2'), answer()]
        self.assertEqual(run_agent(self.client, self.tools, self.messages, 2)[2], 2)
        self.tools.run.assert_called_once()
        sent = self.client.request.call_args.kwargs['json']['messages']
        self.assertFalse(json.loads(sent[2]['content'])['ok'])

    def test_limit(self):
        self.client.request.side_effect = [call(), call(cid='call2')]
        with self.assertRaises(LLMError):
            run_agent(self.client, self.tools, self.messages, 1)
        self.tools.run.assert_called_once()

    def test_empty_final(self):
        self.client.request.side_effect = [call(), answer('')]
        with self.assertRaisesRegex(LLMError, 'vazia'):
            run_agent(self.client, self.tools, self.messages)

    def test_duplicate_id(self):
        self.client.request.side_effect = [call(), call()]
        with self.assertRaises(LLMError):
            run_agent(self.client, self.tools, self.messages)

    def test_fallback_after_no_tool(self):
        self.client.request.side_effect = [answer('Rascunho incorreto'), answer('Bispo branco.')]
        trace = Mock()
        fallback = ('inspect_square', {'square': 'c4'})
        self.assertEqual(run_agent(self.client, self.tools, self.messages, 1, trace, fallback), ('Bispo branco.', 'stop', 1))
        self.tools.run.assert_called_once_with(*fallback)
        sent = self.client.request.call_args.kwargs['json']
        self.assertEqual(sent['tool_choice'], 'none')
        self.assertEqual(sent['messages'][-1]['role'], 'user')
        self.assertNotIn('Rascunho incorreto', str(sent['messages']))
        self.assertIn('bispo (brancas)', sent['messages'][-1]['content'])
        self.assertEqual(trace.call_args.args[0]['origem'], 'contingencia')

    def test_fallback_failure_closed(self):
        self.client.request.return_value = answer('Rascunho incorreto')
        self.tools.run.side_effect = ValueError('falha de ferramenta')
        with self.assertRaisesRegex(LLMError, 'Consulta obrigatória falhou'):
            run_agent(self.client, self.tools, self.messages, 1, fallback=('inspect_square', {'square': 'c4'}))
        self.assertEqual(self.client.request.call_count, 1)

    def test_autonomous_call_preserved_with_fallback(self):
        self.client.request.side_effect = [call(), answer()]
        self.assertEqual(run_agent(self.client, self.tools, self.messages, 1, fallback=('analyze_position', {}))[2], 1)
        self.tools.run.assert_called_once_with('inspect_square', {'square': 'c4'})
