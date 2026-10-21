import { useState } from "react";
import type { Produto } from "../api";
import { reais } from "../status";

type Props = {
  produtos: Produto[];
  categorias: string[];
  carregando: boolean;
  erro: string;
  noCarrinho: Record<string, number>;
  onAdicionar: (produto: Produto, quantidade: number) => void;
  onRecarregar: () => void;
};

export function Catalogo({ produtos, categorias, carregando, erro, noCarrinho, onAdicionar, onRecarregar }: Props) {
  const [filtro, setFiltro] = useState<string>("");
  const visiveis = filtro ? produtos.filter((p) => p.categoria === filtro) : produtos;

  return (
    <section className="catalogo" aria-label="Catálogo">
      <div className="barra-secao">
        <div className="filtros" role="group" aria-label="Filtrar por categoria">
          <button className={`chip ${filtro === "" ? "ativo" : ""}`} onClick={() => setFiltro("")}>
            Todas
          </button>
          {categorias.map((c) => (
            <button key={c} className={`chip ${filtro === c ? "ativo" : ""}`} onClick={() => setFiltro(c)}>
              Categoria {c}
            </button>
          ))}
        </div>
        <button className="botao fantasma" onClick={onRecarregar} disabled={carregando}>
          {carregando ? "Atualizando…" : "Atualizar"}
        </button>
      </div>

      {erro && (
        <div className="aviso erro" role="alert">
          {erro}. <button className="link" onClick={onRecarregar}>Tentar de novo</button>
        </div>
      )}

      <div className="grade">
        {visiveis.map((produto) => (
          <CartaoProduto
            key={produto.id}
            produto={produto}
            noCarrinho={noCarrinho[produto.id] ?? 0}
            onAdicionar={onAdicionar}
          />
        ))}
        {!carregando && !erro && visiveis.length === 0 && (
          <p className="suave">Nenhum produto nesta categoria.</p>
        )}
      </div>
    </section>
  );
}

function CartaoProduto({
  produto,
  noCarrinho,
  onAdicionar,
}: {
  produto: Produto;
  noCarrinho: number;
  onAdicionar: (produto: Produto, quantidade: number) => void;
}) {
  const livre = Math.max(0, produto.quantidade - noCarrinho);
  const [quantidade, setQuantidade] = useState(1);
  const qtd = Math.min(quantidade, Math.max(livre, 1));
  const esgotado = produto.quantidade === 0;

  let saldo = `${produto.quantidade} em estoque`;
  if (esgotado) saldo = "Esgotado";
  else if (produto.quantidade === 1) saldo = "Última unidade";
  else if (produto.quantidade === 2) saldo = "Últimas 2";

  return (
    <article className={`cartao produto ${esgotado ? "esgotado" : ""}`}>
      <div className="produto-topo">
        <span className="selo">Categoria {produto.categoria}</span>
        <span className={`saldo ${esgotado ? "zero" : produto.quantidade <= 2 ? "baixo" : ""}`}>{saldo}</span>
      </div>
      <h3>{produto.nome}</h3>
      <p className="preco">{reais(produto.preco)}</p>
      <div className="produto-acoes">
        <div className="contador" aria-label="Quantidade">
          <button onClick={() => setQuantidade(Math.max(1, qtd - 1))} disabled={esgotado || qtd <= 1} aria-label="Menos">
            −
          </button>
          <span aria-live="polite">{qtd}</span>
          <button onClick={() => setQuantidade(qtd + 1)} disabled={qtd >= livre} aria-label="Mais">
            +
          </button>
        </div>
        <button
          className="botao primario"
          disabled={livre === 0}
          onClick={() => {
            onAdicionar(produto, qtd);
            setQuantidade(1);
          }}
        >
          {esgotado ? "Esgotado" : livre === 0 ? "No carrinho" : "Adicionar"}
        </button>
      </div>
      {noCarrinho > 0 && <p className="no-carrinho">{noCarrinho} no carrinho</p>}
    </article>
  );
}
