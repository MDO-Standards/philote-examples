# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-05-16

### Features

- Monolithic aerostructural discipline wrapping the full coupled OAS analysis in a single Philote service.
- Split aerostructural disciplines (geometry, aerodynamics, structures) served as independent gRPC services.
- Large mesh examples (21x7 CRM wing) for VLM and aerostructural analyses.
- Philote options support for all OAS disciplines (mesh_dict and surface configuration via gRPC send_options).
- Benchmark script comparing native OAS vs Philote overhead.
- Documentation for aerostructural disciplines (overview, tutorial, and API reference).

### Changed

- Require philote-mdo >= 0.8.

## [0.2.0] - 2026-04-23

### Fixed

- PyPI publish workflow not triggering after release.

## [0.1.0] - 2026-04-23

### Features

- NACA 4-digit airfoil geometry discipline with analytical gradient support.
- XFOIL wrapper discipline for viscous/inviscid airfoil analysis.
- OpenAeroStruct VLM discipline for vortex-lattice method analysis.
- Docusaurus documentation site with tutorials and API reference.
- CI pipeline with linting (ruff) and testing.
- Pre-commit hooks for code formatting.

[0.1.0]: https://github.com/MDO-Standards/philote-examples/releases/tag/v0.1.0
[0.2.0]: https://github.com/MDO-Standards/philote-examples/releases/tag/v0.2.0
[Unreleased]: https://github.com/MDO-Standards/philote-examples/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/MDO-Standards/philote-examples/releases/tag/v0.3.0
