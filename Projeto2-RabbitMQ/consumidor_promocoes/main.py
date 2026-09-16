# script de consumidores de promocoes
import os

from comum import mensageria
from comum.config import CATEGORIAS, PADRAO_TODAS_PROMOCOES, rk_promocao


def padroes(escolha):
    """Traduz "A,B" (ou vazio) nos padroes de binding da exchange topic.

    Categorias informadas viram uma routing key cada; nenhuma categoria valida
    significa "todas", e ai o binding e o curinga promocao.#
    """
    pedidas = [parte.strip().upper() for parte in escolha.replace(" ", ",").split(",")]
    validas = [categoria for categoria in CATEGORIAS if categoria in pedidas]
    if not validas:
        return [PADRAO_TODAS_PROMOCOES]
    return [rk_promocao(categoria) for categoria in validas]


def mostrar(_canal, _routing_key, evento):
    print(
        f"[promocao {evento['categoria']}] {evento['nome']}: -{evento['desconto']}% "
        f"(de {evento['preco_original']:.2f} por {evento['preco_promocional']:.2f})"
    )


def main():
    consumidor = os.environ.get("CONSUMIDOR_ID", "c1").strip() or "c1"
    ligados = padroes(os.environ.get("CATEGORIAS_INTERESSE", ""))
    fila = f"promocoes.{consumidor}"

    print(f"[{consumidor}] fila propria: {fila}")
    print(f"[{consumidor}] inscrito em: {', '.join(ligados)}")
    print(f"[{consumidor}] Ctrl+C para encerrar")
    try:
        mensageria.definir_servico(consumidor)
        mensageria.consumir(fila, ligados, mostrar, exclusiva=True)
    except KeyboardInterrupt:
        print(f"\n[{consumidor}] encerrado")


if __name__ == "__main__":
    main()
