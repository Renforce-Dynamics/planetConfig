# planet-protocol

**Portable input protocols and lightweight UDP clients.**

A component of [planetConfig](https://github.com/Renforce-Dynamics/planetConfig), developed and maintained by Renforce Dynamics. This package uses only the Python standard library and imports no robot runtime, configuration loader or hardware binding.

| Module | Contract |
| --- | --- |
| `planet_protocol.operator` | PLNJ v3 encoding and v1/v2/v3 decoding; axes, state-request IDs and signals. |
| `planet_protocol.client` | Operator discovery/status, binding validation and joint-target clients. |
| `planet_protocol.upper` | Convenient exports of `JointTargetClient` and its schema constant. |
| `planet_protocol.localization` | Strict localization samples, JSON codec and one-way UDP producer. |

## Operator requests and discovery

PLNJ binary layout, CRC and deployed legacy formats remain unchanged. The v3 packet is 72 bytes with magic `PLNJ`. State IDs are selected by application configuration; the protocol contains no task implementation.

Read-only queries use JSON schema `planet.operator.v1` on the same UDP endpoint:

```python
from planet_protocol.client import OperatorClient

with OperatorClient("127.0.0.1", 50560) as operator:
    description = operator.validate_bindings([(0, "passive"), (1, "damping")])
    print(description["states"])
    print(operator.status())
```

`describe()` returns the configured state IDs, canonical keys, aliases and reset/fallback IDs. `validate_bindings()` checks ID/key pairs against that description before a producer starts sending requests. `status()` reports the receiver's latest published mode, safety flag and events; an optional `execution` field distinguishes backend execution from shadow evaluation. Queries do not request a state transition or acknowledge any particular command's execution.

`validate_operator_bindings(bindings, states_by_id, aliases)` provides the same matching check without a network call. Its default requires named bindings; `allow_unnamed=True` explicitly enables ID-only validation for old profiles.

## Upper-joint targets

```python
from planet_protocol.upper import JointTargetClient

with JointTargetClient("127.0.0.1", 15100) as targets:
    status = targets.status()
    activation = status["activation"]
    if activation is not None:
        # Supply positions suitable for the configured joint order and limits.
        positions_rad = [0.0] * status["dimension"]
        receipt = targets.send(activation, sequence=0, q_des=positions_rad)
```

Schema `planet.joint-target.v1` carries joint angles in radians, an activation token and an increasing sequence. The application chooses the joint order, dimension, limits and initial posture. The client currently requires a loopback IP address.

Acquire an activation when the consuming state is entered, then increase sequence numbers for each new frame. When that state is re-entered, acquire its new activation. The receiver retains the latest accepted target during delays or disconnects; a client never sends a reset posture on close. A receipt with `accepted: true` acknowledges reception into a mailbox, not backend submission or physical motion. An inactive state reports `activation: null`.

The client validates the returned activation and sequence. It does not choose an activation, advance sequence numbers, retry a target, or enter a motion state automatically.

## Localization

```python
import time
from planet_protocol.localization import LocalizationClient

sampled_monotonic = time.monotonic()
sampled_unix_us = time.time_ns() // 1000
# Replace these example values with a measured pose in the configured frames.
position = (0.0, 0.0, 0.8)
orientation = (1.0, 0.0, 0.0, 0.0)
velocity = (0.0, 0.0, 0.0)

with LocalizationClient("127.0.0.1", 15110, source="mocap") as producer:
    producer.send(position, orientation, velocity,
                  source_age_s=time.monotonic() - sampled_monotonic,
                  source_timestamp_us=sampled_unix_us)
```

Schema `planet.localization.v1` is a strict UTF-8 JSON object with `type: localization` and these sample fields:

| Field | Meaning |
| --- | --- |
| `position_w_m` | Three position components in meters, expressed in `frame_id`. |
| `orientation_wxyz` | Unit quaternion rotating child-frame vectors into `frame_id`, in **w, x, y, z** order. |
| `linear_velocity_w_mps` | Three linear-velocity components in meters per second, expressed in `frame_id`. |
| `frame_id`, `child_frame_id` | Defaults `world` and `policy_root`; producers perform any necessary coordinate conversion before sending. |
| `source` | Logical producer identity; default `localization`. |
| `session_id` | Positive ordered producer epoch. A restarted source must use a strictly larger epoch. |
| `sequence` | Nonnegative sequence, increasing without wrap within a session. |
| `source_timestamp_us` | Unix microseconds at sampling, for trace alignment; zero means unavailable. |
| `source_age_s` | Nonnegative sample age at publication, measured using the producer's monotonic clock. |
| `ttl_s` | Positive maximum sample age, default 0.25 seconds. |
| `valid` | Boolean availability; an accepted newer `false` sample withdraws localization. |

All values must be finite and vectors must have the exact dimensions. Quaternion norm tolerance is 0.001; accepted roundoff is normalized. Integer fields are limited to `2**53 - 1` for exact JSON interoperability. Missing, unknown or duplicate JSON fields are rejected. Source and frame names contain 1–128 characters without whitespace; the two frames must be distinct. Invalidations still need structurally valid numeric fields.

An application receiver should match source and frames explicitly, reject old sessions and non-increasing sequences, and calculate freshness using:

```text
source_age_s + receiver_monotonic_elapsed < min(ttl_s, receiver_max_age_s)
```

Unknown one-way network latency and time spent in an OS receive queue are not measured by this formula. `source_timestamp_us` is never compared directly with receiver monotonic time. A receiver must expire localization on disconnect; any state-specific hold or fallback is an application decision. This differs from the persistent upper-joint target contract.

`LocalizationClient` generates a Unix-microsecond session epoch and assigns sequences automatically. Epochs increase within one process. If wall time can move backwards across producer restarts, persist the previous epoch and select a greater one. Keep a single client for a continuous producer. A successful `send()` only reports local UDP submission; no receipt is requested. Closing the producer stops publication without generating a fallback frame.

`LocalizationSample` is immutable and copies numeric vectors. `encode_localization()` and `decode_localization()` use the default schema; adapters may select an explicit `schema=` alias. Decoding also accepts a tuple of allowed schema names. A receiver supporting aliases must share its ordering counters across all of them. Client classes expose a `schema` attribute so an application compatibility wrapper can select an alias without copying protocol code.

## Errors and lifecycle

All clients support `with` and `close()`. Input or response validation errors raise `ValueError`; network failures raise `OSError`, including timeouts. Operator and joint-target queries allow one outstanding request per client. A localization send consumes its sequence even when the network operation fails, preventing accidental sequence reuse.

See [AUTHORS.md](AUTHORS.md). Licensed under the [MIT License](LICENSE).
