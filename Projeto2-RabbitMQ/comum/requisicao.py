# A pergunta sai como evento levando um id, a thread que perguntou bloqueia, e o
# consumidor entrega a resposta que tem o mesmo id.
# a resposta atrasada de uma pergunta ja
# expirada nao e confundida com a resposta da pergunta seguinte, e dois servicos
# diferentes podem usar o mesmo par de eventos sem se atrapalhar, porque cada um so
# reconhece as respostas que ele mesmo pediu e descarta o resto.

import threading
import uuid

from comum import mensageria


class TempoEsgotado(Exception):
    """Ninguem respondeu a pergunta dentro do prazo."""


class _Pendente:
    """Pergunta aguardando resposta. O evento acorda a thread que perguntou."""

    def __init__(self):
        self.respondida = threading.Event()
        self.resposta = None


class Correlacionador:
    """Casa as perguntas e respostas de um par de eventos."""

    def __init__(self):
        self._lock = threading.Lock()
        self._pendentes = {}  # correlacao -> _Pendente

    def perguntar(self, canal, routing_key, dados=None, espera=5):
        """Publica a pergunta e bloqueia ate a resposta chegar.

        Levanta TempoEsgotado se ninguem responder no prazo.
        """
        correlacao = uuid.uuid4().hex
        pendente = _Pendente()
        with self._lock:
            self._pendentes[correlacao] = pendente
        try:
            evento = dict(dados or {})
            evento["correlacao"] = correlacao
            mensageria.publicar(canal, routing_key, evento)
            if not pendente.respondida.wait(timeout=espera):
                raise TempoEsgotado(f"sem resposta para {routing_key} em {espera}s")
            return pendente.resposta
        finally:
            with self._lock:
                self._pendentes.pop(correlacao, None)

    def responder(self, evento):
        """Entrega a resposta a quem a aguarda (chamado pela thread do consumidor).

        Resposta sem dono e descartada: ou a pergunta expirou, ou quem perguntou
        foi outro servico.
        """
        with self._lock:
            pendente = self._pendentes.get(evento.get("correlacao"))
        if pendente is None:
            return
        pendente.resposta = evento
        pendente.respondida.set()
