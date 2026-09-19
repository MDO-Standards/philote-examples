---
sidebar_position: 3
title: OAS Aerostructural Analysis
---

# OpenAeroStruct Aerostructural Analysis

This tutorial demonstrates two approaches for running an OAS aerostructural analysis through Philote: a **monolithic** discipline that wraps the full coupled analysis, and a **split** decomposition with geometry, aerodynamics, and structures as three independent gRPC services coupled on the client side.

By the end of this tutorial you will be able to:

- Wrap a coupled OAS aerostructural analysis as a single Philote discipline.
- Decompose the analysis into three separate disciplines with client-side coupling.
- Configure wing geometry and material properties via discipline options.
- Run both approaches and compare results.

## Prerequisites

From the repository root:

```bash
pip install -e .
```

This installs `philote-mdo`, `openmdao`, `openaerostruct`, and `numpy` as dependencies.

## Monolithic Example

### Architecture

The `OasAerostructDiscipline` wraps the complete OAS `AerostructGeometry` + `AerostructPoint` pipeline as a single Philote discipline. The internal `NonlinearBlockGS` solver handles the aero-structural coupling automatically.

```
┌──────────────────────────────────────────────────────────────┐
│  OasAerostructDiscipline (port 50051)                        │
│                                                              │
│  AerostructGeometry ──▶ AerostructPoint (coupled VLM + FEM)  │
│                                                              │
│  11 inputs ──▶ 6 outputs                                     │
└──────────────────────────────────────────────────────────────┘
```

### Running the analysis

```bash
cd examples/oas_aerostruct
python run_analysis.py
```

Expected output:

```
OAS aerostructural analysis: v=248.136 m/s, alpha=5.0 deg, M=0.84, Re=1e+06/m, rho=0.38 kg/m^3
  CL             = 0.5700
  CD             = 0.037955
  CM             = [0.0000, -0.7041, 0.0000]
  Fuel burn      = 241347.34 kg
  Failure        = -0.8922
  Structural mass = 252490.91 kg
```

### Standalone server

**Terminal 1:**

```bash
python server.py
```

**Terminal 2:**

```python
from run_analysis import run

cl, cd, cm, fuelburn, failure, struct_mass = run(start_server=False)
```

### Key inputs and outputs

**Inputs** -- flight conditions and mission parameters:

| Name | Units | Description |
|------|-------|-------------|
| `v` | m/s | Freestream velocity |
| `alpha` | deg | Angle of attack |
| `Mach_number` | -- | Mach number |
| `re` | 1/m | Reynolds number per unit length |
| `rho` | kg/m^3 | Air density |
| `CT` | 1/s | Thrust-specific fuel consumption |
| `R` | m | Range |
| `W0` | kg | Operating empty weight |
| `speed_of_sound` | m/s | Speed of sound |
| `load_factor` | -- | Load factor |
| `empty_cg` | m | Empty-weight center of gravity (3-vector) |

**Outputs:**

| Name | Description |
|------|-------------|
| `CL` | Lift coefficient |
| `CD` | Drag coefficient |
| `CM` | Moment coefficient (3-vector) |
| `fuelburn` | Fuel burn (kg) |
| `failure` | Structural failure index (< 0 means safe) |
| `structural_mass` | Structural mass (kg) |

## Split Example

### Architecture

The split example decomposes the analysis into three independent Philote disciplines:

```
                    ┌──────────────┐
                    │  Geometry    │ (port 50051)
                    │  twist_cp    │
                    │  thickness_cp│
                    └──────┬───────┘
           mesh, nodes,    │    stiffness, radius,
           t_over_c        │    thickness
              ┌────────────┴────────────┐
              ▼                         ▼
   ┌──────────────────┐     ┌──────────────────┐
   │  Aerodynamics    │     │   Structures     │
   │  (port 50052)    │     │   (port 50053)   │
   │                  │loads│                  │
   │  VLM + disp/load │────▶│  Beam FEM solve  │
   │  transfer        │◀────│                  │
   │                  │disp │                  │
   └──────────────────┘     └──────────────────┘

   Coupled via NonlinearBlockGS (client-side)
```

