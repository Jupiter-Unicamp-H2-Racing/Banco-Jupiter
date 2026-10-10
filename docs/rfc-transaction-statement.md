# RFC — Extrato de transações por conta

## Contexto

A API registra transferências em `POST /accounts/{account_key}/transactions`, mas ainda não oferece leitura do extrato. O extrato deve apresentar as transferências em que a conta consultada participou, sem expor chaves internas do banco. A implementação respeita o caminho existente `resources → controllers → repositories → models`, usando schema JSON para entrada e DTO para saída.

## Decisão de modelagem

Mantemos a tabela única `transaction`: cada linha representa uma transferência, com `source_account_id`, `destination_account_id`, `amount` e `fee_amount` atômicos. A direção é derivada em tempo de consulta: `debit` quando a conta consultada é a origem e `credit` quando é o destino. A tarifa é uma propriedade do débito da transferência; no lado de crédito, a resposta informa `fee_amount: 0`.

Esta decisão permite que uma consulta filtrada por origem OU destino produza o extrato, mantém a tarifa atomicamente ligada à transferência e corresponde ao domínio atual, que não possui depósitos nem tarifas como operações independentes. Não criamos coluna `type` nem tabelas separadas.

Alternativa descartada: um ledger com coluna `type` (`DEPOSIT`, `TRANSFER`, `FEE`) e possivelmente lançamentos separados por perna. Isso se tornaria apropriado quando depósitos, saques, tarifas independentes, estornos ou ajustes contábeis precisassem existir como operações de primeira classe e todas as mudanças de saldo precisassem ser representadas como lançamentos balanceados. Essa evolução exigiria migração de domínio, não apenas um campo adicional.

`transaction.id` permanece `BIGSERIAL` interno e `transaction_key CHAR(36)` é a chave pública. A tabela é append-only por convenção do fluxo atual: o código da aplicação só insere transações; não há UPDATE/DELETE neste recurso. Não foi adicionado trigger nesta versão, para evitar alterar o comportamento operacional de migrations/fixtures existentes; pode ser adicionado em ambiente controlado como defesa adicional.

## Índices

A migration `002_transaction_statement_indexes.sql` cria:

- `(source_account_id, created_at DESC, id DESC)`;
- `(destination_account_id, created_at DESC, id DESC)`.

Os índices cobrem cada ramo do filtro de extrato e a ordem determinística. Espera-se que `EXPLAIN` mostre `Index Scan`/`Bitmap Index Scan` para conjuntos seletivos; o otimizador ainda pode preferir `Seq Scan` em tabelas pequenas ou quando a maioria das linhas corresponde ao filtro. `id DESC` desempata timestamps iguais. A migration pode ser reaplicada com segurança. `database/database.sql` e `Transaction.__table_args__` espelham os índices.

## Contrato da API

`GET /accounts/{account_key}/transactions`

Query params opcionais:

- `limit`: inteiro em string entre 1 e 100; padrão 20;
- `page`: inteiro em string maior ou igual a 1; padrão 1;
- `start_date`: data ISO `YYYY-MM-DD`, inclusiva;
- `end_date`: data ISO `YYYY-MM-DD`, inclusiva.

Exemplo:

```http
GET /accounts/0f0f0f0f-1111-4222-8333-123456789abc/transactions?limit=20&page=1&start_date=2026-01-01&end_date=2026-01-31
```

Resposta `200`:

```json
{
  "items": [
    {
      "transaction_key": "a1b2c3d4-1111-4222-8333-123456789abc",
      "direction": "debit",
      "amount": 2500,
      "fee_amount": 100,
      "counterparty_account_key": "b2c3d4e5-2222-4333-8444-23456789abcd",
      "created_at": "2026-01-15T14:30:00+00:00"
    }
  ],
  "pagination": {"total_items": 1, "page": 1, "limit": 20}
}
```

Valores monetários são centavos inteiros. A resposta não contém `id`, `source_account_id` nem `destination_account_id`. A consulta inclui linhas em que a conta é origem ou destino, ordenadas por `created_at DESC, id DESC`. `total_items` conta todas as correspondências após filtros de data, antes da paginação.

## Paginação

A implementação usa `page`/`limit` e `OFFSET`, mantendo o padrão já utilizado em `GET /customers` e o contrato solicitado. Em páginas profundas, o banco precisa localizar e descartar as linhas anteriores, tornando o custo crescente com o offset; inserções concorrentes também podem deslocar resultados entre páginas.

Como evolução para extratos volumosos, recomenda-se keyset/cursor: `WHERE (created_at, id) < (:cursor_created_at, :cursor_id) ORDER BY created_at DESC, id DESC LIMIT :limit`. O cursor mantém a progressão baseada na última linha vista e evita descartar grandes quantidades de registros.

## Erros

- `404 AccountNotFound` (`QIT002001`) se a conta não existir;
- `400 InvalidSchema` (`QIT000001`) para parâmetros desconhecidos, formato de data fora do padrão ou paginação fora dos limites;
- `422 InvalidStatementDate` (`QIT002004`) para data impossível no calendário, como `2025-02-30`;
- `422 InvalidDateRange` (`QIT002005`) quando `start_date > end_date`.

O fim do intervalo é implementado como `< 00:00 do dia seguinte a end_date`, incluindo o dia final inteiro.

## Segurança, IDOR e limitações

A API hoje usa apenas o middleware `internal_token`; não há identidade de cliente autenticado nem vínculo de autorização entre cliente e conta. Portanto, esta rota não inventa autenticação. O controller centraliza a verificação em `_ensure_account_access`: hoje verifica existência; quando houver identidade de cliente, esse ponto deverá verificar o vínculo e lançar o mesmo `AccountNotFound` para conta inexistente ou pertencente a terceiro, evitando distinguir os casos com `403`.

O token interno não deve ser tratado como autorização de usuário final. A rota deve permanecer atrás do middleware interno conforme o restante da API. A listagem é somente leitura: não faz commit, não altera saldo/transações e não usa `FOR UPDATE`.

## Riscos e acompanhamento

`OFFSET` pode ficar caro em contas com muitos lançamentos. Os índices ajudam os filtros por conta, mas o predicado OR pode levar o PostgreSQL a combinar índices ou escolher outro plano; confirmar com `EXPLAIN (ANALYZE, BUFFERS)` em volume representativo. O trigger de imutabilidade fica como endurecimento opcional futuro. A implementação não inclui depósitos, estornos ou lançamentos de tarifa independentes, pois não pertencem ao modelo atual.
