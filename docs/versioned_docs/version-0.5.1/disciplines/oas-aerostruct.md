---
sidebar_position: 4
title: OpenAeroStruct Aerostructural
---

# OpenAeroStruct Aerostructural

The aerostructural disciplines wrap a coupled [OpenAeroStruct](https://mdolab-openaerostruct.readthedocs-hosted.com/) (OAS) vortex-lattice method (VLM) + finite-element structural analysis as Philote disciplines. Two decomposition strategies are provided: a **monolithic** approach that wraps the entire coupled analysis as a single discipline, and a **split** approach that exposes geometry, aerodynamics, and structures as three independent disciplines coupled on the client side.

## Monolithic Architecture

The `OasAerostructDiscipline` packages the full OAS `AerostructGeometry` + `AerostructPoint` pipeline -- including the internal Gauss-Seidel coupling loop -- as a single Philote discipline.

```
┌──────────────────────────────────────────────────────────────────────┐
│  OasAerostructDiscipline (Philote gRPC server)                       │
│                                                                      │
│  ┌────────────────┐     ┌──────────────────────────────────────────┐ │
│  │ AerostructGeom  │────▶│         AerostructPoint                  │ │
│  │ (mesh + FEM     │     │  ┌─────────────────────────────────┐    │ │
│  │  setup)         │     │  │  CoupledAS (NonlinearBlockGS)   │    │ │
│  └────────────────┘     │  │  struct ↔ disp_xfer ↔ VLM ↔ loads│    │ │
│                          │  └─────────────────────────────────┘    │ │
│                          └──────────────────────────────────────────┘ │
│                                                                      │
│  Inputs:                         Outputs:                            │
│    v, alpha, Mach_number           CL, CD, CM                        │
│    re, rho, CT, R, W0             fuelburn, failure                  │
│    speed_of_sound                  structural_mass                   │
│    load_factor, empty_cg                                             │
└──────────────────────────────────────────────────────────────────────┘
```

OAS handles the internal aero-structural coupling (displacement transfer, VLM solve, load transfer, beam solve) automatically via its built-in `NonlinearBlockGS` solver. The Philote discipline simply exposes flight conditions and mission parameters as inputs and performance metrics as outputs.

## Split Architecture

The split approach decomposes the analysis into three disciplines that can run as separate gRPC services:

```
┌──────────────┐
│  OasGeom     │──mesh, nodes, stiffness──┐
│  Discipline  │                          │
└──────────────┘                          ▼
                            ┌─────────────────────────┐
                            │   Coupled Group (client) │
                            │   NonlinearBlockGS       │
                            │                          │
                            │  ┌──────────┐  loads     │
                            │  │  Aero    │──────────▶│
                            │  │ Discipline│◀──────────│
                            │  └──────────┘   disp    │
                            │                          │
                            │  ┌──────────┐            │
                            │  │ Struct   │            │
                            │  │Discipline│            │
                            │  └──────────┘            │
                            └─────────────────────────┘
```

| Discipline | Class | Role |
|-----------|-------|------|
| Geometry | `OasGeomDiscipline` | Mesh generation, FEM setup, structural mass |
| Aerodynamics | `OasSplitAeroDiscipline` | Displacement transfer, VLM solve, load transfer |
| Structures | `OasSplitStructDiscipline` | Beam finite-element solve |

The client assembles the three disciplines in OpenMDAO, connecting geometry outputs to both aero and structures, and wiring the coupling variables (`loads` and `disp`) inside a `NonlinearBlockGS`-driven coupled group.

## Coupling Variables

The aero-structural coupling is mediated by two variables at the structural nodes:

| Variable | Shape | Units | Direction |
|----------|-------|-------|-----------|
| `loads` | (ny, 6) | N, N*m | Aero → Struct |
| `disp` | (ny, 6) | m, rad | Struct → Aero |

Where `ny` is the number of spanwise nodes (with symmetry: `(num_y + 1) // 2`). Each row contains 3 force and 3 moment components.

## When to Use Which Approach

| Criterion | Monolithic | Split |
|-----------|-----------|-------|
| Simplest setup | Yes | -- |
| Fewest gRPC calls | Yes (1 discipline) | No (3 disciplines, iterative) |
| Disciplines on separate machines | -- | Yes |
| Different language for each discipline | -- | Yes |
| Custom coupling strategy | -- | Yes |
| Access to intermediate coupling state | -- | Yes |

## Configuration

All aerostructural disciplines accept the same two options, either via constructor arguments or Philote gRPC options:

- **`mesh_dict`** -- dictionary passed to `generate_mesh()` (wing planform, panel counts)
- **`surface`** -- dictionary merged into the OAS surface defaults (material properties, drag flags)

```python
# Constructor (in-process)
discipline = OasAerostructDiscipline(
    mesh_dict={"num_y": 21, "num_x": 7, "wing_type": "CRM", "symmetry": True},
    surface_options={"E": 73.1e9, "G": 33.0e9},
)

# gRPC options (remote)
client.send_options({
    "mesh_dict": {"num_y": 21, "num_x": 7, "wing_type": "CRM", "symmetry": True},
    "surface": {"E": 73.1e9, "G": 33.0e9},
})
```

## Performance

Benchmark results comparing native OAS (direct OpenMDAO) vs Philote gRPC:

| Case | Native (s) | Philote (s) | Overhead |
|---|---|---|---|
| Aerostruct small (5x2) | 0.100 | 0.211 | 112% |
| Aerostruct large (21x7) | 0.181 | 0.232 | 28% |
| Split small (5x2) | 0.146 | 0.282 | 94% |
| Split large (21x7) | 0.175 | 0.405 | 131% |

The monolithic overhead decreases with problem size as computation dominates the fixed gRPC round-trip cost. The split overhead is higher due to iterative gRPC calls during the coupling loop.
