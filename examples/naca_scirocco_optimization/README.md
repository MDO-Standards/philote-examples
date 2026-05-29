# NACA 4-Digit Airfoil Optimization with Scirocco

Gradient-based airfoil shape optimization using OpenMDAO and the Scirocco viscous panel-method solver. The geometry is parameterized by NACA 4-digit variables (camber, camber location, thickness) plus the angle of attack. Scirocco provides aerodynamic coefficients and analytical adjoint sensitivities via a Philote gRPC server.

## Architecture

```
[NACA4Geometry]  --x-->  [Scirocco (Philote)]  --cl,cd,cm-->  [SLSQP]
  analytical       |      analytical adjoint
  gradients        |      sensitivities
                   +-->  [AirfoilArea]  --area-->
```

- **NACA4Geometry** — OpenMDAO component that generates airfoil coordinates from NACA 4-digit parameters with analytical gradients.
- **Scirocco** — Viscous-inviscid panel-method solver running as a Philote gRPC server, providing aerodynamic coefficients and adjoint sensitivities.
- **AirfoilArea** — Computes cross-sectional area via the shoelace formula with analytical gradients.

## Prerequisites

1. Install the package from the repository root:

```bash
pip install -e .
```

2. Build and install the [Scirocco](https://github.com/chrislupp/Scirocco) solver with Philote server support.

## Usage

Start the Scirocco Philote server:

```bash
scirocco_server localhost:50051
```

Then run the script:

```bash
cd examples/naca_scirocco_optimization
python run_optimization.py
```

The script runs three stages:

1. **Single-point analysis** — evaluates a NACA 2412 airfoil at alpha=5 deg, Re=1e6.
2. **Derivative check** — verifies total derivatives (analytical vs. finite difference).
3. **Optimization** — minimizes Cd subject to Cl=0.5 and area >= 80% of the initial NACA 0012 airfoil.

## Outputs

- `optimization_history.h5` — HDF5 file containing the iteration history (viewable in Scirocco Viewer).
- `naca_optimization_result.png` — Plot comparing the initial and optimized airfoil shapes.
