# Device assets

> Status: **Experimental** as of 2026-11-27, v0.1.0.
> This directory defines the asset layout. No asset is committed yet.

Planned subdirectories (one per registered `<vendor>.<device>` id):

```text
assets/
├── urdf/<vendor>.<device>/
├── xacro/<vendor>.<device>/
├── calibration/<vendor>.<device>/
├── hardware/<vendor>.<device>/
└── simulation/<vendor>.<device>/
```

Rules:

- The source of every asset is recorded in `provenance.yaml` with a license,
  retrieval date, transformation note and SHA-256.
- Text descriptions may be committed after review. Binary meshes, recordings
  and model weights stay outside the repository.
- The vendor tree on the robot is read-only; assets are copied out, never
  edited in place.
- A device profile references an asset by a repository-relative path only after
  the asset review closes.

See [docs/ASSET_LAYOUT.md](../docs/ASSET_LAYOUT.md) for the full standard.
