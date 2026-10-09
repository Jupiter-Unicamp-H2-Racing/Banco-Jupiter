# Imagem oficial do Python
FROM python:3.11-slim AS base

# Usuario sem privilegios para executar a aplicacao
RUN adduser --system --no-create-home user

# Ambiente virtual Python
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Dependencias principais da aplicacao
COPY requirements.txt /requirements.txt

RUN pip install --upgrade pip \
    && pip install -r /requirements.txt

# Codigo da aplicacao
WORKDIR /app
COPY src /app

# Imagem da API com dependencias de desenvolvimento e testes
FROM base AS api

# Instala pytest durante o build, enquanto ainda temos permissao de root
COPY requirements-dev.txt /requirements-dev.txt

RUN pip install -r /requirements-dev.txt

# Copia os testes para dentro do container
COPY tests /tests

# Configura o diretorio de trabalho dos testes
ENV PYTHONPATH=/app:/

# Permite que o usuario da aplicacao acesse os arquivos
RUN chown -R user /app /tests

ENV COVERAGE_FILE=/tmp/.coverage

COPY database /database

# Executa a aplicacao sem privilegios de root
USER user

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000", "--no-server-header"]
