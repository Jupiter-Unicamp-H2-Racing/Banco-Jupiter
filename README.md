# Banco Jupiter — Bootcamp Base API

API bancária desenvolvida em Python com FastAPI, PostgreSQL e SQLAlchemy.

O sistema permite cadastrar clientes, abrir contas, realizar transferências entre contas e consultar extratos.

## Funcionalidades

- **Clientes:** cadastro, consulta, listagem e atualização de status.
- **Contas:** abertura vinculada a clientes ativos e consulta de saldo.
- **Transferências:** movimentação entre contas com validação de saldo e cobrança de tarifas.
- **Extratos:** consulta paginada das transações, com filtros por período.
- **Idempotência:** permite reenviar uma transferência sem debitar o valor novamente, utilizando a mesma chave de idempotência.

### Regras principais

- Clientes começam com o status `pending_kyc`.
- Somente clientes ativos podem abrir contas.
- Transferências não podem ter valores menores que um centavo nem ocorrer para a própria conta.
- A conta de origem precisa ter saldo suficiente para cobrir a transferência e a tarifa.
- Os valores monetários são armazenados em centavos inteiros.
- Cada conta possui uma franquia mensal de transferências gratuitas, conforme as regras de tarifa implementadas.

## Tecnologias

- Python
- FastAPI
- PostgreSQL 16
- SQLAlchemy
- Docker e Docker Compose
- Pytest
- pytest-cov

## Como executar

### Pré-requisitos

- Git
- Docker
- Docker Compose

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd bootcamp-base-api
```

### 2. Configurar o ambiente

Antes de iniciar, configure um token interno. Gere um token aleatório e guarde-o em local seguro:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copie o token gerado para `INTERNAL_TOKEN` no arquivo `.env`. O arquivo `.env` não deve ser versionado. O Compose falha explicitamente se `INTERNAL_TOKEN` não estiver configurado.

### 3. Iniciar a aplicação

```bash
sudo docker compose up -d --build
```

Esse comando constrói as imagens necessárias e inicia a API e o banco de dados em segundo plano.

### 4. Verificar os serviços

```bash
sudo docker compose ps
```

A API fica disponível na porta `3000`, e o PostgreSQL utiliza a porta `5432` por padrão.

### 5. Verificar se a API está funcionando

```bash
curl -i http://localhost:3000/health_check
```

O endpoint de saúde retorna HTTP `204` quando a requisição é atendida com sucesso.

## Como executar os testes

**Os testes devem ser executados dentro do container da API**, utilizando os comandos abaixo na raiz do projeto, onde está o arquivo `docker-compose.yml`.

### 1. Construir a imagem da API

```bash
sudo docker compose build api
```

Esse comando constrói a imagem do serviço `api` utilizando a configuração do Docker Compose.

### 2. Iniciar ou recriar a API

```bash
sudo docker compose up -d --force-recreate api
```

Esse comando recria o container da API. O serviço de banco de dados também precisa estar disponível para os testes que dependem do PostgreSQL.

### 3. Executar todos os testes

```bash
sudo docker compose exec api python -m pytest /tests -v
```

Esse comando executa os testes encontrados em `/tests` dentro do container da API.

A opção `-v` exibe os nomes dos testes e seus respectivos resultados.

### 4. Executar os testes com cobertura de código

```bash
sudo docker compose exec api python -m pytest /tests --cov=/app --cov-report=term-missing
```

Esse comando executa os testes e apresenta um relatório de cobertura do código.

O relatório informa:
- A porcentagem de cobertura por arquivo.
- As linhas executadas durante os testes.
- As linhas que não foram cobertas.

### Resumo dos comandos

Execute os comandos na seguinte ordem:

```bash
sudo docker compose build api

sudo docker compose up -d --force-recreate api

sudo docker compose exec api python -m pytest /tests -v

sudo docker compose exec api python -m pytest /tests --cov=/app --cov-report=term-missing
```

**Importante:** os testes de integração podem apagar e recriar o schema do banco de dados. Não execute a suíte de testes em um banco que contenha dados importantes que você deseja preservar.

## Autenticação

Todas as rotas, exceto `GET /` e `GET /health_check`, exigem o cabeçalho HTTP `INTERNAL-TOKEN`, cujo valor deve corresponder à variável de ambiente `INTERNAL_TOKEN` configurada na API. Não existe token padrão no Docker Compose: a inicialização falha se a variável não estiver definida.

Gere um valor aleatório para cada ambiente. Em produção, não utilize os valores de exemplo do `.env.example`. O token interno autentica o chamador como serviço autorizado; ele **não** identifica individualmente um cliente e, portanto, não constitui autorização por cliente. Essa API continua adequada apenas a um contexto interno controlado enquanto não houver identidade e autorização por cliente.

## Principais rotas

| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Identificação do serviço |
| GET | `/health_check` | Verificação de saúde |
| POST | `/customers` | Cadastro de cliente |
| GET | `/customers` | Listagem de clientes |
| GET | `/customers/{customer_key}` | Consulta de cliente |
| PUT | `/customers/{customer_key}` | Atualização do status do cliente |
| POST | `/accounts` | Abertura de conta |
| GET | `/accounts/{account_key}` | Consulta de conta e saldo |
| POST | `/accounts/{account_key}/transactions` | Transferência entre contas |
| GET | `/accounts/{account_key}/transactions` | Consulta do extrato |

## Arquitetura

O projeto utiliza uma arquitetura em camadas para separar responsabilidades:

| Camada | Responsabilidade |
|---|---|
| `app.py` | Configuração da aplicação e das rotas |
| `middlewares/` | Autenticação, sessões e logs |
| `schemas/` | Validação do formato das entradas |
| `resources/` | Tratamento das requisições HTTP |
| `controllers/` | Regras de negócio |
| `repositories/` | Consultas e persistência no banco |
| `models/` | Modelos das tabelas |
| `dtos/` | Estrutura das respostas |
| `database/` | Schema e scripts SQL |

A separação em camadas facilita a manutenção, os testes e a evolução do sistema.

## Repositório público

Para a entrega de **13/10**, confirme que o repositório está público no GitHub.

Antes de entregar:

1. Verifique a visibilidade do repositório nas configurações do GitHub.
2. Acesse o repositório em uma janela anônima para confirmar que ele está público.
3. Confirme que arquivos com credenciais reais, como `.env`, não foram versionados.
4. Verifique se o README apresenta instruções suficientes para executar a aplicação e os testes.

O arquivo `.env.example` pode ser versionado desde que contenha apenas valores de exemplo, sem credenciais reais.


## Contrato HTTP e limitações de segurança

A atualização de status em `PUT /customers/{customer_key}` é síncrona e retorna `200 OK` com a representação do cliente. Erros de validação usam os códigos de erro documentados nos testes e nas classes de `src/errors/`.

A documentação interativa OpenAPI/Swagger/ReDoc permanece desabilitada na aplicação. Consulte a tabela de rotas e os schemas JSON em `src/schemas/` para os formatos de entrada; respostas e erros são definidos pelas resources, DTOs e handlers de erro.

O token interno é uma barreira entre serviços, não um login de cliente. Atualmente não há identidade individual de cliente nem autorização que vincule o chamador a uma conta específica. Não exponha esta API diretamente à internet como se fosse um sistema bancário de uso final.
