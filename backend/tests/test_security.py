from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_the_plaintext() -> None:
    hashed = hash_password("correct-horse")

    assert hashed != "correct-horse"
    assert verify_password("correct-horse", hashed)


def test_wrong_password_is_rejected() -> None:
    hashed = hash_password("correct-horse")

    assert not verify_password("wrong-horse", hashed)


def test_same_password_hashes_differently() -> None:
    """Each hash embeds a fresh random salt."""
    assert hash_password("same") != hash_password("same")


def test_token_round_trip() -> None:
    token = create_access_token("user-id-123")

    assert decode_access_token(token) == "user-id-123"


def test_expired_token_is_rejected() -> None:
    token = create_access_token("user-id-123", expires_delta=timedelta(seconds=-1))

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_token_signed_with_another_secret_is_rejected() -> None:
    other_secret = "x" * 32  # long enough that PyJWT does not warn about key length
    token = jwt.encode({"sub": "attacker"}, other_secret, algorithm="HS256")

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token)
