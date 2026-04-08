---
sidebar_position: 2
title: XfoilDiscipline
---

# XfoilDiscipline

```python
from philote_examples.xfoil import XfoilDiscipline
```

Philote discipline that wraps XFOIL for airfoil analysis. Computes aerodynamic coefficients (Cl, Cd, Cm) for a given airfoil geometry at specified flight conditions.

**Inherits from:** `philote_mdo.general.ExplicitDiscipline`

## Constructor

```python
XfoilDiscipline(n_points: int)
```

### Parameters

| Name | Type | Description |
|------|------|-------------|
| `n_points` | `int` | Number of points defining the airfoil geometry |

### Properties set by constructor

| Property | Default | Description |
|----------|---------|-------------|
| `xfoil_path` | `None` | Set from `XFOIL_PATH` env var during `setup()` |
| `viscous` | `True` | Enable viscous analysis (can be overridden by client) |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `XFOIL_PATH` | Yes | Path to the XFOIL executable |

## Methods

### `initialize()`

Declares available options:

| Option | Type | Description |
|--------|------|-------------|
| `viscous` | `bool` | Enable/disable viscous boundary-layer analysis |

### `set_options(options)`

Called by the framework when the client provides option values. Sets `self.viscous` from the `viscous` option.

### `setup()`

Reads `XFOIL_PATH` from the environment and defines inputs/outputs.

**Raises:** `ValueError` if `XFOIL_PATH` is not set or does not point to an existing file.

**Inputs (viscous mode):**

| Name | Shape | Units | Description |
|------|-------|-------|-------------|
| `alpha` | (1,) | deg | Angle of attack |
| `reynolds` | (1,) | -- | Reynolds number |
| `mach` | (1,) | -- | Mach number |
| `airfoil_x` | (n_points,) | -- | Airfoil x-coordinates |
| `airfoil_y` | (n_points,) | -- | Airfoil y-coordinates |

**Inputs (inviscid mode):**

| Name | Shape | Units | Description |
|------|-------|-------|-------------|
| `alpha` | (1,) | deg | Angle of attack |
| `airfoil_x` | (n_points,) | -- | Airfoil x-coordinates |
| `airfoil_y` | (n_points,) | -- | Airfoil y-coordinates |

**Outputs (both modes):**

| Name | Shape | Units | Description |
|------|-------|-------|-------------|
| `cl` | (1,) | -- | Lift coefficient |
| `cd` | (1,) | -- | Drag coefficient |
| `cm` | (1,) | -- | Moment coefficient |

### `compute(inputs, outputs)`

Runs XFOIL and computes aerodynamic coefficients.

The method:

1. Extracts inputs from the dictionary.
2. Creates a temporary directory for XFOIL files.
3. Writes the airfoil geometry file.
4. Generates the XFOIL command script.
5. Executes XFOIL via subprocess with a timeout.
6. Parses the output polar file.
7. Sets the output dictionary values.

## Wrapper Module

The low-level XFOIL interaction is in `philote_examples.xfoil.wrapper`:

### `write_airfoil_file(x, y, path)`

Writes airfoil coordinates to XFOIL's `.dat` format.

### `write_command_file(path, airfoil_file, output_file, **kwargs)`

Generates the XFOIL batch command script. Keyword arguments include `alpha`, `viscous`, `reynolds`, and `mach`.

### `run_xfoil(xfoil_path, command_file)`

Executes XFOIL as a subprocess with `stdin` redirected from the command file. Includes a timeout to prevent hanging.

### `parse_output_file(path)`

Reads the XFOIL polar output file and returns a dictionary with keys `"cl"`, `"cd"`, and `"cm"`.

## Example

```python
from philote_examples.xfoil import XfoilDiscipline
from philote_mdo.general import run_server

# Create discipline for 100-point airfoil geometries
discipline = XfoilDiscipline(n_points=100)

# Serve over gRPC
run_server(discipline, port=50052)
```
