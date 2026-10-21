# microservico principal: API Gateway 
import uvicorn

from comum.config import PRINCIPAL_PORTA
from servico_principal.api import app

# sobe o microserviço principal (API Gateway)
def main():
    print(f"[principal] HTTP em :{PRINCIPAL_PORTA}  (docs em /docs, Ctrl+C para encerrar)")
    uvicorn.run(app, host="0.0.0.0", port=PRINCIPAL_PORTA)
    print("[principal] encerrado")


if __name__ == "__main__":
    main()
