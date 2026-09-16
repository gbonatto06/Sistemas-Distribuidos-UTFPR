# script para gerar as chaves ssh de cada servico

import stat
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

SERVICOS = ["principal", "estoque", "pagamento", "entrega", "promocoes"]

RAIZ = Path(__file__).resolve().parent.parent
DIR_PRIVADAS = RAIZ / "chaves" / "privadas"
DIR_PUBLICAS = RAIZ / "chaves" / "publicas"


def gerar(servico):
    # define o caminho da chave privada e publica do servico
    privada = DIR_PRIVADAS / servico
    publica = DIR_PUBLICAS / f"{servico}.pub"
    if privada.exists():
        return False

    chave = Ed25519PrivateKey.generate()
    privada.write_bytes(
        chave.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    # So o dono le a chave privada 
    privada.chmod(stat.S_IRUSR | stat.S_IWUSR)
    publica.write_bytes(
        chave.public_key().public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        )
    )
    return True


def main():
    DIR_PRIVADAS.mkdir(parents=True, exist_ok=True)
    DIR_PUBLICAS.mkdir(parents=True, exist_ok=True)

    for servico in SERVICOS:
        if gerar(servico):
            print(f"gerado : {servico}")
        else:
            print(f"ja tem : {servico}")

    print(f"\nprivadas em {DIR_PRIVADAS}")
    print(f"publicas em {DIR_PUBLICAS}  (o keyring, montado read-only nos containers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
