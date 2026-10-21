import sqlite3
from contextlib import contextmanager

# conecta com o banco de dados SQLite, com timeout de 10 segundos e sem isolamento de transacao
def conectar(caminho):
    conexao = sqlite3.connect(caminho, timeout=10, isolation_level=None)
    conexao.row_factory = sqlite3.Row
    return conexao


@contextmanager
def transacao(caminho):
    # abre uma transacao, com commit no final, ou rollback se der erro. 
    # Fechando a conexao no final.
    conexao = conectar(caminho)
    try:
        # se tiver no begin, o sqlite bloqueia o banco para escrita. 
        # evitando que outro processo leia o mesmo tempo e mesmo dado.
        conexao.execute("BEGIN IMMEDIATE")
        yield conexao
        conexao.execute("COMMIT")
    except BaseException:
        conexao.execute("ROLLBACK")
        raise
    finally:
        conexao.close()


@contextmanager
def leitura(caminho):
    # abre uma conexao para leitura, com commit no final. Fechando a conexao no final.
    conexao = conectar(caminho)
    try:
        yield conexao
    finally:
        conexao.close()


def criar_esquema(caminho, esquema):
    # cria o banco de dados e o esquema, se nao existir. Cria o diretorio pai do arquivo, se necessario.
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with transacao(caminho) as conexao:
        for comando in filter(str.strip, esquema.split(";")):
            conexao.execute(comando)
