# Safety model

> Status: **Experimental** as of 2026-11-27, v0.1.0.
> This repository has no motion authority, no device handle and no runtime.

## 1. Red lines

| Rule | Consequence |
|---|---|
| Never open a real device | No serial, USB, CAN, GPIO or video handle is created in code, tests or tools. |
| Never join a runtime graph | No DDS domain, topic, service, action or node. The manifest runtime surface is empty. |
| Never create an independent control channel | No custom transport, socket or gateway that could carry a command. |
| Never bypass `jcheng-system` | Execution authority, leases, deadman, limits and the stop latch stay with the system layer. |
| Never change a cross-repository interface without review | Contract changes start in `jcheng-interfaces`. |
| Never duplicate another repository's function | Perception, mobile, learning and teleoperation keep their own runtime code. |
| Never migrate or modify another repository's assets | Copy only with provenance and review; vendor trees are read-only. |
| Never fabricate a parameter | An unknown value is omitted or marked `unverified` with a note. |

## 2. Description is not authority

A device profile states what a device is; a capability profile states what it
can do. Neither is a permission:

- a profile limit does not replace a runtime limit;
- a capability does not grant a lease;
- a registry entry does not make a device reachable;
- the presence of a motion-related capability does not create a motion path.

Any consumer must still apply its own safety envelope, and the system layer must
still apply the lease, deadman, limits and stop latch.

## 3. Verification discipline

- `verified` requires per-claim evidence and a date.
- `partially_verified` requires evidence, a date and an explicit statement of
  what remains open.
- `unverified` requires an explanation of what is unknown and why.
- A copied value keeps `verified: false` until it is checked against the
  device, even when the source is another trusted repository.
- Synthetic, mock and replay results are never reported as hardware evidence.
- A failed bound stays failed; it is not replaced by a more favourable number.

v0.1.0 makes no `verified` device claim. The ArmPi Ultra profiles are
`partially_verified` and every per-joint value is `verified: false`.

## 4. Data integrity

- The registry is explicit; no filesystem auto-discovery means a stray file
  cannot silently become a device.
- Every id is unique and equals its file name.
- Every path stays inside `registry/`.
- The digest is deterministic, so a consumer can pin the exact registry content
  it validated.
- The repository gate rejects secrets, oversized files, recordings, weights and
  binary meshes.

## 5. Failure behaviour

Validation fails closed:

- any issue makes `validate` exit 1 and the CI job fail;
- an unreadable index exits 2;
- a missing or malformed profile is an error, not a warning;
- a consumer must treat an invalid profile as absent, never as a default.

## 6. Change control

- A change to safety semantics, categories or verification rules updates
  `README.md`, `ROADMAP.md`, `ACCEPTANCE.md` and this document in one pull
  request.
- A new device category or a profile schema change needs owner review.
- Adding a real device requires a sourced profile; adding a measured value
  requires recorded evidence.
- Real-robot work is authorized separately per session and is never triggered
  by CI or an unattended script.

## 7. What this repository cannot guarantee

- That a described device matches the description. Only a measurement can show
  that.
- Functional safety. The platform has no e-stop, brake, independent encoder or
  self-collision model; this repository does not claim SIL/PL.
- That a vendor document is correct. Vendor claims remain `unverified` until
  checked.
- That a consumer applies its own limits. The system layer owns that
  enforcement.

## 8. Related

- [README](../README.md)
- [Architecture](ARCHITECTURE.md)
- [Integration boundary](INTEGRATION.md)
- [Device registry rules](DEVICE_REGISTRY.md)
- [`jcheng-system` safety documentation](https://github.com/JCHENG-Robotics/jcheng-system/blob/main/docs/SAFETY.md)
- [`.github` hardware workflow](https://github.com/JCHENG-Robotics/.github/blob/main/docs/hardware-workflow.md)
