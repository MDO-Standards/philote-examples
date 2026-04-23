---
sidebar_position: 2
title: XFOIL Aerodynamic Analysis
---

# XFOIL Aerodynamic Analysis

The `XfoilDiscipline` wraps the [XFOIL](https://web.mit.edu/drela/Public/web/xfoil/) panel-method airfoil solver as a Philote discipline. It computes aerodynamic coefficients (Cl, Cd, Cm) for a given airfoil geometry at specified flight conditions.

## Overview

XFOIL is a well-established interactive program for the design and analysis of subsonic isolated airfoils. The `XfoilDiscipline` automates XFOIL's batch mode:

1. Writes the airfoil geometry to a file in XFOIL format.
2. Generates a command script for the analysis (LOAD, OPER, etc.).
3. Executes XFOIL as a subprocess with a timeout.
4. Parses the output polar file for the aerodynamic coefficients.

Each `compute()` call runs in an isolated temporary directory, ensuring clean execution when called many times during an optimization.

## Environment Setup

The `XfoilDiscipline` requires the `XFOIL_PATH` environment variable to be set:

```bash
# Linux / macOS
export XFOIL_PATH=/path/to/xfoil

# Windows
set XFOIL_PATH=C:\path\to\xfoil.exe
```

The discipline validates this path during `setup()` and raises a `ValueError` if it is unset or points to a nonexistent file.

## Viscous vs. Inviscid Modes

The discipline supports two analysis modes controlled by the `viscous` option:

### Viscous mode (default)

Enables the boundary-layer solver. Requires `reynolds` and `mach` inputs in addition to `alpha` and the airfoil geometry. Returns physically meaningful drag coefficients.

### Inviscid mode

Runs a potential-flow panel solution without a boundary layer. Omits the `reynolds` and `mach` inputs entirely. Cd will be exactly 0.0 since there is no viscous drag model.

The mode is set via the `viscous` option on the client side:

```python
# Viscous (default)
RemoteExplicitComponent(channel=channel)

# Inviscid
RemoteExplicitComponent(channel=channel, viscous=False)
```

## Inputs and Outputs

### Inputs

| Name | Shape | Units | Viscous | Inviscid | Description |
|------|-------|-------|---------|----------|-------------|
| `alpha` | (1,) | deg | Yes | Yes | Angle of attack |
| `reynolds` | (1,) | -- | Yes | No | Reynolds number |
| `mach` | (1,) | -- | Yes | No | Mach number |
| `airfoil_x` | (n_points,) | -- | Yes | Yes | Airfoil x-coordinates |
| `airfoil_y` | (n_points,) | -- | Yes | Yes | Airfoil y-coordinates |

### Outputs

| Name | Shape | Units | Description |
|------|-------|-------|-------------|
| `cl` | (1,) | -- | Lift coefficient |
| `cd` | (1,) | -- | Drag coefficient |
| `cm` | (1,) | -- | Moment coefficient |

## The Wrapper Module

The low-level XFOIL interaction is delegated to a separate `wrapper.py` module with four standalone functions:

| Function | Purpose |
|----------|---------|
| `write_airfoil_file` | Write x/y coordinates to XFOIL's airfoil format |
| `write_command_file` | Generate the XFOIL batch script (LOAD, OPER, etc.) |
| `run_xfoil` | Execute XFOIL via `subprocess.run` with a timeout |
| `parse_output_file` | Read the polar output file and return a dict of floats |

This separation keeps the discipline class focused on the Philote interface and makes the file-handling logic independently testable.

## Example Usage

```python
from philote_examples.xfoil import XfoilDiscipline
from philote_mdo.general import run_server

# Create the discipline for 100-point airfoil geometries
discipline = XfoilDiscipline(n_points=100)

# Start the gRPC server on port 50052
run_server(discipline, port=50052)
```
