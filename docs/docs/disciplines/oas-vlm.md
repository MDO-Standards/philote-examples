---
sidebar_position: 3
title: OpenAeroStruct VLM
---

# OpenAeroStruct VLM

The `OasDiscipline` wraps a complete [OpenAeroStruct](https://mdolab-openaerostruct.readthedocs-hosted.com/) (OAS) vortex-lattice method (VLM) aerodynamic analysis as a single Philote discipline. Unlike the NACA and XFOIL disciplines which subclass `ExplicitDiscipline`, this discipline uses the `OpenMdaoSubProblem` pattern to package an entire OpenMDAO Group as a gRPC-servable discipline.

## Architecture

The discipline contains two internal components:

```
┌─────────────────────────────────────────────────────┐
│  OasDiscipline (Philote gRPC server)                │
│                                                     │
│  ┌──────────────┐       ┌────────────────────────┐  │
│  │   Geometry    │──mesh──▶    AeroPoint (VLM)    │  │
│  │  (wing shape) │       │  (vortex-lattice solve)│  │
│  └──────────────┘       └────────────────────────┘  │
│                                                     │
│  Inputs:                    Outputs:                │
│    v          (m/s)           CL  (scalar)          │
│    alpha      (deg)           CD  (scalar)          │
│    Mach_number                CM  (3-vector)        │
│    re         (1/m)                                 │
│    rho        (kg/m^3)                              │
│    cg         (3-vector, m)                         │
└─────────────────────────────────────────────────────┘
```

**Geometry** applies design variables (twist, chord, shear) to a baseline mesh.

**AeroPoint** runs the VLM aerodynamic analysis on the deformed mesh at the specified flight condition and computes lift, drag, and moment coefficients.

## The `OpenMdaoSubProblem` Pattern

Where the NACA/XFOIL examples wrap external executables using `ExplicitDiscipline`, this example takes advantage of the fact that OAS is already an OpenMDAO Group. The `OpenMdaoSubProblem` base class handles the wrapping:

1. **Create an `om.Group`** (`OasAeroGroup`) containing the solver components and their internal connections.
2. **Subclass `OpenMdaoSubProblem`** and call `self.add_group(group)` to embed the Group in an internal `om.Problem`.
3. **Map inputs/outputs** using `self.add_mapped_input()` and `self.add_mapped_output()` to define the Philote-level interface.

At runtime, `compute()` copies inputs into the internal problem, calls `run_model()`, and copies outputs back -- all handled by the base class.

### When to use which pattern

| Use case | Recommended class |
|----------|-------------------|
| Wrapping an external executable (file I/O) | `ExplicitDiscipline` |
| Wrapping an OpenMDAO Group or Component | `OpenMdaoSubProblem` |
| Need fine-grained control over compute logic | `ExplicitDiscipline` |
| Solver already built as an OpenMDAO model | `OpenMdaoSubProblem` |

## Inputs and Outputs

### Inputs

| Philote Name | OpenMDAO Path | Shape | Units | Description |
|--------------|---------------|-------|-------|-------------|
| `v` | `v` | (1,) | m/s | Freestream velocity |
| `alpha` | `alpha` | (1,) | deg | Angle of attack |
| `Mach_number` | `Mach_number` | (1,) | -- | Mach number |
| `re` | `re` | (1,) | 1/m | Reynolds number per unit length |
| `rho` | `rho` | (1,) | kg/m^3 | Air density |
| `cg` | `cg` | (3,) | m | Center of gravity position |

### Outputs

| Philote Name | OpenMDAO Path | Shape | Units | Description |
|--------------|---------------|-------|-------|-------------|
| `CL` | `aero_point_0.wing_perf.CL` | (1,) | -- | Lift coefficient |
| `CD` | `aero_point_0.wing_perf.CD` | (1,) | -- | Drag coefficient |
| `CM` | `aero_point_0.CM` | (3,) | -- | Moment coefficient vector |

## Mesh Configuration

Pass a `mesh_dict` to `OasDiscipline` to change the wing planform:

```python
from philote_examples import OasDiscipline

# Default: rectangular wing (10 m span, 1 m chord, 7 spanwise panels)
discipline = OasDiscipline()

# CRM wing with 13 spanwise panels
discipline = OasDiscipline(
    mesh_dict={
        "num_y": 13,
        "num_x": 3,
        "wing_type": "CRM",
        "symmetry": True,
        "num_twist_cp": 5,
    }
)
```

The default mesh configuration is:

```python
{
    "num_y": 7,
    "num_x": 2,
    "wing_type": "rect",
    "symmetry": True,
    "span": 10.0,
    "root_chord": 1.0,
}
```

## Surface Properties

Use `surface_options` to override defaults like viscous drag or baseline CD:

```python
discipline = OasDiscipline(
    surface_options={
        "with_viscous": True,
        "CD0": 0.015,
        "with_wave": True,
    }
)
```

The default surface properties include:

| Property | Default | Description |
|----------|---------|-------------|
| `CL0` | 0.0 | Baseline lift coefficient |
| `CD0` | 0.0 | Baseline drag coefficient |
| `k_lam` | 0.05 | Fraction of chord with laminar flow |
| `t_over_c_cp` | [0.15] | Thickness-to-chord ratio |
| `c_max_t` | 0.303 | Chordwise location of max thickness |
| `with_viscous` | False | Enable viscous drag estimation |
| `with_wave` | False | Enable wave drag estimation |

## Example Usage

```python
from philote_examples import OasDiscipline
from philote_mdo.general import run_server

# Create the discipline with default rectangular wing
discipline = OasDiscipline()

# Start the gRPC server on port 50051
run_server(discipline, port=50051)
```
