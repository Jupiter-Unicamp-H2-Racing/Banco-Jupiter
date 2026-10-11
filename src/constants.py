import os


SERVICE_ROOT = os.path.abspath(os.path.dirname(__file__))

# Onde moram os arquivos de schema — os .json que descrevem o formato
# que cada requisicao precisa ter. Quem le essa pasta e o
# src/utils/schema_handler.py.
SCHEMA_PATH = os.path.join(SERVICE_ROOT, "schemas")

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "bootcamp-api")

DATABASE_URL = os.environ.get("DATABASE_URL")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN")

# A API de boletos: o serviço de fora que este projeto chama pra emitir
# uma cobrança (veja src/connectors/). O endereço vem do ambiente, como
# tudo aqui — na sua máquina ele aponta pro mock server do sábado 4; em
# produção, apontaria pro serviço de verdade. O código não sabe a
# diferença, e esse é o ponto.
BANKSLIP_API_URL = os.environ.get("BANKSLIP_API_URL", "http://localhost:8080")
BANKSLIP_API_INTERNAL_TOKEN = os.environ.get("BANKSLIP_API_INTERNAL_TOKEN", "default_token")

# Quantos segundos esperar pelo serviço de boletos antes de desistir.
# Todo connector TEM um timeout — o porquê está em
# src/connectors/rest_connector.py.
BANKSLIP_API_TIMEOUT = int(os.environ.get("BANKSLIP_API_TIMEOUT", "5"))

# Rotas públicas: não exigem o header INTERNAL-TOKEN. São as duas que
# precisam responder pra quem ainda não tem token nenhum: a raiz, que
# diz quem é este serviço, e o health check, que o Docker consulta pra
# saber se a API já está de pé.
BYPASS_ENDPOINTS = [
    "/",
    "/health_check",
]

REQUIRED_VARIABLES = ["DATABASE_URL", "INTERNAL_TOKEN"]


def check_variables():
    missing = []
    for name in REQUIRED_VARIABLES:
        if not globals().get(name):
            missing.append(name)

    if missing:
        raise EnvironmentError(
            f"Faltam variáveis de ambiente obrigatórias: {', '.join(missing)}. "
            "Configure-as explicitamente no ambiente ou no arquivo .env."
        )

    if APP_ENV.lower() in {"production", "prod"} and INTERNAL_TOKEN.strip() in {
        "default_token", "troque-por-um-token-aleatorio"
    }:
        raise EnvironmentError(
            "INTERNAL_TOKEN não pode usar o valor de exemplo em produção. "
            "Configure uma credencial forte por variável de ambiente."
        )

# Conta interna que recebe as tarifas de transferência.
FEE_REVENUE_ACCOUNT_KEY = "00000000-0000-4000-8000-000000000001"
FEE_REVENUE_CUSTOMER_KEY = "00000000-0000-4000-8000-000000000002"

DEFAULT_LIMIT = 10
DEFAULT_PAGE = 1
MAX_LIMIT = 100
MAX_BALANCE = 2**63 - 1
BUSINESS_TIMEZONE = os.environ.get("BUSINESS_TIMEZONE", "America/Sao_Paulo")
