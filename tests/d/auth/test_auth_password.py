"""D-R01 口令派生行为：随机盐、可校验、畸形记录不抛异常。"""

import pytest

from app.d.auth.password import ITERATIONS, hash_password, verify_password


def test_d_r01_hash_is_salted_pbkdf2_and_verifiable():
    stored = hash_password("Demo#2026")

    algorithm, iterations, salt, digest = stored.split("$")
    assert algorithm == "pbkdf2_sha256"
    assert int(iterations) == ITERATIONS
    assert len(bytes.fromhex(salt)) == 16
    assert len(bytes.fromhex(digest)) == 32
    assert verify_password("Demo#2026", stored) is True


def test_d_r01_same_password_hashes_differently_and_both_verify():
    first = hash_password("Demo#2026")
    second = hash_password("Demo#2026")

    assert first != second
    assert verify_password("Demo#2026", first) is True
    assert verify_password("Demo#2026", second) is True


def test_d_r01_wrong_password_is_rejected():
    stored = hash_password("Demo#2026")

    assert verify_password("demo#2026", stored) is False
    assert verify_password("", stored) is False
    assert verify_password("Demo#2026 ", stored) is False


def test_d_r01_stored_hash_never_contains_plaintext_password():
    stored = hash_password("PlainSecret#2026")

    assert "PlainSecret#2026" not in stored


@pytest.mark.parametrize(
    "stored",
    [
        "",
        "plain-text",
        "pbkdf2_sha256$200000$not-hex$ff",
        "pbkdf2_sha256$200000$00ff$not-hex",
        "pbkdf2_sha256$0$00ff$ff",
        "md5$200000$00ff$ff",
        "pbkdf2_sha256$200000$$ff",
        "pbkdf2_sha256$200000$00ff$",
    ],
)
def test_d_r01_malformed_stored_hash_is_rejected_without_exception(stored):
    assert verify_password("Demo#2026", stored) is False


def test_d_r01_non_string_arguments_are_rejected():
    stored = hash_password("Demo#2026")

    assert verify_password(None, stored) is False
    assert verify_password("Demo#2026", None) is False


def test_d_r01_empty_password_cannot_be_hashed():
    with pytest.raises(ValueError):
        hash_password("")


def test_d_r01_custom_iterations_are_recorded_and_honoured():
    stored = hash_password("Demo#2026", iterations=1000)

    assert stored.split("$")[1] == "1000"
    assert verify_password("Demo#2026", stored) is True
