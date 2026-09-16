# Publica : produtos.consulta.promocoes, promocao.categoria.<A|B|C>
# Consome : produtos.catalogo.promocoes

# Gera promocoes aleatorias e publica na exchange topic com routing key carregando a categoria do produto.
# consumidor escolhe no binding o que quer receber

import random
import threading

from comum import mensageria, requisicao
from comum.config import (
    FILA_PROMOCOES,
    PROMOCAO_INTERVALO,
    rk_catalogo_para,
    rk_consulta_catalogo,
    rk_promocao,
)

RK_CATALOGO = rk_catalogo_para("promocoes")
RK_CONSULTA = rk_consulta_catalogo("promocoes")

ROUTING_KEYS = [RK_CATALOGO]

DESCONTOS = (10, 15, 20, 25, 30, 40, 50)

_correlacionador = requisicao.Correlacionador()


def tratar(canal, routing_key, evento):
    if routing_key == RK_CATALOGO:
        _correlacionador.responder(evento)


def gerar_promocao(canal):
    """Sorteia um produto do catalogo e publica a promocao na categoria dele."""
    resposta = _correlacionador.perguntar(canal, RK_CONSULTA)
    produtos = resposta["produtos"]
    if not produtos:
        print("[promocoes] catalogo vazio; nada a promover")
        return

    produto = random.choice(produtos)
    desconto = random.choice(DESCONTOS)
    routing_key = rk_promocao(produto["categoria"])

    print(f"[promocoes] {produto['nome']}: -{desconto}% -> {routing_key}")
    mensageria.publicar(
        canal,
        routing_key,
        {
            "produto_id": produto["id"],
            "nome": produto["nome"],
            "categoria": produto["categoria"],
            "preco_original": produto["preco"],
            "preco_promocional": round(produto["preco"] * (100 - desconto) / 100, 2),
            "desconto": desconto,
        },
    )


def main():
    print(f"[promocoes] uma promocao a cada {PROMOCAO_INTERVALO}s")
    print("[promocoes] Ctrl+C para encerrar")
    mensageria.definir_servico("promocoes")

    # O consumidor sobe primeiro: sem a fila ligada, a resposta do catalogo se
    # perderia e nenhuma promocao sairia.
    pronto = threading.Event()
    threading.Thread(
        target=mensageria.consumir,
        args=(FILA_PROMOCOES, ROUTING_KEYS, tratar),
        kwargs={"pronto": pronto},
        daemon=True,
    ).start()
    if not pronto.wait(timeout=30):
        print("[promocoes] a fila nao ficou pronta; encerrando")
        return

    conexao, canal = mensageria.conectar()
    try:
        while True:
            try:
                gerar_promocao(canal)
            except requisicao.TempoEsgotado as erro:
                print(f"[promocoes] {erro}; tento de novo no proximo ciclo")
            # sleep da propria conexao: responde heartbeat enquanto espera
            conexao.sleep(PROMOCAO_INTERVALO)
    except KeyboardInterrupt:
        print("\n[promocoes] encerrado")
    finally:
        if conexao.is_open:
            conexao.close()


if __name__ == "__main__":
    main()
