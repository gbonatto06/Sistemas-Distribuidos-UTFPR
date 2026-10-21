// Pedidos do cliente, mantidos ao vivo pelo canal SSE do Gateway.
//
// Ao conectar, o Gateway manda um evento "pedidos" com a lista inteira; depois,
// um evento "pedido" a cada mudanca de status. O EventSource reconecta sozinho
// se a conexao cair, e a lista inicial da reconexao cobre o que se perdeu.

import { useCallback, useEffect, useRef, useState } from "react";
import { urlEventos, type Notificacao, type Pedido } from "./api";

export type EstadoConexao = "conectando" | "aberta" | "reconectando";

// A resposta do POST /pedidos pode chegar DEPOIS do primeiro evento SSE do mesmo
// pedido. Cada mudanca acrescenta uma entrada no historico, entao a versao com o
// historico mais longo e a mais nova.
function maisNovo(atual: Pedido | undefined, chegou: Pedido) {
  return !atual || chegou.historico.length >= atual.historico.length ? chegou : atual;
}

export function usePedidos(cliente: string, aoNotificar: (n: Notificacao) => void) {
  const [pedidos, setPedidos] = useState<Record<string, Pedido>>({});
  const [conexao, setConexao] = useState<EstadoConexao>("conectando");
  // copia sincrona do estado, para quem precisa ler fora do ciclo do React
  const atuais = useRef<Record<string, Pedido>>({});
  const notificar = useRef(aoNotificar);
  notificar.current = aoNotificar;

  const guardar = useCallback((lista: Pedido[]) => {
    const proximo = { ...atuais.current };
    for (const pedido of lista) proximo[pedido.pedido_id] = maisNovo(proximo[pedido.pedido_id], pedido);
    atuais.current = proximo;
    setPedidos(proximo);
  }, []);

  useEffect(() => {
    atuais.current = {};
    setPedidos({});
    setConexao("conectando");

    const fonte = new EventSource(urlEventos(cliente));
    fonte.onopen = () => setConexao("aberta");
    fonte.onerror = () => setConexao("reconectando");

    fonte.addEventListener("pedidos", (evento) => {
      guardar(JSON.parse((evento as MessageEvent<string>).data) as Pedido[]);
    });
    fonte.addEventListener("pedido", (evento) => {
      const notificacao = JSON.parse((evento as MessageEvent<string>).data) as Notificacao;
      guardar([notificacao.pedido]);
      notificar.current(notificacao);
    });
    return () => fonte.close();
  }, [cliente, guardar]);

  const lista = Object.values(pedidos).sort((a, b) => b.sequencia - a.sequencia);

  return {
    pedidos: lista,
    conexao,
    guardar: (pedido: Pedido) => guardar([pedido]),
    buscar: (pedidoId: string): Pedido | undefined => atuais.current[pedidoId],
  };
}
