# planetConfig

**Shared configuration and communication contracts for robot applications.**

This repository publishes two independent Python packages. Services select the package they need; source composition pins this repository without bringing in a robot executor, model or hardware SDK.

| Package | Import | Contents | Runtime dependencies |
| --- | --- | --- | --- |
| `planet-config` | `planet_config` | YAML layers, resource paths, strict overrides, provenance and snapshots | PyYAML |
| `planet-protocol` | `planet_protocol` | Operator input, state discovery, joint targets and localization codecs/clients | Python standard library |

## Quick start

Requires Python 3.10+ and `uv`.

```bash
git clone git@github.com:Renforce-Dynamics/planetConfig.git
cd planetConfig
./scripts/bootstrap.sh
./scripts/doctor.sh
./scripts/run.sh resolve pkg://planet_config/data/example.yaml --set service.rate_hz=100 --output runs/example
./scripts/test.sh
./scripts/build.sh
```

`--venv /path/to/env` selects an environment. Tool defaults can also be set with `PLANET_VENV`, `PLANET_PYTHON` and `PLANET_WHEELHOUSE`. `bootstrap.sh` installs the two local packages; `setup.sh --wheelhouse PATH` provides the wheel-based workflow used by the other Planet repositories.

## Configuration

```yaml
extends: ./defaults.yaml
compose:
  site: ./site.yaml
service:
  rate_hz: 50
```

Composition applies `extends` in order, then `robot`, `backend`, `task`, `site`, `experiment`, the current file and CLI overrides. Mappings merge recursively; lists and scalars replace. Duplicate keys, inheritance cycles, missing resources and unknown override fields raise configuration errors. Each service validates its own domain schema after composition.

```python
from planet_config import load_config

config = load_config("site.yaml", overrides=["service.rate_hz=100"])
config.freeze("runs/site")
```

`ResolvedConfig.path()` resolves a resource relative to the file that declared it, including through inheritance. `pkg://` references installed package resources; `artifact://` references explicit files with SHA256 checks. Snapshots include the effective YAML, declaration provenance, overrides and digest.

## Protocols and consumers

The [protocol package](packages/planet-protocol/README.md) defines `planet.operator.v1`, `planet.joint-target.v1` and `planet.localization.v1`, as well as the PLNJ binary format. The receiver owns execution and state transitions; clients submit input or perform read-only discovery.

PlanetJoystick uses configuration and protocol clients. PlanetRecord and PlanetRelay use configuration. planet-rally composes those services. Cadence consumes these packages and implements the execution-side adapters; it retains its old package names and wire schemas as compatibility adapters. Planet packages never import those adapters.

## Development and ownership

`source-workspace.json` lists the two packages in this repository. There are no submodules. Source and wheel installations are checked independently, including a standard-library-only protocol test.

Maintained by **Renforce Dynamics** under the MIT license.
