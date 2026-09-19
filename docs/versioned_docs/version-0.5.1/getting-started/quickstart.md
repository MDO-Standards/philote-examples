---
sidebar_position: 2
title: Quick Start
---

# Quick Start

Run your first Philote MDO analysis in under five minutes. This guide uses the OpenAeroStruct VLM example, which requires no external dependencies beyond the package itself.

## 1. Install the package

```bash
git clone https://github.com/MDO-Standards/philote-examples.git
cd philote-examples
pip install -e .
```

## 2. Run the analysis

```bash
cd examples/oas_vlm
python run_analysis.py
```

This starts a Philote gRPC server hosting the OAS VLM discipline, connects an OpenMDAO client, runs a vortex-lattice method analysis on a rectangular wing, and prints the aerodynamic coefficients:

```
OAS VLM analysis: v=248.136 m/s, alpha=5.0 deg, M=0.84, Re=1e+06/m, rho=0.38 kg/m^3
  CL = ...
  CD = ...
  CM = [...]
```

## 3. What just happened?

The script performed these steps automatically:

1. **Created an `OasDiscipline`** -- a Philote discipline wrapping the OpenAeroStruct Geometry + AeroPoint solver.
2. **Started a gRPC server** hosting the discipline on port 50051.
3. **Built an OpenMDAO `Problem`** with a `RemoteExplicitComponent` connected to the server.
4. **Set flight conditions** (velocity, angle of attack, Mach number, Reynolds number, density) and ran the model.
5. **Printed results** -- CL, CD, and the CM vector.

## Next steps

- **[NACA + XFOIL Tutorial](../tutorials/naca-xfoil-analysis.md)** -- Couple two disciplines for airfoil geometry generation and aerodynamic analysis.
- **[OAS VLM Tutorial](../tutorials/oas-vlm-analysis.md)** -- Customize the wing geometry and surface properties.
- **[Disciplines](../disciplines/naca-airfoil.md)** -- Detailed reference for each discipline's inputs, outputs, and options.
