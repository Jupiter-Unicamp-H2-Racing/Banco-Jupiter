import pytest

from tests.utils.random_generator import RandomGenerator
from utils.document_number import is_valid_cpf


def test_valid_cpf_is_accepted_with_and_without_mask():
    assert is_valid_cpf("529.982.247-25")
    assert is_valid_cpf("52998224725")


def test_generated_cpfs_are_valid():
    assert all(is_valid_cpf(RandomGenerator.generate_cpf()) for _ in range(50))


@pytest.mark.parametrize("value", [
    "111.222.333-44",   # formato certo, dígitos verificadores errados
    "529.982.247-24",   # último dígito errado
    "111.111.111-11",   # dígitos repetidos
    "529.982.247",      # curto demais
    "",
])
def test_invalid_cpf_is_rejected(value):
    assert not is_valid_cpf(value)
