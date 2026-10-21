import type { Pedido } from "../api";
import { CANCELAVEIS, ROTULOS, TONS, dataCurta, etapas, reais } from "../status";

type Props = {
  pedidos: Pedido[];
  cancelando: string | null;
  onCancelar: (pedido: Pedido) => void;
  onPagar: (pedido: Pedido) => void;
  onIrCatalogo: () => void;
};

export function Pedidos({ pedidos, cancelando, onCancelar, onPagar, onIrCatalogo }: Props) {
  if (pedidos.length === 0) {
    return (
      <section className="cartao vazio">
        <h2>Nenhum pedido ainda</h2>
        <p className="suave">Os seus pedidos aparecem aqui e são atualizados em tempo real.</p>
        <button className="botao primario" onClick={onIrCatalogo}>
          Ver catálogo
        </button>
      </section>
    );
  }

  return (
    <section className="lista-pedidos" aria-label="Meus pedidos">
      {pedidos.map((pedido) => (
        <CartaoPedido
          key={pedido.pedido_id}
          pedido={pedido}
          cancelando={cancelando === pedido.pedido_id}
          onCancelar={onCancelar}
          onPagar={onPagar}
        />
      ))}
    </section>
  );
}

function CartaoPedido({
  pedido,
  cancelando,
  onCancelar,
  onPagar,
}: {
  pedido: Pedido;
  cancelando: boolean;
  onCancelar: (pedido: Pedido) => void;
  onPagar: (pedido: Pedido) => void;
}) {
  const podePagar = pedido.status === "AGUARDANDO_PAGAMENTO" && pedido.checkout_url;
  const podeCancelar = CANCELAVEIS.has(pedido.status);

  return (
    <article className="cartao pedido">
      <header className="pedido-topo">
        <div>
          <h3>Pedido #{pedido.pedido_id}</h3>
          <p className="suave">
            {dataCurta(pedido.criado_em)} · {reais(pedido.total)}
          </p>
        </div>
        <span className={`status tom-${TONS[pedido.status]}`}>{ROTULOS[pedido.status]}</span>
      </header>

      <ol className="etapas">
        {etapas(pedido).map((etapa) => (
          <li key={etapa.rotulo} className={`etapa ${etapa.estado}`}>
            <span className="ponto" aria-hidden="true" />
            <span>{etapa.rotulo}</span>
          </li>
        ))}
      </ol>

      {pedido.motivo && <p className="aviso erro">{pedido.motivo}</p>}
      {pedido.nota_fiscal && (
        <p className="aviso sucesso">
          Nota fiscal <strong>{pedido.nota_fiscal}</strong> emitida, pedido despachado.
        </p>
      )}

      <ul className="itens">
        {pedido.itens.map((item) => (
          <li key={item.produto_id}>
            <span>
              {item.quantidade}× {item.nome}
            </span>
            <span className="suave">{reais(item.preco * item.quantidade)}</span>
          </li>
        ))}
      </ul>

      {(podePagar || podeCancelar) && (
        <footer className="pedido-acoes">
          {podePagar && (
            <button className="botao primario" onClick={() => onPagar(pedido)}>
              Pagar agora
            </button>
          )}
          {podeCancelar && (
            <button className="botao perigo" onClick={() => onCancelar(pedido)} disabled={cancelando}>
              {cancelando ? "Cancelando…" : "Cancelar pedido"}
            </button>
          )}
        </footer>
      )}
    </article>
  );
}
