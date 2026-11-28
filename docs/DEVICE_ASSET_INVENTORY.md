# Device Asset Inventory — ArmPi Ultra / PiPER X / AR5

> Status: **read-only inventory (2026-11-28)**. No file was moved, deleted or
> copied. Private vendor assets are listed by category and stay outside the
> repository; they are not committed or pushed.

## 1. Rules

- **Device Model vs Device Instance.** A device profile ID names the model
  (`hiwonder.armpi-ultra`, `agilex.piper-x`, `rokae.ar5`). A real unit is an
  instance (e.g. `hiwonder.armpi-ultra@armpi-lab-01`); the `@instance` part is
  not part of the registry ID and must be recorded in deployment metadata.
- **DOF is an attribute, not a name.** Five/six/seven axes never replace the
  vendor + model ID.
- Missing or unverified values are explicit (`unverified`, `not recorded`,
  `data_missing`), never guessed.
- Vendor SDKs, manuals, calibration and raw data are checked for license and
  confidentiality before any public commit. Paths below are categories, not
  publishable links.

## 2. ArmPi Ultra (5-DoF, reference)

| Field | Value |
|---|---|
| Model ID | `hiwonder.armpi-ultra` |
| Vendor / product | Hiwonder / ArmPi Ultra |
| DOF | 5 (arm) + gripper |
| Status | **reference**; ArmPi Ultra × ore_sorting is the only full reference integration |
| Device profile | `<workspace>/jcheng-devices/registry/devices/hiwonder.armpi-ultra*.yaml` (public) |
| Deployment profile | `<workspace>/jcheng-system/configs/robots/armpi_ultra/{profile,readonly_mapping,safety_overlay}.yaml` (public; runtime authority) |
| Simulation | `<workspace>/jcheng-simulation/ros2_ws/src/jcheng_simulation_robots/robots/armpi_ultra/` (public, simplified) |
| Vendor source | `<local-assets>/vendor-armpi-ultra/` (~16 GB, vendor proprietary, **private**) |
| Manuals | `<local-assets>/armpi-ultra-manuals/` (~11 MB PDF, copyrighted, **private**) |
| Calibration | `<workspace>/calibration/` and perception evidence (private; not committed) |
| Datasets | `<workspace>/perception_datasets/` (private; not committed) |
| License | Vendor runtime/assets proprietary; no vendor code or mesh in the repos |
| Verification | Partially verified on hardware (see system/perception acceptance); device limits unmeasured |

## 3. PiPER X (6-DoF, candidate)

| Field | Value |
|---|---|
| Model ID | `agilex.piper-x` |
| Vendor / product | AgileX / PiPER X |
| DOF | 6 + prismatic gripper |
| Status | **candidate**; registration and offline assets only |
| Device profile | `<workspace>/jcheng-devices/registry/devices/agilex.piper-x.yaml` (public; unverified) |
| System profile | `<workspace>/jcheng-system/configs/robots/piper_x/profile.yaml` (simulation-only, no servo IDs) |
| Simulation | `<workspace>/jcheng-simulation/ros2_ws/src/jcheng_simulation_robots/robots/piper_x/` (URDF/world/controllers) |
| Research record | `<workspace>/jcheng-research/references/manipulation/piper-x-assets.md` and `reports/` (public) |
| Local asset cache | `<local-assets>/piper_x/` (618 files, ~38.7 MB, git-ignored outside repo; `PROVENANCE.json` + `SHA256SUMS`) |
| Vendor repos | `agx_arm_urdf` MIT, `agx_arm_ros` MIT, `pyAgxArm` LGPL-3.0, `piper_sdk` MIT; record commits in the research reference |
| License | Mixed MIT/LGPL; do not bulk-copy LGPL code into the repo; keep notices and use an external cache |
| Verification | **Unverified on hardware**; joint limits cross-checked between MIT URDF and official SDK, but no unit was present |

## 4. Rokae AR5 family + AR5L / AR5R variants (7-DoF, planned)

| Field | Value |
|---|---|
| Family ID | `rokae.ar5` (family reference only; not a physical unit) |
| Unit model IDs | `rokae.ar5l` (left), `rokae.ar5r` (right) |
| Vendor / product | Rokae / AR5 family; AR5L left, AR5R right |
| Official source | <https://www.rokae.com/en/product/show/595/> (accessed 2026-11-28) |
| DOF | 7 (vendor-public; previous owner statement consistent) |
| Vendor-public facts | 7 DOF; 5 kg rated payload; 683 mm operating radius; EtherCAT; joint torque sensors standard; published joint ranges (axis1 ±178°, axis2 ±120°, axis3 ±178°, axis4 -60…145°, axis5 ±178°, axis6 ±60°, axis7 ±90°) |
| Status | Family: planned / `data_status: partial`; units: planned / `data_status: missing` |
| Device profiles | `rokae.ar5.yaml` (family facts), `rokae.ar5l.yaml`, `rokae.ar5r.yaml` (unit placeholders) |
| Unit source | ROKAE ROS 2 manual confirms AR5L/AR5R model identifiers and dual-arm context |
| SDK / URDF / control adapter | **not found** in the scanned workspace |
| Calibration / data | **not found** |
| Local mention | A WeChat training note references a `rokae_1119` dataset; it is not a device asset and was not copied |
| License | Product-page facts are cited, not copied; no vendor SDK/URDF/manual is present or committed |
| Verification | **Unverified on hardware**; joint signs, velocity, acceleration, payload at reach, repeatability and the ecosystem control interface are not locally verified |

The owner's physical system is a dual-arm pair: left `AR5L`, right `AR5R`.
Variant-specific mirroring, joint signs, limits, SDK/URDF, calibration and
instance records are absent. Do not plan, limit-check or deploy either unit
from these profiles. The family profile is not a substitute for a unit.

## 5. Cross-device facts

| Attribute | ArmPi Ultra | PiPER X | AR5 |
|---|---|---|---|
| DOF | 5 + gripper | 6 + prismatic gripper | 7 (family vendor-public; AR5L/AR5R units) |
| Interface | vendor bus servos | CAN 1 Mbps (declared) | EtherCAT (vendor-public; no local adapter) |
| Runtime adapter | system vendor bridge (existing) | none | none; two unit variants L/R |
| Full reference integration | **yes** | no | no |
| Public assets committed | declarative profiles only | declarative profiles only | declarative profile with vendor-public facts |
| Private assets | vendor tree, manuals, calibration | external cache, vendor repos | none found |

## 6. Non-goals

- No new runtime adapter for PiPER X or AR5 in this sprint.
- No copying vendor SDK/URDF/mesh/manual into a public repo.
- No claim that the three arms are interchangeable; each has a distinct
  kinematic and control model.

## Related

- [Device registry](DEVICE_REGISTRY.md)
- [Integration boundary](INTEGRATION.md)
- [Phase 2 design](https://github.com/JCHENG-Robotics/.github/blob/main/docs/boundary-consolidation/24-phase2-source-of-truth-design.md)