The **geometry** discipline runs once to produce the mesh and structural setup. The **aero** and **struct** disciplines iterate inside a coupled group until the displacements and loads converge.

### Running the analysis

```bash
cd examples/oas_aerostruct_split
python run_analysis.py
```

Expected output:

```
Split OAS aerostructural analysis: v=248.136 m/s, alpha=5.0 deg, M=0.84, Re=1e+06/m, rho=0.38 kg/m^3
  CL      = 0.5700
  CD      = 0.037955
  Failure = -0.8922
```

Results match the monolithic case exactly.

### Standalone servers

**Terminal 1:** `python geom_server.py`
**Terminal 2:** `python aero_server.py`
**Terminal 3:** `python struct_server.py`
**Terminal 4:**

```python
from run_analysis import run

cl, cd, failure = run(start_servers=False)
```

### Client-side coupling

The client script assembles the three disciplines in OpenMDAO:

```python
# Coupled group with Gauss-Seidel solver
coupled = om.Group()
coupled.add_subsystem("struct", RemoteExplicitComponent(channel=struct_channel))
coupled.add_subsystem("aero", RemoteExplicitComponent(channel=aero_channel))

coupled.connect("aero.loads", "struct.loads")
coupled.connect("struct.disp", "aero.disp")

coupled.nonlinear_solver = om.NonlinearBlockGS(use_aitken=True)
coupled.nonlinear_solver.options["maxiter"] = 100
coupled.nonlinear_solver.options["atol"] = 1e-7
```

The subsystem order (`struct` before `aero`) matches the execution order inside OAS's `CoupledAS` group, ensuring consistent convergence behavior.

### Initializing coupling variables

`RemoteExplicitComponent` initializes all inputs to 1.0 by default. For correct convergence, coupling variables must be zero-initialized after `prob.setup()`:

```python
prob.set_val("coupled.aero.disp", np.zeros((ny, 6)))
prob.set_val("coupled.struct.loads", np.zeros((ny, 6)))
```

Geometry design variables must also be set to their correct baseline values (e.g., `twist_cp` from `generate_mesh()`, `thickness_cp`).

## Large Mesh Examples

Both monolithic and split examples have large-mesh counterparts in `examples/oas_aerostruct_large/` and `examples/oas_aerostruct_split_large/` using a 21x7 CRM wing mesh. These demonstrate how to configure disciplines with custom mesh options:

```python
MESH_DICT = {
    "num_y": 21,
    "num_x": 7,
    "wing_type": "CRM",
    "symmetry": True,
    "num_twist_cp": 5,
}

discipline = OasAerostructDiscipline(mesh_dict=MESH_DICT)
```

Run them the same way:

```bash
cd examples/oas_aerostruct_large
python run_analysis.py
```

## Configuring via gRPC Options

All OAS disciplines support runtime configuration through Philote options. Instead of passing constructor arguments, a remote client can send options before setup:

```python
client.send_options({
    "mesh_dict": {
        "num_y": 21,
        "num_x": 7,
        "wing_type": "CRM",
        "symmetry": True,
    },
    "surface": {
        "E": 73.1e9,
        "G": 33.0e9,
        "with_viscous": True,
    },
})
```

The `mesh_dict` option controls wing planform generation. The `surface` option overrides default material and aerodynamic properties, using the same keys as the OAS surface dictionary.

## Troubleshooting

**Port already in use**
The default ports are 50051--50053. If other processes are using them, stop them or change the `PORT` / `GEOM_PORT` / `AERO_PORT` / `STRUCT_PORT` constants.

**Convergence failure**
If the split example fails to converge, check that coupling variables are zero-initialized and geometry design variables are set to correct baseline values after `prob.setup()`.

**Mismatched results between monolithic and split**
Ensure all three split disciplines use the same `mesh_dict` as the monolithic discipline. Different mesh sizes produce different variable shapes and will cause connection errors or incorrect results.
