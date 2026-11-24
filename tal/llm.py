"""Client for a local OpenAI-compatible llama.cpp server."""
import os
import requests
from .settings import positive_int

class LLMError(RuntimeError):
    pass

class LocalLLM:
    def __init__(self):
        self.url = os.getenv('LLM_BASE_URL', 'http://127.0.0.1:8080/v1').rstrip('/')
        self.model = os.getenv('LLM_MODEL', 'tal-base')
        self.timeout = positive_int('LLM_TIMEOUT', 180)
        self.max_tokens = positive_int('LLM_MAX_TOKENS', 256)
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.3'))
        if not 0 <= self.temperature <= 2:
            raise ValueError('LLM_TEMPERATURE deve estar entre 0 e 2.')

    def request(self, method, path, **kwargs):
        try:
            r = requests.request(method, self.url + path, timeout=(5, self.timeout), **kwargs)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, dict):
                raise ValueError('Resposta não é um objeto JSON.')
            return data
        except (requests.RequestException, ValueError) as e:
            raise LLMError(f'Falha na API LLM ({self.url}): {e}') from e

    def doctor(self):
        data = self.request('GET', '/models')
        if self.model not in [m.get('id') for m in data.get('data', [])]:
            raise LLMError(f'Modelo {self.model!r} não encontrado. Confira --alias e LLM_MODEL.')
        return self.model

    def complete(self, messages):
        # Guard against Qwen3 switching to verbose thinking mode.
        messages = [dict(m) for m in messages]
        messages[-1]['content'] += '\n/no_think'
        data = self.request('POST', '/chat/completions', json={
            'model': self.model, 'messages': messages, 'temperature': self.temperature,
            'max_tokens': self.max_tokens, 'stream': False})
        try:
            choice = data['choices'][0]
            result = choice['message']['content']
            if not isinstance(result, str) or not result.strip():
                raise ValueError('Resposta vazia.')
            return result.strip(), choice.get('finish_reason')
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise LLMError(f'Resposta inválida do modelo: {e}') from e
