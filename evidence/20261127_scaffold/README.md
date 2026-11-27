# Evidence — 2026-11-27 scaffold and M1

> Status: **pass** as of 2026-11-27 for v0.1.0.
> Scope: offline registry, schemas, validator, CLI, tests and repository gate.
> No device was opened and no motion command was sent.

## Contents

| File | What it records |
|---|---|
| `gate.txt` | `bash scripts/check_repo_gate.sh` output: document set, no license, secret scan, artifact scan, link check, registry validation and tests |
| `pytest.txt` | `python3 -m pytest -q tests` output |
| `README.md` | this summary |

## Commands

```bash
cd /path/to/jcheng-devices
PYTHONPATH=src python3 -m jcheng_devices validate
python3 -m pytest -q tests | tee evidence/20261127_scaffold/pytest.txt
bash scripts/check_repo_gate.sh | tee evidence/20261127_scaffold/gate.txt
```

## Result

- Registry: 6 device profiles, 7 capability profiles, no validation issues.
- Tests: contract, registry failure paths, profile invariants, CLI,
  static hardware boundary and reference-device facts.
- Gate: document set, no `LICENSE`, no secrets, no recordings or weights, links
  resolve, registry validates, tests pass.

## Caveats

- L0/L1 only. There is no mock runtime (L2), no replay (L4) and no hardware
  session (L5).
- Device facts are copied from in-tree documentation and remain
  `partially verified` or `unverified`; this repository measured nothing on a
  device.
- A pass here is not a hardware validation and must not be reported as one.

## Related

- [Acceptance report](../../ACCEPTANCE.md)
- [Roadmap](../../ROADMAP.md)
- [M1 plan](../../docs/M1_PLAN.md)
