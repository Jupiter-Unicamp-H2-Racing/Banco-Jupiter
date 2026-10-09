# Banco Jupiter

API bancária desenvolvida em Python com FastAPI, PostgreSQL e SQLAlchemy, organizada em camadas para facilitar a manutenção, a evolução e a implementação de funcionalidades financeiras.

## Tecnologias

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Docker
- Docker Compose
- Pydantic
- Pytest

## Funcionalidades

- Gerenciamento de contas bancárias.
- Operações de transação entre contas.
- Validação de dados e regras de negócio.
- Persistência de dados utilizando PostgreSQL.
- Cobrança de tarifas por transação, conforme as regras de negócio implementadas.
- Execução da aplicação em ambiente conteinerizado com Docker.

## Arquitetura

O projeto segue uma organização em camadas, separando as responsabilidades da aplicação.

- **API / Routes:** definição dos endpoints e tratamento das requisições HTTP.
- **Entities / Models:** representação das entidades e dos dados persistidos.
- **Schemas:** validação e serialização dos dados de entrada e saída.
- **Services:** implementação das regras de negócio.
- **Repositories:** acesso e manipulação dos dados no banco.
- **Database:** configuração da conexão e da persistência.

A estrutura exata depende dos módulos presentes no código-fonte.

## Requisitos

Para executar o projeto, você precisará de:

- Git
- Docker
- Docker Compose

Para execução sem Docker, também será necessário instalar uma versão compatível do Python e configurar o PostgreSQL.

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/Jupiter-Unicamp-H2-Racing/Banco-Jupiter.git
```

### 2. Acesse a pasta do projeto

```bash
cd Banco-Jupiter
```

### 3. Configure as variáveis de ambiente

Verifique se o projeto possui um arquivo `.env.example` ou instruções específicas para configurar as variáveis de ambiente.

Se existir um `.env.example`, execute:

```bash
cp .env.example .env
```

Configure as variáveis necessárias para a conexão com o banco de dados e para a execução da aplicação.

**Importante:** não compartilhe senhas, tokens ou credenciais reais no repositório.

## Executando com Docker

A maneira recomendada de executar o projeto é utilizando Docker Compose.

### 1. Verifique os arquivos de configuração

Na raiz do projeto, execute:

```bash
ls -la
```

Verifique a existência de um dos seguintes arquivos:

- `compose.yaml`
- `compose.yml`
- `docker-compose.yml`
- `docker-compose.yaml`

### 2. Construa e inicie os serviços

Se o arquivo de configuração estiver na raiz do projeto:

```bash
docker compose up --build -d
```

Esse comando constrói as imagens necessárias e inicia os serviços em segundo plano.

### 3. Verifique os containers

```bash
docker compose ps
```

Confira se os serviços estão em execução.

### 4. Consulte os logs

```bash
docker compose logs -f
```

Para acompanhar apenas os logs da API, caso o serviço se chame `api`:

```bash
docker compose logs -f api
```

Para sair da visualização dos logs, pressione `Ctrl + C`.

### 5. Acesse a documentação da API

Se a aplicação estiver publicada na porta `8000`, acesse:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

A documentação interativa permite consultar os endpoints, visualizar os parâmetros e executar requisições HTTP.

Os endereços acima pressupõem que a porta `8000` esteja publicada e que a documentação esteja habilitada.

### 6. Encerre os serviços

Para parar e remover os containers da aplicação:

```bash
docker compose down
```

Esse comando não remove os volumes por padrão.

**Atenção:** evite utilizar `docker compose down -v` em ambientes com dados importantes, pois isso pode remover volumes e apagar dados persistidos.

## Executando os testes

Os testes verificam o comportamento da aplicação e ajudam a identificar regressões após alterações no código.

### 1. Verifique a configuração de testes

Na raiz do projeto, procure os arquivos e diretórios relacionados aos testes:

```bash
find . -maxdepth 3 \( -name "test_*.py" -o -name "*_test.py" -o -name "pytest.ini" -o -name "pyproject.toml" \)
```

Verifique também se o projeto possui dependências de desenvolvimento ou um arquivo `requirements.txt`.

### 2. Execute os testes com Docker

Se o projeto possuir um serviço `api` com as dependências necessárias para executar os testes, tente:

```bash
docker compose exec api pytest
```

Esse comando executa o Pytest dentro do container da API.

Se o Pytest não estiver instalado no container, será necessário instalar as dependências de teste ou utilizar um ambiente apropriado para desenvolvimento.

Caso o serviço não esteja em execução, verifique a configuração do Docker Compose antes de continuar.

### 3. Execute os testes localmente

Para executar os testes fora do Docker, crie um ambiente virtual Python:

```bash
python3 -m venv .venv
```

Ative o ambiente virtual no Linux:

```bash
source .venv/bin/activate
```

Instale as dependências do projeto:

```bash
pip install -r requirements.txt
```

Se o Pytest fizer parte das dependências do projeto, execute:

```bash
pytest
```

Para obter mais detalhes sobre os testes executados:

```bash
pytest -v
```

Para executar um arquivo de teste específico:

```bash
pytest caminho/para/test_arquivo.py -v
```

Substitua o caminho pelo arquivo de teste existente no projeto.

**Observação:** os testes podem exigir uma instância do PostgreSQL e variáveis de ambiente específicas. Consulte a configuração de testes antes de executá-los.

## Desenvolvimento

Para contribuir com o projeto:

1. Crie uma branch para sua alteração.
2. Implemente a funcionalidade seguindo a arquitetura existente.
3. Execute os testes disponíveis.
4. Revise as alterações antes de enviá-las.
5. Abra um Pull Request para revisão.

## Repositório

GitHub: https://github.com/Jupiter-Unicamp-H2-Racing/Banco-Jupiter

## Licença

Consulte os arquivos do repositório para verificar os termos de licença aplicáveis.
