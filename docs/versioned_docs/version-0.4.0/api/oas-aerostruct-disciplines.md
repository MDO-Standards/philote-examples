---
sidebar_position: 4
title: OAS Aerostructural Disciplines
---

# OasAerostructDiscipline

```python
from philote_examples import OasAerostructDiscipline
```

Philote discipline wrapping a complete OAS coupled aerostructural analysis. The internal `AerostructPoint` group contains a `NonlinearBlockGS` solver that converges the aero-structural coupling automatically. The wing geometry, structural properties, and mesh are configured at construction time or via gRPC options.

**Inherits from:** `philote_mdo.openmdao.OpenMdaoSubProblem`

## Constructor

```python
OasAerostructDiscipline(mesh_dict=None, surface_options=None)
```

### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `mesh_dict` | `dict` or `None` | See below | Dictionary passed to `generate_mesh` |
| `surface_options` | `dict` or `None` | `None` | Extra entries merged into the OAS surface dictionary |

### Default mesh configuration

```python
{
    "num_y": 5,
    "num_x": 2,
    "wing_type": "CRM",
    "symmetry": True,
    "num_twist_cp": 5,
}
```

### Default surface properties

| Property | Default | Description |
|----------|---------|-------------|
| `E` | 70.0e9 | Young's modulus (Pa) |
| `G` | 30.0e9 | Shear modulus (Pa) |
| `yield` | 200.0e6 | Yield stress (Pa), with safety factor 2.5 |
| `mrho` | 3.0e3 | Material density (kg/m^3) |
| `fem_origin` | 0.35 | Chordwise FEM origin |
| `wing_weight_ratio` | 2.0 | Wing weight multiplier |
| `thickness_cp` | [0.1, 0.2, 0.3] | Thickness control points (m) |
| `with_viscous` | True | Enable viscous drag |
| `CD0` | 0.015 | Parasitic drag coefficient |

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

## Mapped Inputs

| Philote Name | OpenMDAO Path | Shape | Units |
|--------------|---------------|-------|-------|
| `v` | `v` | (1,) | m/s |
| `alpha` | `alpha` | (1,) | deg |
| `Mach_number` | `Mach_number` | (1,) | -- |
| `re` | `re` | (1,) | 1/m |
| `rho` | `rho` | (1,) | kg/m^3 |
| `CT` | `CT` | (1,) | 1/s |
| `R` | `R` | (1,) | m |
| `W0` | `W0` | (1,) | kg |
| `speed_of_sound` | `speed_of_sound` | (1,) | m/s |
| `load_factor` | `load_factor` | (1,) | -- |
| `empty_cg` | `empty_cg` | (3,) | m |

## Mapped Outputs

| Philote Name | OpenMDAO Path | Shape | Units |
|--------------|---------------|-------|-------|
| `CL` | `AS_point_0.wing_perf.CL` | (1,) | -- |
| `CD` | `AS_point_0.wing_perf.CD` | (1,) | -- |
| `CM` | `AS_point_0.CM` | (3,) | -- |
| `fuelburn` | `AS_point_0.fuelburn` | (1,) | kg |
| `failure` | `AS_point_0.wing_perf.failure` | (1,) | -- |
| `structural_mass` | `wing.structural_mass` | (1,) | kg |

---

# OasGeomDiscipline

```python
from philote_examples import OasGeomDiscipline
```

Philote discipline wrapping OAS `AerostructGeometry` for the split aerostructural decomposition. Produces mesh, structural nodes, stiffness matrices, and other geometry constants consumed by the aero and structural disciplines.

**Inherits from:** `philote_mdo.openmdao.OpenMdaoSubProblem`

## Constructor

```python
OasGeomDiscipline(mesh_dict=None, surface_options=None)
```

Parameters, defaults, options, and methods follow the same pattern as `OasAerostructDiscipline`.

## Mapped Inputs

| Philote Name | OpenMDAO Path | Shape | Units |
|--------------|---------------|-------|-------|
| `twist_cp` | `twist_cp` | (num_twist_cp,) | deg |
| `thickness_cp` | `thickness_cp` | (num_thickness_cp,) | m |

Inputs are only mapped when the corresponding control points exist in the surface dictionary.

## Mapped Outputs

