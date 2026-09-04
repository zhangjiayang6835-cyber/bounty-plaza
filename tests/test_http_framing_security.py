import pytest
from scripts.http_framing_security import (
    HTTPFramingValidator,
    AmbiguousFramingError,
    MalformedHeaderError,
)


def test_clean_content_length_accepted():
    validator = HTTPFramingValidator()
    headers = {
        "Host": "bountyplaza.dev",
        "Content-Type": "application/json",
        "Content-Length": "42",
    }
    result = validator.validate_request_framing(headers)
    assert result["Content-Length"] == "42"
    assert result["Framing-Type"] == "content-length"


def test_clean_transfer_encoding_accepted():
    validator = HTTPFramingValidator()
    headers = {
        "Host": "bountyplaza.dev",
        "Transfer-Encoding": "chunked",
    }
    result = validator.validate_request_framing(headers)
    assert result["Transfer-Encoding"] == "chunked"
    assert result["Framing-Type"] == "chunked"


def test_simultaneous_cl_and_te_rejected():
    validator = HTTPFramingValidator()
    # Classic CL.TE smuggling vector
    headers = {
        "Host": "bountyplaza.dev",
        "Content-Length": "100",
        "Transfer-Encoding": "chunked",
    }
    with pytest.raises(AmbiguousFramingError) as excinfo:
        validator.validate_request_framing(headers)
    assert "Both Transfer-Encoding and Content-Length are present" in str(excinfo.value)


def test_malformed_content_length_rejected():
    validator = HTTPFramingValidator()
    # Invalid non-integer characters
    with pytest.raises(MalformedHeaderError):
        validator.validate_request_framing({"Content-Length": "42a"})

    with pytest.raises(MalformedHeaderError):
        validator.validate_request_framing({"Content-Length": "-5"})


def test_malformed_transfer_encoding_rejected():
    validator = HTTPFramingValidator()
    # Obfuscated or invalid final encoding
    with pytest.raises(MalformedHeaderError):
        validator.validate_request_framing({"Transfer-Encoding": "chunked, identity"})

    with pytest.raises(MalformedHeaderError):
        validator.validate_request_framing({"Transfer-Encoding": "unsupported_enc"})


def test_http2_transfer_encoding_rejected():
    validator = HTTPFramingValidator()
    with pytest.raises(MalformedHeaderError) as excinfo:
        validator.validate_request_framing({"Transfer-Encoding": "chunked"}, protocol_version="HTTP/2.0")
    assert "Transfer-Encoding is prohibited in HTTP/2+" in str(excinfo.value)


def test_http2_framing_valid():
    validator = HTTPFramingValidator()
    result = validator.validate_request_framing({"Host": "bountyplaza.dev"}, protocol_version="HTTP/2.0")
    assert result["framing"] == "multiplexed"
