"""A missing UDP server must never turn a client into its own responder."""

import errno
import socket

import pytest

from planet_protocol.client import JointTargetClient, OperatorClient


def sockets(monkeypatch, family, *, collision=True, failure=None, same_port_remote=False):
    host = "::1" if family == socket.AF_INET6 else "127.0.0.1"
    endpoint = (host, 40500, 0, 0) if family == socket.AF_INET6 else (host, 40500)
    created, sent = [], []

    class Socket:
        def __init__(self, index):
            self.index = index
            self.closed = self.bound = False
            self.endpoint = None

        def settimeout(self, value):
            self.timeout = value
            if self.index == 1 and failure == "timeout":
                raise OSError("timeout setup failed")

        def bind(self, address):
            assert self.index == 1
            assert not created[0].closed  # The colliding port remains reserved.
            assert address == ("::" if family == socket.AF_INET6 else "0.0.0.0", 0)
            self.bound = True
            if failure == "bind":
                raise OSError("bind failed")

        def connect(self, address):
            assert address == endpoint
            if self.index == 1:
                assert self.bound and not created[0].closed
                if failure == "connect":
                    raise OSError("connect failed")
            self.endpoint = address

        def getsockname(self):
            if self.index == 0 and failure == "inspect":
                raise OSError("endpoint inspection failed")
            if (self.index == 0 and collision) or (self.index == 1 and failure == "self"):
                return endpoint
            source = list(endpoint)
            if same_port_remote:
                source[0] = "::2" if family == socket.AF_INET6 else "127.0.0.2"
            else:
                source[1] += 1
            return tuple(source)

        def getpeername(self):
            return self.endpoint

        def send(self, payload):
            assert not self.closed
            assert self.getsockname() != self.getpeername()
            sent.append(self.index)

        def recv(self, maximum):
            # The repaired client sees a missing server, never its own request.
            raise ConnectionRefusedError(errno.ECONNREFUSED, "no server")

        def close(self):
            self.closed = True

    def factory(selected_family, kind):
        assert selected_family == family and kind == socket.SOCK_DGRAM
        index = len(created)
        assert index < 2, "self-connection recovery must not retry indefinitely"
        if index == 1 and failure == "create":
            raise OSError("socket allocation failed")
        value = Socket(index)
        created.append(value)
        return value

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [(family, socket.SOCK_DGRAM, 0, "", endpoint)])
    monkeypatch.setattr(socket, "socket", factory)
    return host, created, sent


@pytest.mark.parametrize("family", [socket.AF_INET, socket.AF_INET6])
@pytest.mark.parametrize("client_type", [OperatorClient, JointTargetClient])
def test_self_connection_is_replaced_before_any_request(monkeypatch, family, client_type):
    host, created, sent = sockets(monkeypatch, family)
    with client_type(host, 40500, timeout_s=.2) as client:
        assert len(created) == 2 and created[0].closed
        assert not created[1].closed and created[1].bound
        assert created[1].timeout == .2
        assert client._socket.getsockname() != client._socket.getpeername()
        with pytest.raises(ConnectionRefusedError):
            client.status()
        assert sent == [1]
    assert all(sock.closed for sock in created)


@pytest.mark.parametrize("family", [socket.AF_INET, socket.AF_INET6])
@pytest.mark.parametrize("same_port_remote", [False, True])
def test_distinct_endpoints_keep_the_original_connected_socket(monkeypatch, family, same_port_remote):
    host, created, _ = sockets(monkeypatch, family, collision=False, same_port_remote=same_port_remote)
    with OperatorClient(host, 40500):
        assert len(created) == 1 and not created[0].closed
        assert not created[0].bound
    assert created[0].closed


@pytest.mark.parametrize("failure", ["create", "timeout", "bind", "connect", "self", "inspect"])
def test_self_connection_recovery_is_bounded_and_closes_every_socket(monkeypatch, failure):
    host, created, sent = sockets(monkeypatch, socket.AF_INET, failure=failure)
    with pytest.raises(OSError) as error:
        OperatorClient(host, 40500)
    if failure == "self":
        assert error.value.errno == errno.EADDRINUSE
    assert not sent
    assert 1 <= len(created) <= 2
    assert all(sock.closed for sock in created)
