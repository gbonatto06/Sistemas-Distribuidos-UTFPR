# microservico de promocoes
# Consome : interesse.promocao (inscrever / cancelar)
# REST    : GET /produtos no Estoque; POST /emails no Resend (API externa)
#
# Guarda os e-mails inscritos e suas categorias. A cada PROMOCAO_INTERVALO
# sorteia um produto de uma categoria que tem inscritos, aplica um desconto e
# manda o e-mail so para quem se interessa por aquela categoria.

import random
import threading
import time

from comum import estoque_cliente, mensageria
from comum.config import (
    ACAO_CANCELAR,
    ACAO_INSCREVER,
    FILA_PROMOCOES,
    PROMOCAO_INTERVALO,
    RK_INTERESSE_PROMOCAO,
)
from servico_promocoes import correio

ROUTING_KEYS = [RK_INTERESSE_PROMOCAO]

DESCONTOS = (10, 15, 20, 25, 30, 40, 50)

# e-mail -> categorias de interesse. Escrito pela thread do consumidor e lido
# pelo laco de promocoes, por isso o lock.
_lock = threading.Lock()
_interesses = {}


def tratar(_canal, routing_key, evento):
    if routing_key != RK_INTERESSE_PROMOCAO:
        return
    email = evento["email"]
    categorias = set(evento.get("categorias", []))
    acao = evento.get("acao")

    with _lock:
        if acao == ACAO_INSCREVER:
            # o formulario manda o conjunto inteiro: passa a valer exatamente este
            _interesses[email] = categorias
        elif acao == ACAO_CANCELAR:
            # sem categorias cancela todas
            restantes = _interesses.get(email, set()) - categorias if categorias else set()
            if restantes:
                _interesses[email] = restantes
            else:
                _interesses.pop(email, None)
        atuais = sorted(_interesses.get(email, set()))
    print(f"[promocoes] {email}: {acao} -> categorias atuais {atuais or 'nenhuma'}")


def gerar_promocao():
    """Sorteia um produto entre as categorias com inscritos e dispara os e-mails."""
    with _lock:
        interesses = {email: set(cats) for email, cats in _interesses.items()}
    categorias = set().union(*interesses.values())
    if not categorias:
        print("[promocoes] ninguem inscrito; nada a enviar")
        return

    candidatos = [
        produto for produto in estoque_cliente.produtos(disponiveis=True)
        if produto["categoria"] in categorias
    ]
    if not candidatos:
        print(f"[promocoes] nenhum produto em estoque nas categorias {sorted(categorias)}")
        return

    produto = random.choice(candidatos)
    desconto = random.choice(DESCONTOS)
    preco = round(produto["preco"] * (100 - desconto) / 100, 2)
    destinatarios = sorted(e for e, cats in interesses.items() if produto["categoria"] in cats)

    print(f"[promocoes] {produto['nome']} (categoria {produto['categoria']}): -{desconto}% "
          f"-> {len(destinatarios)} inscrito(s)")
    mensagem = correio.mensagem_promocao(produto, desconto, preco)
    for email in destinatarios:
        correio.enviar(email, *mensagem)


def main():
    print(f"[promocoes] envio de e-mail: {'Resend' if correio.ativo() else 'SIMULADO (sem RESEND_API_KEY)'}")
    print(f"[promocoes] uma promocao a cada {PROMOCAO_INTERVALO}s  (Ctrl+C para encerrar)")

    mensageria.definir_servico("promocoes")
    mensageria.consumir_em_segundo_plano(FILA_PROMOCOES, ROUTING_KEYS, tratar)

    try:
        while True:
            time.sleep(PROMOCAO_INTERVALO)
            try:
                gerar_promocao()
            except Exception as erro:
                # uma promocao que falha (ex.: Estoque fora do ar) nao derruba o laco
                print(f"[promocoes] falha ao gerar promocao: {erro}")
    except KeyboardInterrupt:
        print("\n[promocoes] encerrado")


if __name__ == "__main__":
    main()
