from errors import QIException


class InvalidDocumentNumber(QIException):
    """O CPF tem o formato certo e não existe.

    422, e não 400, de propósito: 400 quer dizer "não consegui ler o seu
    pedido". Aqui a API leu, entendeu, e o valor é que não pode existir —
    os dois últimos dígitos não batem com a conta. A diferença está
    explicada em src/utils/document_number.py.
    """

    code = "QIT001003"

    def __init__(self, document_number) -> None:
        title = "Invalid Document Number"
        http_status = 422
        description = f"The document number {document_number} is not a valid CPF."
        translation = "O CPF informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedDocumentNumber(QIException):
    """Já existe um cadastro com este CPF.

    409 Conflict: o pedido está correto em si, e o que impede é o que já
    está no banco. É a mesma família do CustomerFinalStatus aqui em
    cima — conflito com o que já existe, não erro de quem pediu.
    """

    code = "QIT001004"

    def __init__(self, document_number) -> None:
        title = "Document Number already registered"
        http_status = 409
        description = f"There is already an entity with the document number {document_number}."
        translation = "Já existe um cadastro com este CPF."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedEmail(QIException):
    code = "QIT001005"

    def __init__(self, email) -> None:
        title = "Email already registered"
        http_status = 409
        description = f"There is already an entity with the email {email}."
        translation = "Já existe um cadastro com este e-mail."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidBirthdate(QIException):
    """A data tem o formato certo e não existe no calendário.

    Existe porque o `pattern` do schema sabe contar dígitos, não dias:
    "2025-02-30" e "9999-99-99" passam pelo regex e morrem no
    `date.fromisoformat`. Sem esta classe, esse ValueError virava 500 —
    a API culpando a si mesma por um erro de quem chamou.
    """

    code = "QIT001007"

    def __init__(self, birthdate) -> None:
        title = "Invalid Birthdate"
        http_status = 422
        description = f"The birthdate {birthdate} is not a real date."
        translation = "A data de nascimento informada não existe."
        super().__init__(title, self.code, http_status, description, translation)


class AccountNotFound(QIException):
    code = "QIT002001"

    def __init__(self, account_key) -> None:
        super().__init__(
            "Account not Found", self.code, 404,
            f"Account with key {account_key} was not found.",
            "A conta informada não foi encontrada.",
        )


class InsufficientBalance(QIException):
    code = "QIT002002"

    def __init__(self) -> None:
        super().__init__(
            "Insufficient Balance", self.code, 422,
            "The source account does not have enough balance for this transfer and its fee.",
            "Saldo insuficiente para realizar a transferência e pagar a tarifa.",
        )


class InvalidTransfer(QIException):
    code = "QIT002003"

    def __init__(self, description: str) -> None:
        super().__init__(
            "Invalid Transfer", self.code, 422,
            description, "A transferência solicitada não é válida.",
        )


# Erros canônicos do domínio Customer. Mantêm os códigos/contratos HTTP
# já usados pela API, sem reaproveitar nomes da entidade removida.
class NotFoundCustomer(QIException):
    code = "QIT001001"
    def __init__(self, customer_key):
        super().__init__("Customer not Found", self.code, 404,
                         f"Customer with key {customer_key} was not found.",
                         f"O cliente com chave {customer_key} não foi encontrado.")

class CustomerFinalStatus(QIException):
    code = "QIT001002"
    def __init__(self, old_status, new_status):
        super().__init__("Customer cannot change status", self.code, 409,
                         f"Customer with status {old_status} cannot update to {new_status}.",
                         "Este cliente não pode ter o status alterado.")

class UnderageCustomer(QIException):
    code = "QIT001006"
    def __init__(self, age, minimum_age):
        super().__init__("Customer is underage", self.code, 422,
                         f"The customer is {age} years old; minimum age is {minimum_age}.",
                         f"É preciso ter pelo menos {minimum_age} anos.")

class OverAgeCustomer(QIException):
    code = "QIT001008"
    def __init__(self, age, maximum_age):
        super().__init__("Customer age exceeds limit", self.code, 422,
                         f"The customer is {age} years old; maximum age is {maximum_age}.",
                         f"A idade máxima para cadastro é {maximum_age} anos.")
