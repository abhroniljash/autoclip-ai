from types import SimpleNamespace

from app import auth


def test_password_hash_round_trip():
    encoded = auth.hash_password("correct-horse-battery-staple")
    assert encoded != "correct-horse-battery-staple"
    assert auth.verify_password("correct-horse-battery-staple", encoded)
    assert not auth.verify_password("incorrect-password", encoded)


def test_password_minimum_length():
    try:
        auth.hash_password("short")
    except ValueError:
        return
    raise AssertionError("Short passwords must be rejected")


def test_jwt_token_contains_required_claims():
    previous = auth.JWT_SECRET
    auth.JWT_SECRET = "test-only-secret-value-with-more-than-32-characters"
    try:
        user = SimpleNamespace(id="user-123")
        token = auth.create_access_token(user)
        claims = auth.jwt.decode(
            token, auth.JWT_SECRET, algorithms=[auth.JWT_ALGORITHM],
            issuer="autoclip-ai", audience="autoclip-api"
        )
        assert claims["sub"] == "user-123"
        assert claims["aud"] == "autoclip-api"
    finally:
        auth.JWT_SECRET = previous
