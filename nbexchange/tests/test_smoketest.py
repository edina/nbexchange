import socket
import pytest

@pytest.mark.skip()
def test_smoketest_nbexchange(container):
    sock = socket.socket()
    sock.connect(("127.0.0.1", container.ports["9000/tcp"][0]))
