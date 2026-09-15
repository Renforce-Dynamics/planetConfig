"""Optional stream metadata can be consumed without importing a robot runtime."""

import socket

import pytest

from planet_protocol.client import JOINT_TARGET_SCHEMA, JointTargetClient
from test_protocol_clients import server


BASE = {"schema": JOINT_TARGET_SCHEMA, "type": "status", "activation": 17, "dimension": 2}


@pytest.mark.parametrize("optional", [
    {},
    {"joint_names": None, "q_des": None, "sequence": None, "state_id": None, "state_key": None},
    {"joint_names": ["left", "right"], "q_des": [.2, -.1], "sequence": 42,
     "state_id": 5, "state_key": "upper_stream"},
    {"activation": None, "joint_names": ["left", "right"], "q_des": None,
     "sequence": None, "state_id": 5, "state_key": "upper_stream"},
])
def test_old_and_extended_status_shapes_are_preserved(optional):
    response = {**BASE, **optional}
    with server(lambda request: response) as (port, _):
        with JointTargetClient("127.0.0.1", port) as client:
            assert client.status() == response


@pytest.mark.parametrize("changes", [
    {"joint_names": "ab"}, {"joint_names": ["left"]},
    {"joint_names": ["left", "left"]}, {"joint_names": ["left", ""]},
    {"joint_names": ["left", 1]}, {"joint_names": ["left", {}]},
    {"q_des": "0,0"}, {"q_des": [0]}, {"q_des": [[0], [0]]},
    {"q_des": [True, 0]}, {"q_des": [0, None]}, {"q_des": [0, "1"]},
    {"q_des": [0, float("inf")]}, {"q_des": [0, float("nan")]},
    {"q_des": [0, 1 << 1024]},
    {"sequence": -1}, {"sequence": True}, {"sequence": "2"}, {"sequence": 1.5},
    {"activation": None, "sequence": 0}, {"activation": None, "q_des": [0, 0]},
    {"state_id": -1}, {"state_id": 65536}, {"state_id": True}, {"state_id": "5"},
    {"state_key": ""}, {"state_key": " "}, {"state_key": 5}, {"state_key": False},
])
def test_invalid_optional_status_fields_are_rejected(changes):
    with server(lambda request: {**BASE, **changes}) as (port, _):
        with JointTargetClient("127.0.0.1", port) as client:
            with pytest.raises(ValueError):
                client.status()


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "224.0.0.1", "ff02::1", "255.255.255.255"])
def test_joint_target_destinations_must_be_unicast(monkeypatch, host):
    def unexpected_socket(*args):
        pytest.fail("invalid destination must be rejected before opening a socket")

    monkeypatch.setattr(socket, "socket", unexpected_socket)
    with pytest.raises(ValueError, match="unicast"):
        JointTargetClient(host, 15100)
