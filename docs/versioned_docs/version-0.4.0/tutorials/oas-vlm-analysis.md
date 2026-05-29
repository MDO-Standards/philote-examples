---
sidebar_position: 2
title: OAS VLM Analysis
---

# OpenAeroStruct VLM Analysis

This tutorial demonstrates how to wrap an entire OpenMDAO Group -- the OpenAeroStruct (OAS) vortex-lattice method (VLM) aerodynamic solver -- as a single Philote discipline using the `OpenMdaoSubProblem` class. Unlike the NACA/XFOIL example, which wraps individual tools as `ExplicitDiscipline` subclasses, this approach packages a complete analysis pipeline (geometry + aerodynamics) into one gRPC-servable discipline.

By the end of this tutorial you will be able to:

- Wrap an OpenMDAO Group as a Philote discipline using `OpenMdaoSubProblem`.
- Serve the OAS VLM solver over gRPC.
- Run a VLM aerodynamic analysis from an OpenMDAO client.
- Customize the wing geometry and surface properties.

## Prerequisites

### Install the package

From the repository root:

```bash
pip install -e .
```

This installs `philote-mdo`, `openmdao`, `openaerostruct`, and `numpy` as dependencies.

## Architecture Overview

The example wraps two OAS components inside a single Philote discipline:

```
┌─────────────────────────────────────────────────────┐
│  OasDiscipline (Philote gRPC server, port 50051)    │
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

The `OasDiscipline` class inherits from `OpenMdaoSubProblem`, which wraps an entire `om.Problem` as a Philote explicit discipline. Variable mappings translate between the Philote interface (flat inputs/outputs) and the internal OpenMDAO problem paths.

## Running the Analysis

### All-in-one script

The quickest way to run the example starts the server in-process, connects via gRPC, runs the analysis, and prints the results:

```bash
cd examples/oas_vlm
python run_analysis.py
```

This evaluates a rectangular wing (10 m span, 1 m chord, 7 spanwise panels) at the following flight conditions: v = 248.136 m/s, alpha = 5 deg, M = 0.84, Re = 1e6/m, rho = 0.38 kg/m^3. Expected output:

```
OAS VLM analysis: v=248.136 m/s, alpha=5.0 deg, M=0.84, Re=1e+06/m, rho=0.38 kg/m^3
  CL = ...
  CD = ...
  CM = [...]
```

### Standalone server

To run the discipline as a standalone gRPC server for integration into larger workflows:

**Terminal 1** -- Start the server:

```bash
python server.py
```

Output:

```
OAS VLM server started. Listening on port 50051.
```

**Terminal 2** -- Connect from a client:

```python
from run_analysis import run

cl, cd, cm = run(start_server=False)
```

## Customizing the Wing

### Mesh configuration

Pass a `mesh_dict` to `OasDiscipline` to change the wing planform:

```python
from philote_examples import OasDiscipline

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

### Surface properties

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

## Understanding the Code

### The `OpenMdaoSubProblem` pattern

Where the NACA/XFOIL example wraps external executables using `ExplicitDiscipline`, this example takes advantage of the fact that OAS is already an OpenMDAO Group. The `OpenMdaoSubProblem` class handles the wrapping automatically:

1. **Create an `om.Group`** (`OasAeroGroup`) that contains the solver components and their internal connections.
2. **Subclass `OpenMdaoSubProblem`** (`OasDiscipline`) and in the constructor:
   - Generate the mesh and build the surface dictionary.
   - Call `self.add_group(group)` to embed the Group in an internal `om.Problem`.
   - Call `self.add_mapped_input()` and `self.add_mapped_output()` to define the Philote-level interface.

At runtime, `compute()` copies inputs into the internal problem, calls `run_model()`, and copies outputs back -- all handled by the base class.

### Key variable mappings

| Philote name | OpenMDAO path | Shape | Units |
|--------------|---------------|-------|-------|
| `v` | `v` | (1,) | m/s |
| `alpha` | `alpha` | (1,) | deg |
| `Mach_number` | `Mach_number` | (1,) | -- |
| `re` | `re` | (1,) | 1/m |
| `rho` | `rho` | (1,) | kg/m^3 |
| `cg` | `cg` | (3,) | m |
| `CL` | `aero_point_0.wing_perf.CL` | (1,) | -- |
| `CD` | `aero_point_0.wing_perf.CD` | (1,) | -- |
| `CM` | `aero_point_0.CM` | (3,) | -- |

## Troubleshooting

**Port already in use**
The default port is 50051. If another process is using it, stop it or change the `PORT` constant in the scripts.

**OpenAeroStruct not installed**
Run `pip install -e .` from the repository root to install all dependencies including `openaerostruct`.
