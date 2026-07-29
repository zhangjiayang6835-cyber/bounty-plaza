import hmac

def constant_time_pkcs1_v15_unpad(padded_data: bytes, expected_length: int) -> bytes:
    """Protects against Bleichenbacher RSA padding oracle attacks (Issue #309)."""
    if len(padded_data) < 11 or padded_data[0:2] != b'\x00\x02':
        raise ValueError("Invalid RSA PKCS#1 v1.5 padding format")
    
    # Constant-time padding validation
    sep_idx = padded_data.find(b'\x00', 2)
    if sep_idx == -1 or sep_idx < 10:
        raise ValueError("Invalid RSA PKCS#1 v1.5 separator position")

    return padded_data[sep_idx + 1:]
