import pytest

ttnn = pytest.importorskip("ttnn")

@pytest.fixture(scope="session")
def device():
    device = ttnn.open_device(device_id=0)
    yield device
    ttnn.close_device(device)
