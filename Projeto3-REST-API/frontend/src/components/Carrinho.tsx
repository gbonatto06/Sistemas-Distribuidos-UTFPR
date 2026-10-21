import type { Produto } from "../api";
import { reais } from "../status";

type Props = {
  itens: Record<string, number>;
  produtos: Produto[];
  enviando: boolean;
  onAlterar: (produtoId: string, quantidade: number) => void;
  onFinalizar: () => void;
};

export function Carrinho({ itens, produtos, enviando, onAlterar, onFinalizar }: Props) {
  const porId = new Map(produtos.map((p) => [p.id, p]));
  const linhas = Object.entries(itens)
    .map(([id, quantidade]) => ({ produto: porId.get(id), id, quantidade }))
    .filter((l) => l.quantidade > 0);
  const total = linhas.reduce((soma, l) => soma + (l.produto?.preco ?? 0) * l.quantidade, 0);
  const unidades = linhas.reduce((soma, l) => soma + l.quantidade, 0);

  return (
    <aside className="cartao carrinho" aria-label="Carrinho">
      <h2>
        Carrinho {unidades > 0 && <span className="contagem">{unidades}</span>}
      </h2>

      {linhas.length === 0 ? (
        <p className="suave">Seu carrinho está vazio. Escolha produtos no catálogo.</p>
      ) : (
        <ul className="linhas-carrinho">
          {linhas.map(({ id, produto, quantidade }) => {
            const maximo = produto?.quantidade ?? quantidade;
            return (
              <li key={id}>
                <div>
                  <strong>{produto?.nome ?? `Produto ${id}`}</strong>
                  <span className="suave">{reais((produto?.preco ?? 0) * quantidade)}</span>
                  {quantidade > maximo && (
                    <span className="texto-erro">Só há {maximo} em estoque agora</span>
                  )}
                </div>
                <div className="contador pequeno">
                  <button onClick={() => onAlterar(id, quantidade - 1)} aria-label={`Menos ${produto?.nome}`}>
                    −
                  </button>
                  <span>{quantidade}</span>
                  <button
                    onClick={() => onAlterar(id, quantidade + 1)}
                    disabled={quantidade >= maximo}
                    aria-label={`Mais ${produto?.nome}`}
                  >
                    +
                  </button>
                </div>
                <button className="link remover" onClick={() => onAlterar(id, 0)}>
                  Remover
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <div className="total">
        <span>Total</span>
        <strong>{reais(total)}</strong>
      </div>
      <button className="botao primario largo" disabled={linhas.length === 0 || enviando} onClick={onFinalizar}>
        {enviando ? "Enviando pedido…" : "Finalizar pedido"}
      </button>
      <p className="suave pequeno-texto">
        O pagamento abre em uma nova aba assim que o estoque for confirmado.
      </p>
    </aside>
  );
}
