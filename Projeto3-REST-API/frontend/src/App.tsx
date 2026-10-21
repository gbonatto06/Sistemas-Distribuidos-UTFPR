import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "./api";
import type { Notificacao, Pedido, Produto } from "./api";
import { Carrinho } from "./components/Carrinho";
import { Catalogo } from "./components/Catalogo";
import { Identificacao } from "./components/Identificacao";
import { Pedidos } from "./components/Pedidos";
import { Promocoes } from "./components/Promocoes";
import { Toasts } from "./components/Toasts";
import { FINAIS, TONS } from "./status";
import { usePedidos, type EstadoConexao } from "./usePedidos";
import { useToasts } from "./useToasts";

type Aba = "catalogo" | "pedidos" | "promocoes";
const ABAS: { id: Aba; rotulo: string }[] = [
  { id: "catalogo", rotulo: "Catálogo" },
  { id: "pedidos", rotulo: "Meus pedidos" },
  { id: "promocoes", rotulo: "Promoções" },
];

// categorias de promocao (as mesmas do backend, comum/config.py)
const CATEGORIAS = ["A", "B", "C"];

const CHAVE_CLIENTE = "loja.cliente";

function lerCliente() {
  try {
    return localStorage.getItem(CHAVE_CLIENTE) ?? "";
  } catch {
    return "";
  }
}

function salvarCliente(cliente: string) {
  try {
    if (cliente) localStorage.setItem(CHAVE_CLIENTE, cliente);
    else localStorage.removeItem(CHAVE_CLIENTE);
  } catch {
    // sem storage o nome so nao sobrevive ao recarregar
  }
}

export default function App() {
  const [cliente, setCliente] = useState(lerCliente);

  function trocar(novo: string) {
    salvarCliente(novo);
    setCliente(novo);
  }

  if (!cliente) return <Identificacao onEntrar={trocar} />;
  // key: trocar de cliente recomeca do zero (carrinho, pedidos e conexao SSE)
  return <Loja key={cliente} cliente={cliente} onSair={() => trocar("")} />;
}

const TEXTO_CONEXAO: Record<EstadoConexao, string> = {
  conectando: "Conectando…",
  aberta: "Ao vivo",
  reconectando: "Reconectando…",
};

