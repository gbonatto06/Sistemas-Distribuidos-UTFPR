# Cada imagem leva apenas comum/ e o codigo do proprio servico.
FROM python:3.12-slim

# SERVICO nomeia um microsservico (servico_<nome>); PACOTE permite apontar para um
# pacote fora desse padrao que nao e microsservico
ARG SERVICO
ARG PACOTE=servico_${SERVICO}
ENV PACOTE=${PACOTE} \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY comum/ comum/
COPY ${PACOTE}/ ${PACOTE}/

# sh -c porque o nome do modulo vem da variavel de ambiente
CMD ["sh", "-c", "python -m ${PACOTE}.main"]
