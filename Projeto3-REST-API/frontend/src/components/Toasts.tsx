import type { Toast } from "../useToasts";

export function Toasts({ toasts, onFechar }: { toasts: Toast[]; onFechar: (id: number) => void }) {
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast tom-${t.tom}`} role="status">
          <div>
            <strong>{t.titulo}</strong>
            {t.detalhe && <p>{t.detalhe}</p>}
          </div>
          <button className="fechar" onClick={() => onFechar(t.id)} aria-label="Fechar">
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