function Loja({ cliente, onSair }: { cliente: string; onSair: () => void }) {
  const [aba, irPara] = useState<Aba>("catalogo");
  const { toasts, avisar, fechar } = useToasts();

  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erroCatalogo, setErroCatalogo] = useState("");

  const [carrinho, setCarrinho] = useState<Record<string, number>>({});
  const [enviando, setEnviando] = useState(false);
  const [cancelando, setCancelando] = useState<string | null>(null);

  // abas de pagamento abertas no clique de "Finalizar", esperando a checkout_url
  const janelas = useRef(new Map<string, Window>());

  const carregarProdutos = useCallback(async () => {
    setCarregando(true);
    try {
      setProdutos(await api.listarProdutos());
      setErroCatalogo("");
    } catch (erro) {
      setErroCatalogo((erro as Error).message);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregarProdutos();
  }, [carregarProdutos]);

  /** Leva a aba reservada para o checkout, ou fecha se o pedido nao vai ser pago. */
  const conduzirJanela = useCallback((pedido: Pedido) => {
    const janela = janelas.current.get(pedido.pedido_id);
    if (!janela) return;
    if (janela.closed) {
      janelas.current.delete(pedido.pedido_id);
    } else if (pedido.status === "AGUARDANDO_PAGAMENTO" && pedido.checkout_url) {
      janela.location.href = pedido.checkout_url;
      janelas.current.delete(pedido.pedido_id);
    } else if (FINAIS.has(pedido.status)) {
      janela.close();
      janelas.current.delete(pedido.pedido_id);
    }
  }, []);

  const aoNotificar = useCallback(
    ({ pedido, mensagem }: Notificacao) => {
      avisar(TONS[pedido.status], `Pedido #${pedido.pedido_id}: ${mensagem}`, pedido.motivo || undefined);
      conduzirJanela(pedido);
      // reserva, devolucao e cancelamento mudam o saldo que o catalogo mostra
      void carregarProdutos();
    },
    [avisar, conduzirJanela, carregarProdutos],
  );

  const { pedidos, conexao, guardar, buscar } = usePedidos(cliente, aoNotificar);
  const emAndamento = pedidos.filter((p) => !FINAIS.has(p.status)).length;

  function alterarCarrinho(produtoId: string, quantidade: number) {
    setCarrinho((atual) => {
      const proximo = { ...atual };
      if (quantidade <= 0) delete proximo[produtoId];
      else proximo[produtoId] = quantidade;
      return proximo;
    });
  }

  async function finalizar() {
    // a aba precisa ser aberta AGORA, dentro do clique; aberta depois, quando a
    // URL chega pelo SSE, o navegador bloquearia como pop-up
    const janela = window.open("", "_blank");
    if (janela) {
      janela.document.title = "Preparando pagamento";
      janela.document.body.innerHTML =
        '<p style="font:16px system-ui,sans-serif;padding:40px;color:#667085">' +
        "Confirmando o estoque e preparando o pagamento…</p>";
    }

    setEnviando(true);
    try {
      const itens = Object.entries(carrinho).map(([produto_id, quantidade]) => ({ produto_id, quantidade }));
      const pedido = await api.criarPedido(cliente, itens);
      guardar(pedido);
      setCarrinho({});
      if (janela) {
        janelas.current.set(pedido.pedido_id, janela);
        // o SSE pode ter entregado a checkout_url antes desta resposta chegar
        conduzirJanela(buscar(pedido.pedido_id) ?? pedido);
      }
      avisar(
        "info",
        `Pedido #${pedido.pedido_id} criado`,
        janela
          ? "O pagamento abre na outra aba assim que o estoque for confirmado."
          : "Seu navegador bloqueou a nova aba: use o botão Pagar agora.",
      );
      irPara("pedidos");
    } catch (erro) {
      janela?.close();
      avisar("erro", "Não foi possível criar o pedido", (erro as Error).message);
      void carregarProdutos();
    } finally {
      setEnviando(false);
    }
  }

  async function cancelar(pedido: Pedido) {
    if (!window.confirm(`Cancelar o pedido #${pedido.pedido_id}?`)) return;
    setCancelando(pedido.pedido_id);
    try {
      guardar(await api.cancelarPedido(pedido.pedido_id, cliente));
    } catch (erro) {
      avisar("erro", "Não foi possível cancelar", (erro as Error).message);
    } finally {
      setCancelando(null);
    }
  }

  function pagar(pedido: Pedido) {
    if (pedido.checkout_url) window.open(pedido.checkout_url, "_blank");
  }

  return (
    <>
      <header className="topo">
        <div className="topo-conteudo">
          <span className="logo">Loja UTFPR</span>
          <nav className="abas" aria-label="Seções">
            {ABAS.map((a) => (
              <button
                key={a.id}
                className={`aba ${aba === a.id ? "ativa" : ""}`}
                aria-current={aba === a.id ? "page" : undefined}
                onClick={() => irPara(a.id)}
              >
                {a.rotulo}
                {a.id === "pedidos" && emAndamento > 0 && <span className="contagem">{emAndamento}</span>}
              </button>
            ))}
          </nav>
          <div className="usuario">
            <span className={`conexao ${conexao}`} title="Canal SSE de notificações">
              <span className="luz" aria-hidden="true" />
              {TEXTO_CONEXAO[conexao]}
            </span>
            <span className="nome">{cliente}</span>
            <button className="link" onClick={onSair}>
              Trocar
            </button>
          </div>
        </div>
      </header>

      <main className="conteudo">
        {aba === "catalogo" && (
          <div className="layout-loja">
            <Catalogo
              produtos={produtos}
              categorias={CATEGORIAS}
              carregando={carregando}
              erro={erroCatalogo}
              noCarrinho={carrinho}
              onAdicionar={(produto, quantidade) => {
                alterarCarrinho(produto.id, (carrinho[produto.id] ?? 0) + quantidade);
                avisar("neutro", `${quantidade}× ${produto.nome} no carrinho`);
              }}
              onRecarregar={carregarProdutos}
            />
            <Carrinho
              itens={carrinho}
              produtos={produtos}
              enviando={enviando}
              onAlterar={alterarCarrinho}
              onFinalizar={finalizar}
            />
          </div>
        )}
        {aba === "pedidos" && (
          <Pedidos
            pedidos={pedidos}
            cancelando={cancelando}
            onCancelar={cancelar}
            onPagar={pagar}
            onIrCatalogo={() => irPara("catalogo")}
          />
        )}
        {aba === "promocoes" && <Promocoes categorias={CATEGORIAS} produtos={produtos} avisar={avisar} />}
      </main>

      <Toasts toasts={toasts} onFechar={fechar} />
    </>
  );
}
