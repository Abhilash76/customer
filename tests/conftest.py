import sys
import os
import pytest

# Add backend directory to sys.path so we can import modules for testing
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
