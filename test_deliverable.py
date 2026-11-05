"""Local conformance check: minimal EventSource framing vectors."""
import deliverable

VECTORS = [
    ([b'data: {"id":1}\n\n'], ['{"id":1}']),
    ([b'data: {"method":', b'"ping"}\n\n'], ['{"method":"ping"}']),
    ([b'data: {"unit":"\xc2', b'\xb5s"}\n\n'], ['{"unit":"\u00b5s"}']),
    ([b'data: {"glyph":"\xf0\x9f', b'\x9a\x80"}\n\n'], ['{"glyph":"\U0001f680"}']),
    ([b'data: {"seq":6}\r\n\r\n'], ['{"seq":6}']),
    ([b': keepalive\ndata: {"seq":7}\n\n'], ['{"seq":7}']),
]


def test_vectors():
    fn = getattr(deliverable, deliverable.TARGET_ENTRYPOINT)
    for chunks, expected in VECTORS:
        assert fn(chunks) == expected


if __name__ == "__main__":
    test_vectors()
    print("ok")
