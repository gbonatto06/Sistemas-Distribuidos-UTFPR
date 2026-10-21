// Cliente REST do API Gateway (MS Principal)

export const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type Produto = {
  id: string;
  nome: string;
  preco: number;
  quantidade: number;
  categoria: string;
};

export type StatusPedido =
  | "CRIADO"
  | "ESTOQUE_OK"
  | "ESTOQUE_INDISPONIVEL"
  | "AGUARDANDO_PAGAMENTO"
  | "PAGAMENTO_APROVADO"
  | "PAGAMENTO_RECUSADO"
  | "PEDIDO_ENVIADO"
  | "EXCLUIDO";

export type ItemPedido = {
  produto_id: string;
  nome: string;
  preco: number;
  quantidade: number;
};

export type Pedido = {
  pedido_id: string;
  cliente: string;
  itens: ItemPedido[];
  total: number;
  status: StatusPedido;
  motivo: string;
  checkout_url: string | null;
  nota_fiscal: string | null;
  criado_em: string;
  atualizado_em: string;
  sequencia: number; // ordem de criacao no Gateway
  historico: { status: StatusPedido; em: string }[];
};

// o que chega em cada evento "pedido" do SSE
export type Notificacao = { pedido: Pedido; mensagem: string };

export type Inscricao = { email: string; categorias: string[]; acao: string };

export class ErroApi extends Error {
  constructor(mensagem: string, readonly status: number) {
    super(mensagem);
  }
}

function mensagemDeErro(corpo: unknown, status: number): string {
  const detalhe = (corpo as { detail?: unknown } | null)?.detail;
  if (typeof detalhe === "string") return detalhe;
  // erros de validacao do FastAPI: lista de {loc, msg}
  if (Array.isArray(detalhe)) {
    return detalhe
      .map((d) => String((d as { msg?: string }).msg ?? d).replace(/^Value error, /, ""))
      .join("; ");
  }
  return `Erro ${status}`;
}

async function requisitar<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(`${API_URL}${caminho}`, {
      ...init,
      headers: init.body ? { "content-type": "application/json" } : undefined,
    });
  } catch {
    throw new ErroApi("Não foi possível falar com o servidor", 0);
  }
  const corpo: unknown = await resposta.json().catch(() => null);
  if (!resposta.ok) throw new ErroApi(mensagemDeErro(corpo, resposta.status), resposta.status);
  return corpo as T;
}

export function listarProdutos() {
  // inclui os esgotados: o catalogo mostra o selo "Esgotado"
  return requisitar<Produto[]>("/produtos?disponiveis=false");
}

export function criarPedido(cliente: string, itens: { produto_id: string; quantidade: number }[]) {
  return requisitar<Pedido>("/pedidos", {
    method: "POST",
    body: JSON.stringify({ cliente, itens }),
  });
}

export function cancelarPedido(pedidoId: string, cliente: string) {
  const params = new URLSearchParams({ cliente });
  return requisitar<Pedido>(`/pedidos/${encodeURIComponent(pedidoId)}?${params}`, {
    method: "DELETE",
  });
}

export function inscrever(email: string, categorias: string[]) {
  return requisitar<Inscricao>("/interesses", {
    method: "POST",
    body: JSON.stringify({ email, categorias }),
  });
}

export function cancelarInscricao(email: string) {
  return requisitar<Inscricao>(`/interesses/${encodeURIComponent(email)}`, { method: "DELETE" });
}

export function urlEventos(cliente: string) {
  return `${API_URL}/eventos?${new URLSearchParams({ cliente })}`;
}
