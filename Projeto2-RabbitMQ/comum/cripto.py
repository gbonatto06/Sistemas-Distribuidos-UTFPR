# lib para assinar e verificar eventos, usando chaves ssh
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization

from comum.config import CHAVES_PUBLICAS, caminho_chave_privada

# regex para validar nomes de servico: apenas minusculas, numeros e underscore
_NOME_SERVICO = re.compile(r"^[a-z0-9_]+$")

# le a chave privada do servico e retorna um objeto de chave privada
def chave_privada(servico):
    return serialization.load_ssh_private_key(
        caminho_chave_privada(servico).read_bytes(), password=None
    )

# le a chave publica do produtor e retorna um objeto de chave publica
def chave_publica(produtor):
    if not isinstance(produtor, str) or not _NOME_SERVICO.match(produtor):
        raise ValueError(f"nome de produtor invalido: {produtor!r}")
    return serialization.load_ssh_public_key(
        (CHAVES_PUBLICAS / f"{produtor}.pub").read_bytes()
    )

# utilizando a chave privada do servico, assina o conteudo e retorna o hash da assinatura
def assinar_conteudo(servico, conteudo):
    return chave_privada(servico).sign(conteudo.encode("utf-8")).hex()


def verificar(produtor, conteudo, assinatura_hex):
    "verifica a assinatura do conteudo com a chave publica do produtor"
    try:
        chave_publica(produtor).verify(
            bytes.fromhex(assinatura_hex), conteudo.encode("utf-8")
        )
        return True
    except (InvalidSignature, ValueError, KeyError, FileNotFoundError):
        return False
