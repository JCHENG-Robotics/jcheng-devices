# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Nothing yet.

### Changed

- Cite the `jcheng-system` per-robot `robot-profile.v1` instances as the
  source of joint ranges and state explicitly that they remain the runtime
  authority. Device profiles describe models and capabilities; they never
  replace or export runtime configuration.

## [0.1.0] — 2026-11-27

### Added

- L3 admission as the ecosystem device library: declarative device and
  capability profiles with `hardware_access: none` and an empty runtime
  surface. Pins `jcheng-interfaces` v0.2.0, contract hash
  `sha256:afca22a4…c35b1c`.
- `registry/registry.yaml` with six device profiles: `hiwonder.armpi-ultra`,
  `hiwonder.armpi-ultra-gripper`, `hiwonder.armpi-ultra-chassis`,
  `intel.realsense-d435i`, `lslidar.m10` and `agilex.piper-x`.
- Seven capability profiles: `arm.position_control`, `arm.joint_feedback`,
  `end_effector.position_control`, `base.velocity_intent`,
  `sensor.rgb_stream`, `sensor.depth_stream` and `sensor.laserscan`.
- `device-profile.v1` and `capability-profile.v1` JSON Schemas with
  category-specific required blocks, per-parameter source and verification
  markers, and relative-path rules for future assets.
- ROS-free validator with identity, schema, cross-reference, kinematics and
  verification checks; `list`, `show`, `validate` and `digest` CLI commands
  with deterministic JSON and explicit exit codes.
- Repository gate, CI workflow, document set and the asset organisation
  standard for URDF/Xacro, calibration, hardware configuration and simulation
  assets.
- Unit and contract tests, including a static boundary scan that rejects
  device, runtime-graph and motion tokens in code and data.
