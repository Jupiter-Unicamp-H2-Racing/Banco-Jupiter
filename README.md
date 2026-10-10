# Banco Jupiter (bootcamp-base-api)

API bancária mínima em Python (FastAPI + PostgreSQL + SQLAlchemy). Cadastra **clientes**, abre **contas** vinculadas a clientes ativos, move dinheiro entre contas com **transações** que respeitam saldo e **tarifa**, e devolve o **extrato** paginado de cada conta.

> **Aviso de entrega (13/10):** o repositório precisa estar **público** na entrega. Veja o [checklist](#entrega-repositório-público-em-1310) no fim deste arquivo.

## Sumário

- [O que o sistema faz](#o-que-o-sistema-faz)
- [Como subir](#como-subir)
- [Autenticação e variáveis de ambiente](#autenticação-e-variáveis-de-ambiente)
- [Rotas](#rotas)
- [Como testar](#como-testar)
- [Camadas](#camadas)
- [Decisões de modelagem](#decisões-de-modelagem)
- [Entrega: repositório público em 13/10](#entrega-repositório-público-em-1310)

## O que o sistema faz

| Conceito | Regra |
|---|---|
| **Cliente** | Nasce em `pending_kyc`. Exige CPF válido (dígitos verificadores), e-mail e CPF únicos, idade entre 18 e 80 anos. O status só pode sair de `pending_kyc` **uma vez**, para `active`, `blocked` ou `inactive`; depois disso é final (`409`). |
| **Conta** | Sempre vinculada a um cliente, e só clientes `active` abrem conta (`422` caso contrário). Pode nascer com `initial_balance` (padrão `0`). |
| **Transação** | Transferência de uma conta de origem para outra de destino. A origem paga `amount + tarifa`, o destino recebe só `amount`. Rejeita saldo insuficiente, conta inexistente e transferência para a própria conta. |
| **Extrato** | Lista paginada das transações em que a conta é origem (`debit`) ou destino (`credit`), da mais nova para a mais antiga, com filtro opcional por período. |

Todo valor monetário é **inteiro em centavos**: `10000` = R$ 100,00.

### Regra da tarifa

1. Cada conta tem uma **franquia mensal** de transferências gratuitas (`monthly_free_transfers_limit`, padrão **5**).
2. A contagem considera as transferências em que a conta foi **origem** no **mês-calendário UTC** corrente, lidas da tabela `transaction` (a virada do mês é automática, não há contador para zerar).
3. Dentro da franquia: tarifa **0**.
4. Esgotada a franquia: tarifa de **50 centavos (R$ 0,50)**, **exceto** se o saldo da origem *imediatamente antes* da transferência for **≥ 100000 centavos (R$ 1.000,00)**; nesse caso a tarifa é 0.
5. A origem precisa ter `saldo >= amount + tarifa`; senão, `422` (`QIT002002`).
6. A tarifa cobrada (inclusive `0`) fica gravada em `transaction.fee_amount`. Ela é descontada da origem e **não é creditada a nenhuma conta**.

A regra mora em `src/utils/transaction_fee.py`; o detalhe está em `docs/transaction-fee.md`.

## Como subir

Pré-requisitos: Git e Docker com Compose.

```bash
git clone <url-do-repositório>
cd bootcamp-base-api
docker compose up
```

Não é preciso criar `.env`: todo valor tem padrão no próprio `docker-compose.yml`. O comando sobe dois serviços:

| Serviço | Porta (host) | Observação |
|---|---|---|
| `api` | **3000** | uvicorn com `--reload` (o `./src` é montado no container). Só inicia depois que o banco fica saudável. |
| `db` | 5432 | PostgreSQL 16; `database/database.sql` roda na criação do banco. Usuário/senha/banco: `bootcamp`. |

Espere o `api` ficar `healthy` (`docker compose ps`) e confirme:

```bash
curl -i http://localhost:3000/health_check    # HTTP 204, sem corpo
curl http://localhost:3000/                    # {"service":"bootcamp-api","id":"<pid>"}
```

Porta ocupada (`port is already allocated`)? Crie um `.env` (copie o `.env.example`) e descomente `API_PORT` e/ou `DB_PORT`.

> **Não existe Swagger/ReDoc.** `src/app.py` cria o FastAPI com `docs_url=None`, `redoc_url=None` e `openapi_url=None`. `/docs` responde `404`. O contrato de entrada está em `src/schemas/*.json`.

## Autenticação e variáveis de ambiente

Toda rota, **exceto `GET /` e `GET /health_check`**, exige o header:

```
INTERNAL-TOKEN: default_token
```

O valor esperado vem da variável `INTERNAL_TOKEN`. Sem o header, ou com valor errado, a resposta é `403` com código `QIT000002`. O middleware roda antes do roteamento: até uma rota inexistente responde `403` sem token (e `404` com token).

Variáveis do `.env.example`:

| Variável | Padrão | Para que serve |
|---|---|---|
| `APP_ENV` | `local` | `local`/`test`/`production`. Muda o nível do log (`DEBUG` aparece em `local` e `test`). |
| `SERVICE_NAME` | `bootcamp-api` | Nome do serviço, exibido no log e em `GET /`. |
| `DATABASE_URL` | `postgresql+psycopg2://bootcamp:bootcamp@localhost:5432/bootcamp` | Conexão com o banco, usada **fora** do Docker (testes, acesso direto). Dentro do compose a API usa `...@db:5432/...` e ignora este valor. **Obrigatória.** |
| `INTERNAL_TOKEN` | `default_token` | Valor aceito no header `INTERNAL-TOKEN`. **Obrigatória.** A API não sobe sem ela. |
| `SERVER_LOCALHOST` | `0.0.0.0` | Host onde os testes procuram a API. |
| `BANKSLIP_API_URL` | `http://localhost:8080` | Endereço da API de boletos (connector em `src/connectors/`). |
| `BANKSLIP_API_INTERNAL_TOKEN` | `default_token` | Token que a API de boletos exige. |
| `BANKSLIP_API_TIMEOUT` | `5` | Segundos de espera pela API de boletos. |
| `API_PORT` | `3000` (comentada) | Porta da API na sua máquina; os testes também a leem. |
| `DB_PORT` | `5432` (comentada) | Porta do banco na sua máquina. |

> O `.env` nunca vai para o Git (está no `.gitignore`); só o `.env.example`, que contém apenas valores de exemplo.

## Rotas

Todos os exemplos assumem a API em `localhost:3000`. Defina uma vez:

```bash
H='INTERNAL-TOKEN: default_token'
J='Content-Type: application/json'
B=http://localhost:3000
```

| Método | Rota | Sucesso | Função |
|---|---|---|---|
| GET | `/` | 200 | Identifica o serviço (pública) |
| GET | `/health_check` | 204 | Saúde (pública) |
| POST | `/customers` | 201 | Cadastra cliente em `pending_kyc` |
| GET | `/customers` | 200 | Lista paginada com filtros |
| GET | `/customers/{customer_key}` | 200 | Detalhe + histórico de status |
| PUT | `/customers/{customer_key}` | 202 | Define o status (só a partir de `pending_kyc`) |
| POST | `/accounts` | 201 | Abre conta para cliente ativo |
| GET | `/accounts/{account_key}` | 200 | Saldo e dono da conta |
| POST | `/accounts/{account_key}/transactions` | 201 | Transfere da conta da URL para outra |
| GET | `/accounts/{account_key}/transactions` | 200 | Extrato paginado |

Erros têm sempre o formato `{"title","description","translation","code"}`.

### Clientes

```bash
# Cadastrar (201 -> {"customer_key": "..."})
curl -X POST $B/customers -H "$H" -H "$J" \
  -d '{"name":"Maria Silva","email":"maria@example.com","document_number":"529.982.247-25","birthdate":"1990-05-20"}'

# Ativar (202). Troque <customer_key> pela chave devolvida acima
curl -X PUT $B/customers/<customer_key> -H "$H" -H "$J" -d '{"status":"active"}'

# Detalhe (200): inclui status_events, o histórico de mudanças de status
curl $B/customers/<customer_key> -H "$H"

# Listar (200). Filtros: status (repetível), name, email, document_number,
# birthdate_from, birthdate_to; limit (1-100, padrão 10) e page (padrão 1)
curl "$B/customers?status=active&limit=10&page=1" -H "$H"
```

Resposta da listagem: `{"data":[...],"limit":10,"page":1,"is_last_page":false}`.

### Contas

```bash
# Abrir conta com R$ 5.000,00 (201 -> {"account_key": "..."}); initial_balance é opcional
curl -X POST $B/accounts -H "$H" -H "$J" \
  -d '{"customer_key":"<customer_key>","initial_balance":500000}'

# Consultar (200 -> account_key, balance em centavos, customer_key, tier)
curl $B/accounts/<account_key> -H "$H"
```

### Transações e extrato

```bash
# Transferir R$ 100,00 (201)
curl -X POST $B/accounts/<conta_origem>/transactions -H "$H" -H "$J" \
  -d '{"destination_account_key":"<conta_destino>","amount":10000}'
# -> {"transaction_key":"...","amount":10000,"fee_amount":0,"is_fee_exempt":true}

# Extrato (200). Parâmetros opcionais: limit (1-100, padrão 20), page (padrão 1),
# start_date e end_date (YYYY-MM-DD, UTC, ambas inclusivas)
curl "$B/accounts/<account_key>/transactions?limit=20&page=1&start_date=2026-10-01&end_date=2026-10-31" -H "$H"
# -> {"items":[{"transaction_key","direction":"debit|credit","amount","fee_amount",
#               "counterparty_account_key","created_at"}],
#     "pagination":{"total_items":6,"page":1,"limit":20}}
```

No extrato, `fee_amount` só aparece diferente de zero em `debit`; o `credit` mostra sempre `0`.

### Erros mais comuns

| HTTP | Código | Quando |
|---|---|---|
| 400 | `QIT000001` | Corpo ou query fora do schema (ex.: `amount` decimal, `limit=101`) |
| 400 | `QIT000010` | `birthdate_from` depois de `birthdate_to` |
| 403 | `QIT000002` | Header `INTERNAL-TOKEN` ausente ou errado |
| 404 | `QIT001001` / `QIT002001` | Cliente / conta não encontrado |
| 404 | `QIT000404` | Rota inexistente (inclui `/docs`) |
| 409 | `QIT001002` | Cliente já saiu de `pending_kyc` |
| 409 | `QIT001004` / `QIT001005` | CPF / e-mail já cadastrado |
| 422 | `QIT001003` | CPF com formato válido, mas inexistente |
| 422 | `QIT001006` / `QIT001008` | Menor de 18 / maior de 80 anos |
| 422 | `QIT001009` | Cliente não está `active` ao abrir conta |
| 422 | `QIT002002` | Saldo insuficiente para `amount + tarifa` |
| 422 | `QIT002003` | Transferência para a própria conta |
| 422 | `QIT002004` / `QIT002005` | Data de extrato inexistente / `start_date` > `end_date` |

## Como testar

Os testes rodam **na sua máquina**, contra a API e o banco que o `docker compose up` colocou de pé.

```bash
docker compose up -d                 # em um terminal: API e banco de pé
pip install -r requirements-dev.txt  # Python 3.11+
PYTHONPATH=src:. pytest              # a partir da raiz do projeto
```

- `PYTHONPATH=src:.` é necessário: os testes importam os módulos de `src/` (`controllers`, `database`...) e `tests.*`. Um `pytest` puro falha na coleta com `ModuleNotFoundError: No module named 'controllers'`.
- Última execução: **84 testes passando** (30 unitários + 54 de integração).
- Só os unitários (não usam API nem banco): `PYTHONPATH=src:. pytest tests/unit`.
- Só os de integração (marcados `integration`): `PYTHONPATH=src:. pytest tests/integration`.
- Os testes encontram a API em `SERVER_LOCALHOST:API_PORT` (`0.0.0.0:3000`) e o banco em `DATABASE_URL`, e usam o token padrão. Se mudou porta ou token, exporte as mesmas variáveis antes de rodar.

> **Atenção: os testes de integração apagam o banco.** Testes como os de `test_customers.py` e `test_transaction_statement.py` chamam `DbUtils.rollback()`, que faz `DROP SCHEMA public CASCADE` e reaplica `database/database.sql`; como todos dividem o mesmo banco, rodar a suíte apaga o que você tinha criado à mão. Nunca aponte `DATABASE_URL` para um banco com dados que você queira manter.

## Camadas

Dentro de `src/`. A requisição atravessa as camadas na ordem em que aparecem abaixo.

| Camada | Decide |
|---|---|
| **`app.py`** | Monta a aplicação: a **ordem dos middlewares**, qual endereço aponta para qual método de resource, e que a documentação interativa fica desligada. Valida as variáveis obrigatórias na subida. |
| **`middlewares/`** | O que acontece em **toda** requisição, antes e depois da rota: `internal_token` (quem pode entrar), `session_manager` (a sessão de banco nasce no começo e sofre `rollback`/`close` no fim, **nunca `commit`**), `request_logger` (log de entrada/saída) e `request_context` (o `request_id` que acompanha o log). |
| **`schemas/`** | Se o **formato** do que chegou é aceitável. Arquivos JSON Schema (corpo dos `POST`/`PUT` e query strings dos `GET`), aplicados pelo `utils/schema_handler.py`. Falha vira `400 QIT000001`. |
| **`resources/`** | A tradução **HTTP ↔ aplicação**: valida a entrada pelo schema, chama o controller e escolhe o status de sucesso (201, 202...). Não tem regra de negócio. |
| **`controllers/`** | As **regras de negócio** (idade, CPF, status final, saldo, tarifa) e a **fronteira da transação de banco**: são o único lugar que dá `commit`, na última linha antes do `return`. Cada controller abre o contexto de banco ao ser construído. |
| **`repositories/`** | **Como** os dados são lidos e gravados: toda consulta SQLAlchemy mora aqui, inclusive o `SELECT ... FOR UPDATE`. Não decide regra, só busca e persiste. |
| **`models/`** | O formato das **tabelas** no SQLAlchemy: colunas, chaves e `CHECK` constraints (saldo ≥ 0, valor > 0, origem ≠ destino). |
| **`dtos/`** | O formato da **saída**: o que de cada entidade sai na resposta JSON (por exemplo, `AccountDTO` não expõe IDs internos). |
| **`database/database.sql`** | O **schema inicial** (tabelas, constraints, índices e os quatro status de cliente). Roda quando o container do banco é criado. |

Apoio: `errors/` (exceções com código e tradução, mais o tradutor erro → JSON), `utils/` (`transaction_fee.py`, `document_number.py`, `schema_handler.py`, logger), `database/migrations/` (migrações aditivas **para bancos que já existem**, aplicadas manualmente com `psql`; instalações novas não precisam delas) e `connectors/` (cliente HTTP da API de boletos; nenhuma rota atual o usa).

## Decisões de modelagem

**Dinheiro em centavos, `BIGINT`.** `balance`, `amount` e `fee_amount` são inteiros. Não há ponto flutuante em nenhum ponto do caminho: o schema JSON recusa `amount` decimal (`1.5` → `400`) e exige `amount >= 1`. Constraints no banco reforçam: `balance >= 0`, `amount > 0`, `fee_amount >= 0`.

**O saldo mora em `account.balance`.** É uma coluna mantida, não um valor calculado somando o extrato: a leitura é direta, e o débito/crédito acontece sob lock, na mesma transação que insere a linha em `transaction`. O custo é haver duas representações do dinheiro (a coluna e o histórico) que só se mantêm coerentes porque o commit é único. Consequência a conhecer: o `initial_balance` entra direto no saldo, **sem** linha em `transaction`, então o extrato não reconstrói esse valor inicial.

**Travamento com `SELECT ... FOR UPDATE`.** Em uma transferência, origem e destino são travados **em ordem crescente de `id`**, independentemente de quem é quem. Assim `A→B` e `B→A` simultâneas não se travam mutuamente (sem deadlock). As linhas são relidas com `populate_existing()` depois do lock, e a contagem da franquia e o cálculo do saldo acontecem **depois** de travar, então duas transferências concorrentes não enxergam o mesmo saldo antigo. Débito, crédito e registro são confirmados em **um único `commit`**; qualquer exceção faz `rollback`. Os testes de integração incluem cenários concorrentes (conservação do dinheiro e impossibilidade de estourar o saldo).

**Histórico de status em tabela própria.** `customer.status_id` guarda o status **atual**; cada mudança (inclusive a criação) acrescenta uma linha em `customer_status_event` com `event_datetime`, nunca altera nem apaga as anteriores. O `GET /customers/{key}` devolve esse histórico em `status_events`. Que o histórico é só de inserção é uma convenção do código, não um bloqueio do banco. Os status moram em `customer_status` (`pending_kyc`, `active`, `blocked`, `inactive`).

**Identificadores públicos separados dos internos.** Chaves de API são UUIDs (`customer_key`, `account_key`, `transaction_key`); as chaves primárias numéricas nunca saem na resposta. É por elas, porém, que se define a ordem de lock.

## Entrega: repositório público em 13/10

Na entrega de **13/10**, o repositório precisa estar **público**. Antes de enviar:

1. No GitHub, em *Settings → General → Danger Zone → Change visibility*, deixe como **Public**.
2. Abra a URL do repositório numa **janela anônima** (sem login). Se o código aparece, está público.
3. Confirme que nada sensível foi versionado: `git ls-files | grep -E '(^|/)\.env$'` não deve listar nada (só `.env.example` é versionado, e ele contém apenas valores de exemplo).
4. Confirme que o `README.md` e o `docker compose up` funcionam a partir de um clone novo.