| Philote Name | OpenMDAO Path | Shape | Units |
|--------------|---------------|-------|-------|
| `mesh` | `wing.mesh` | (nx, ny, 3) | m |
| `nodes` | `wing.nodes` | (ny, 3) | m |
| `t_over_c` | `wing.t_over_c` | (1, ny-1) | -- |
| `local_stiff_transformed` | `wing.local_stiff_transformed` | (ny-1, 12, 12) | -- |
| `radius` | `wing.radius` | (ny-1,) | m |
| `thickness` | `wing.thickness` | (1, ny-1) | m |
| `structural_mass` | `wing.structural_mass` | (1,) | kg |
| `cg_location` | `wing.cg_location` | (3,) | m |

---

# OasSplitAeroDiscipline

```python
from philote_examples import OasSplitAeroDiscipline
```

Philote discipline wrapping the aerodynamic portion of the aerostructural analysis: displacement transfer, VLM geometry, VLM solve, load transfer, and aerodynamic functionals.

**Inherits from:** `philote_mdo.openmdao.OpenMdaoSubProblem`

## Constructor

```python
OasSplitAeroDiscipline(mesh_dict=None, surface_options=None)
```

Parameters, defaults, options, and methods follow the same pattern as `OasAerostructDiscipline`.

## Mapped Inputs

| Philote Name | OpenMDAO Path | Shape | Units | Source |
|--------------|---------------|-------|-------|--------|
| `v` | `v` | (1,) | m/s | Flow condition |
| `alpha` | `alpha` | (1,) | deg | Flow condition |
| `Mach_number` | `Mach_number` | (1,) | -- | Flow condition |
| `re` | `re` | (1,) | 1/m | Flow condition |
| `rho` | `rho` | (1,) | kg/m^3 | Flow condition |
| `mesh` | `mesh` | (nx, ny, 3) | m | Geometry discipline |
| `nodes` | `nodes` | (ny, 3) | m | Geometry discipline |
| `t_over_c` | `t_over_c` | (1, ny-1) | -- | Geometry discipline |
| `disp` | `disp` | (ny, 6) | -- | Structural discipline (coupling) |

## Mapped Outputs

| Philote Name | OpenMDAO Path | Shape | Units | Destination |
|--------------|---------------|-------|-------|-------------|
| `loads` | `loads` | (ny, 6) | -- | Structural discipline (coupling) |
| `CL` | `CL` | (1,) | -- | Performance output |
| `CD` | `CD` | (1,) | -- | Performance output |

---

# OasSplitStructDiscipline

```python
from philote_examples import OasSplitStructDiscipline
```

Philote discipline wrapping the structural portion of the aerostructural analysis: spatial beam finite-element solve and failure computation.

**Inherits from:** `philote_mdo.openmdao.OpenMdaoSubProblem`

## Constructor

```python
OasSplitStructDiscipline(mesh_dict=None, surface_options=None)
```

Parameters, defaults, options, and methods follow the same pattern as `OasAerostructDiscipline`.

## Mapped Inputs

| Philote Name | OpenMDAO Path | Shape | Units | Source |
|--------------|---------------|-------|-------|--------|
| `loads` | `loads` | (ny, 6) | -- | Aero discipline (coupling) |
| `local_stiff_transformed` | `local_stiff_transformed` | (ny-1, 12, 12) | -- | Geometry discipline |
| `nodes` | `nodes` | (ny, 3) | m | Geometry discipline |
| `radius` | `radius` | (ny-1,) | m | Geometry discipline |
| `thickness` | `thickness` | (1, ny-1) | m | Geometry discipline |

## Mapped Outputs

| Philote Name | OpenMDAO Path | Shape | Units | Destination |
|--------------|---------------|-------|-------|-------------|
| `disp` | `disp` | (ny, 6) | -- | Aero discipline (coupling) |
| `failure` | `failure` | (1,) | -- | Performance output |

---

## Shape Notation

All shape-dependent variables use `nx` and `ny` which depend on the mesh configuration:

- `nx` = `mesh_dict["num_x"]`
- `ny` = `mesh_dict["num_y"]` if `symmetry` is False, otherwise `(num_y + 1) // 2`

For the default mesh (`num_y=5, num_x=2, symmetry=True`): `nx=2, ny=3`.
For the large mesh (`num_y=21, num_x=7, symmetry=True`): `nx=7, ny=11`.
