import pytest
import ttnn

@pytest.fixture(scope="session")
def device():
    return ttnn.open_device(0)
