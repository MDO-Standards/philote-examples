---
sidebar_position: 3
title: OasDiscipline
---

# OasDiscipline

```python
from philote_examples import OasDiscipline
```

Philote discipline wrapping an OpenAeroStruct VLM aerodynamic analysis. Accepts flight conditions as inputs and returns aerodynamic coefficients. The wing geometry (mesh and surface properties) is fixed at construction time.

**Inherits from:** `philote_mdo.openmdao.OpenMdaoSubProblem`

## Constructor

```python
OasDiscipline(mesh_dict=None, surface_options=None)
```

### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `mesh_dict` | `dict` or `None` | See below | Dictionary passed to `openaerostruct.geometry.utils.generate_mesh` |
| `surface_options` | `dict` or `None` | `None` | Extra entries merged into the OAS surface dictionary |

### Default mesh configuration

When `mesh_dict` is `None`, the following default is used:

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

### Default surface properties

| Property | Default | Description |
|----------|---------|-------------|
| `name` | `"wing"` | Surface name |
| `symmetry` | From `mesh_dict` | Use half-model with symmetry |
| `S_ref_type` | `"wetted"` | Reference area type |
| `fem_model_type` | `"tube"` | FEM model type |
| `CL0` | `0.0` | Baseline lift coefficient |
| `CD0` | `0.0` | Baseline drag coefficient |
| `k_lam` | `0.05` | Fraction of chord with laminar flow |
| `t_over_c_cp` | `[0.15]` | Thickness-to-chord ratio control points |
| `c_max_t` | `0.303` | Chordwise location of max thickness |
| `with_viscous` | `False` | Enable viscous drag estimation |
| `with_wave` | `False` | Enable wave drag estimation |

## Philote Options

| Option | Type | Description |
|--------|------|-------------|
| `mesh_dict` | dict | Overrides `mesh_dict` constructor argument |
| `surface` | dict | Overrides `surface_options` constructor argument |

## Methods

### `initialize()`

Declares `mesh_dict` and `surface` as available Philote options.

### `set_options(options)`

Stores option values from the client. Called automatically by the Philote framework when a client sends options via `send_options()`.

### `setup()`

Builds the discipline (mesh generation, group creation, variable mapping) then calls the base class `setup()` to initialize the internal OpenMDAO problem.

### `_build_discipline()`

Internal method called by `setup()`. Performs all setup:

1. **Generates the mesh** using `openaerostruct.geometry.utils.generate_mesh`.
2. **Builds the surface dictionary** with default properties merged with `surface_options`.
3. **Creates the OpenMDAO Group** (`OasAeroGroup`) and adds it via `self.add_group()`.
4. **Maps inputs** from the Philote interface to the internal problem.
5. **Maps outputs** from the internal problem to the Philote interface.

## Mapped Inputs

| Philote Name | OpenMDAO Path | Shape | Units |
|--------------|---------------|-------|-------|
| `v` | `v` | (1,) | m/s |
| `alpha` | `alpha` | (1,) | deg |
| `Mach_number` | `Mach_number` | (1,) | -- |
| `re` | `re` | (1,) | 1/m |
| `rho` | `rho` | (1,) | kg/m^3 |
| `cg` | `cg` | (3,) | m |

## Mapped Outputs

| Philote Name | OpenMDAO Path | Shape | Units |
|--------------|---------------|-------|-------|
| `CL` | `aero_point_0.wing_perf.CL` | (1,) | -- |
| `CD` | `aero_point_0.wing_perf.CD` | (1,) | -- |
| `CM` | `aero_point_0.CM` | (3,) | -- |

---

# OasAeroGroup

```python
from philote_examples.oas.oas_discipline import OasAeroGroup
```

OpenMDAO Group containing OAS Geometry + AeroPoint for one lifting surface. An `IndepVarComp` exposes six flow-condition variables at the group level. Explicit connections route them to AeroPoint and wire the mesh and thickness-to-chord ratio from Geometry.

**Inherits from:** `openmdao.api.Group`

## Constructor

```python
OasAeroGroup(surface=surface_dict)
```

The `surface` dictionary is passed via OpenMDAO options.

### Options

| Name | Type | Description |
|------|------|-------------|
| `surface` | `dict` | OAS surface dictionary (must include `"name"`, `"mesh"`, etc.) |

## Internal Components

| Subsystem | Class | Description |
|-----------|-------|-------------|
| `flow_vars` | `IndepVarComp` | Exposes v, alpha, Mach_number, re, rho, cg |
| `{surface_name}` | `Geometry` | Applies twist/chord/shear to the baseline mesh |
| `aero_point_0` | `AeroPoint` | VLM solver for a single flight condition |

## Internal Connections

- `{name}.mesh` -> `aero_point_0.{name}.def_mesh`
- `{name}.mesh` -> `aero_point_0.aero_states.{name}_def_mesh`
- `{name}.t_over_c` -> `aero_point_0.{name}_perf.t_over_c`
- Flow variables (`v`, `alpha`, etc.) -> `aero_point_0.{var}`

## Example

```python
from philote_examples import OasDiscipline
from philote_mdo.general import run_server

# Default rectangular wing
discipline = OasDiscipline()
run_server(discipline, port=50051)

# CRM wing with viscous drag
discipline = OasDiscipline(
    mesh_dict={
        "num_y": 13,
        "num_x": 3,
        "wing_type": "CRM",
        "symmetry": True,
        "num_twist_cp": 5,
    },
    surface_options={
        "with_viscous": True,
        "CD0": 0.015,
    },
)
run_server(discipline, port=50051)
```
