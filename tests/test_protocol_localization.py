"""Strict localization codec and producer tests using only the protocol package."""

import json
import socket
from pathlib import Path
import subprocess
import sys

import pytest

from planet_protocol.localization import (
    LOCALIZATION_SCHEMA, MAX_DATAGRAM_BYTES, MAX_SAFE_INTEGER, LocalizationClient,
    LocalizationSample, decode_localization, encode_localization, new_localization_session,
)

def sample(**overrides):
    values = dict(position_w_m=(1., 2., 3.), orientation_wxyz=(1., 0., 0., 0.),
                  linear_velocity_w_mps=(0.1, 0.2, 0.3), source="mocap",
                  session_id=100, sequence=0, source_timestamp_us=1234567,
                  ttl_s=0.25, source_age_s=0.0)
    return LocalizationSample(**{**values, **overrides})


@pytest.mark.parametrize("field,value", [
    ("position_w_m", [1, 2]), ("position_w_m", [1, 2, float("nan")]),
    ("position_w_m", [True, 0, 0]), ("position_w_m", ["1", 2, 3]),
    ("position_w_m", [10 ** 1000, 0, 0]),
    ("linear_velocity_w_mps", [[1], 2, 3]),
    ("orientation_wxyz", [0, 0, 0, 0]), ("orientation_wxyz", [2, 0, 0, 0]),
    ("orientation_wxyz", [float("inf"), 0, 0, 0]),
    ("sequence", -1), ("sequence", 0.1), ("sequence", True),
    ("session_id", 0), ("session_id", MAX_SAFE_INTEGER + 1),
    ("source_timestamp_us", -1), ("source_timestamp_us", MAX_SAFE_INTEGER + 1),
    ("source_age_s", -0.1), ("source_age_s", float("nan")),
    ("source_age_s", 10 ** 1000), ("ttl_s", 0), ("ttl_s", True),
    ("valid", 1), ("source", ""), ("source", "mocap stream"),
    ("frame_id", "policy_root"), ("child_frame_id", "x" * 129),
])
def test_sample_strict_validation(field, value):
    with pytest.raises(ValueError):
        sample(**{field: value})


def test_quaternion_convention_preserves_rotation_and_normalizes_roundoff():
    result = sample(orientation_wxyz=(0., 0., 0., 1.00001))
    assert result.orientation_wxyz == (0., 0., 0., 1.)
    assert decode_localization(encode_localization(result)).orientation_wxyz == (0., 0., 0., 1.)


@pytest.mark.parametrize("mutate", [
    lambda data: {**data, "unexpected": 1},
    lambda data: {key: value for key, value in data.items() if key != "valid"},
    lambda data: {**data, "schema": "planet.localization.v2"},
    lambda data: {**data, "type": "target"},
    lambda data: {**data, "valid": "false"},
])
def test_wire_fields_are_versioned_and_strict(mutate):
    data = json.loads(encode_localization(sample()))
    with pytest.raises(ValueError):
        decode_localization(json.dumps(mutate(data)).encode())


@pytest.mark.parametrize("data", [
    b"", b"[]", b"true", b"{", b"\xff", b"{" * 2000,
    b'{"schema":"a","schema":"b"}',
    b'{"position_w_m":[NaN,0,0]}', b" " * (MAX_DATAGRAM_BYTES + 1),
])
def test_malformed_wire_is_rejected(data):
    with pytest.raises(ValueError):
        decode_localization(data)


def test_client_new_sessions_are_ordered():
    assert new_localization_session() < new_localization_session()


def test_round_trip_copies_vectors_and_rejects_an_unselected_alias():
    position = [1., 2., 3.]
    value = sample(position_w_m=position)
    position[0] = 100.
    assert value.position_w_m == (1., 2., 3.)
    assert decode_localization(encode_localization(value)) == value
    alternate = encode_localization(value, schema="application.localization.v1")
    with pytest.raises(ValueError, match="schema"):
        decode_localization(alternate)
    assert decode_localization(alternate, schema="application.localization.v1") == value
    assert decode_localization(alternate, schema=(LOCALIZATION_SCHEMA, "application.localization.v1")) == value


@pytest.mark.parametrize("schema", [None, [], (), ("",), (123,), True])
def test_schema_selection_is_explicit_and_checked(schema):
    with pytest.raises(ValueError):
        decode_localization(encode_localization(sample()), schema=schema)


def test_client_sends_ordered_samples_and_explicit_invalidation_over_real_udp():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(1.)
        with LocalizationClient(*receiver.getsockname(), source="mocap", session_id=100) as client:
            sent = client.send([1, 2, 3], [1, 0, 0, 0], [0, 0, 0],
                               source_timestamp_us=123, source_age_s=0.02)
            assert decode_localization(receiver.recv(8192)) == sent
            assert sent.sequence == 0 and sent.session_id == client.session_id == 100
            client.send([1, 2, 3], [1, 0, 0, 0], [0, 0, 0], valid=False)
            invalid = decode_localization(receiver.recv(8192))
            assert not invalid.valid and invalid.sequence == 1
        with pytest.raises(ValueError, match="closed"):
            client.send([0, 0, 0], [1, 0, 0, 0], [0, 0, 0])


def test_client_schema_can_be_explicitly_specialized_without_changing_sample_types():
    class ApplicationClient(LocalizationClient):
        schema = "application.localization.v1"

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(1.)
        with ApplicationClient(*receiver.getsockname(), session_id=1) as client:
            sent = client.send([0, 0, 1], [1, 0, 0, 0], [0, 0, 0])
            packet = receiver.recv(8192)
            assert json.loads(packet)["schema"] == ApplicationClient.schema
            assert decode_localization(packet, schema=ApplicationClient.schema) == sent


def test_all_protocol_modules_load_without_site_packages():
    import planet_protocol

    source = Path(planet_protocol.__file__).parent.parent
    subprocess.run([sys.executable, "-S", "-c", """
import sys
sys.path.insert(0, sys.argv[1])
from planet_protocol import operator, client, upper, localization
assert upper.JointTargetClient is client.JointTargetClient
assert client.LocalizationClient is localization.LocalizationClient
assert 'site' not in sys.modules
""", str(source)], check=True)
