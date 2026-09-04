import json
import time
import pytest
from scripts.jwt_security import (
    JWTValidator,
    base64url_encode,
    JWTAlgorithmConfusionError,
    JWTInvalidHeaderError,
    JWTSignatureError,
    JWTExpiredError,
)


def create_token(header: dict, payload: dict, signature: bytes = b"mock_sig") -> str:
    h_b64 = base64url_encode(json.dumps(header).encode("utf-8"))
    p_b64 = base64url_encode(json.dumps(payload).encode("utf-8"))
    s_b64 = base64url_encode(signature)
    return f"{h_b64}.{p_b64}.{s_b64}"


def test_jwt_validator_rejects_none_algorithm_configuration():
    with pytest.raises(JWTInvalidHeaderError) as excinfo:
        JWTValidator(allowed_algorithms=["RS256", "none"])
    assert "Algorithm 'none' is strictly prohibited" in str(excinfo.value)


def test_jwt_validator_blocks_rs256_to_hs256_confusion():
    # Server expects RS256 with an asymmetric public key
    validator = JWTValidator(
        allowed_algorithms=["RS256"],
        expected_algorithm="RS256"
    )

    # Attacker forged token using HS256 with the server's public key as HMAC secret
    forged_token = create_token(
        header={"alg": "HS256", "typ": "JWT"},
        payload={"sub": "admin", "role": "superuser"}
    )

    with pytest.raises(JWTAlgorithmConfusionError) as excinfo:
        validator.decode_and_verify(forged_token)
    assert "Algorithm confusion detected" in str(excinfo.value)
    assert "HS256" in str(excinfo.value)


def test_jwt_validator_blocks_none_alg_in_token():
    validator = JWTValidator(allowed_algorithms=["RS256"], expected_algorithm="RS256")
    none_token = create_token(
        header={"alg": "none", "typ": "JWT"},
        payload={"sub": "admin"}
    )
    with pytest.raises(JWTAlgorithmConfusionError) as excinfo:
        validator.decode_and_verify(none_token)
    assert "'none' algorithm is rejected" in str(excinfo.value)


def test_jwt_validator_accepts_expected_algorithm():
    validator = JWTValidator(allowed_algorithms=["RS256", "ES256"], expected_algorithm="RS256")
    valid_token = create_token(
        header={"alg": "RS256", "typ": "JWT"},
        payload={"sub": "alice", "exp": time.time() + 3600}
    )

    # Signature validator callback returns True for valid RS256
    def mock_verifier(signing_input, sig, alg):
        return alg == "RS256"

    payload = validator.decode_and_verify(valid_token, verify_signature_fn=mock_verifier)
    assert payload["sub"] == "alice"


def test_jwt_validator_detects_signature_failure():
    validator = JWTValidator(allowed_algorithms=["RS256"], expected_algorithm="RS256")
    token = create_token(
        header={"alg": "RS256", "typ": "JWT"},
        payload={"sub": "alice"}
    )

    def failing_verifier(signing_input, sig, alg):
        return False

    with pytest.raises(JWTSignatureError):
        validator.decode_and_verify(token, verify_signature_fn=failing_verifier)


def test_jwt_validator_detects_expiration():
    validator = JWTValidator(allowed_algorithms=["RS256"], expected_algorithm="RS256", leeway_seconds=0)
    expired_token = create_token(
        header={"alg": "RS256", "typ": "JWT"},
        payload={"sub": "alice", "exp": time.time() - 100}
    )
    with pytest.raises(JWTExpiredError):
        validator.decode_and_verify(expired_token)
