import { useCallback, useState } from "react";
import type { Tom } from "./status";

export type Toast = { id: number; tom: Tom; titulo: string; detalhe?: string };

const DURACAO_MS = 6000;
let proximoId = 1;

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const fechar = useCallback((id: number) => {
    setToasts((lista) => lista.filter((t) => t.id !== id));
  }, []);

  const avisar = useCallback(
    (tom: Tom, titulo: string, detalhe?: string) => {
      const id = proximoId++;
      // no maximo 4 na tela: o mais antigo sai
      setToasts((lista) => [...lista.slice(-3), { id, tom, titulo, detalhe }]);
      window.setTimeout(() => fechar(id), DURACAO_MS);
    },
    [fechar],
  );

  return { toasts, avisar, fechar };
}
