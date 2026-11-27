# Dependency review

> Status: **Experimental** as of 2026-11-27, v0.1.0.
> Every dependency below is used offline. No ROS package, vendor SDK, network
> client or device library is imported.

## 1. Runtime dependencies

| Package | Pin | Why it is needed | License | Alternative considered |
|---|---|---|---|---|
| `PyYAML` | 6.0.2 | profiles and the registry index are human-edited YAML | MIT | JSON only; rejected because comments and multi-line provenance matter |
| `jsonschema` | 4.26.0 | the schemas are the deliverable; validation must follow them exactly | MIT | hand-written checks; rejected because they drift from the schema |

`jsonschema` pulls transitive packages: `attrs`, `jsonschema-specifications`,
`referencing` and `rpds-py`. All are MIT. They are validation-only and are
installed from PyPI at the pinned version.

There is no ROS dependency. The package imports only the standard library,
`PyYAML` and `jsonschema`. A static test rejects imports of process, network,
serial, CAN, GPIO, camera, USB and robot-runtime modules.

## 2. Test dependencies

| Package | Pin | Role | License |
|---|---|---|---|
| `pytest` | 8.3.4 | unit and contract tests | MIT |

Tests run against the repository files; they do not install the package, open a
device or start a process other than the CLI under test.

## 3. Contract dependency

| Item | Value |
|---|---|
| `jcheng-interfaces` range | `>=0.2,<0.3` |
| Contract hash | `sha256:afca22a42f7163e0351d185d5a8577b0b51f2f3da4b92278f161a4a7d2c35b1c` (v0.2.0) |
| `jcheng-system` API range | `>=0.2,<0.4` (declarative; no call in v0.1.0) |

The manifest pins the released contract. The device profile schemas are
repository-local and are **not** a contract dependency for other repositories
until a reviewed proposal is accepted.

## 4. Data and assets

- No dataset, recording, point cloud or image is in the repository.
- No URDF, Xacro, mesh or calibration file is committed in v0.1.0.
- No vendor code is copied. Profile facts cite in-tree documentation by URL.
- No model weights are present; `/opt/jcheng/models/` is the model location.

## 5. Update policy

1. A runtime dependency update changes `pyproject.toml` and the license table
   in the same pull request.
2. A major-version update requires a review of the changelog and the validation
   behaviour.
3. A schema update is versioned as described in
   [PROFILE_SCHEMA.md](PROFILE_SCHEMA.md); it is never a silent edit to `v1`.
4. A contract range change requires a new `jcheng-interfaces` tag and a
   regenerated lock in the consuming repositories.

## 6. Related

- [README](../README.md)
- [Profile schemas](PROFILE_SCHEMA.md)
- [License review](../LICENSE-REVIEW.md)
- [`jcheng-interfaces`](https://github.com/JCHENG-Robotics/jcheng-interfaces)
