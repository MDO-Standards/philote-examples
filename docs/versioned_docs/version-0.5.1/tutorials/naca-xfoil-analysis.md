---
sidebar_position: 1
title: NACA + XFOIL Coupled Analysis
---

# NACA + XFOIL Coupled Analysis

This tutorial demonstrates how to couple two aerodynamic disciplines -- a NACA 4-digit airfoil geometry generator and the XFOIL panel-method solver -- using Philote MDO and OpenMDAO. Each discipline runs as an independent gRPC service, and OpenMDAO handles the data flow between them.

By the end of this tutorial you will be able to:

- Launch Philote discipline servers for geometry generation and aerodynamic analysis.
- Build an OpenMDAO model that chains the two disciplines together.
- Run viscous and inviscid airfoil analyses and retrieve Cl, Cd, and Cm.
- Run the disciplines as standalone servers for use in larger MDO workflows.

## Prerequisites

### 1. Install the package

From the repository root:

```bash
pip install -e .
```

Or, if you also want to run the test suite:

```bash
pip install -e ".[dev]"
```

This installs `philote-mdo`, `openmdao`, and `numpy` as dependencies.

### 2. Install XFOIL

Download the XFOIL executable for your platform from the [XFOIL website](https://web.mit.edu/drela/Public/web/xfoil/).

Set the `XFOIL_PATH` environment variable to point to the executable:

```bash
# Linux / macOS
export XFOIL_PATH=/path/to/xfoil

# Windows
set XFOIL_PATH=C:\path\to\xfoil.exe
```

The `XfoilDiscipline` reads this variable at setup time and will raise a `ValueError` if it is unset or points to a nonexistent file.

## Architecture Overview

The example is built on two Philote disciplines that communicate over gRPC:

```
┌──────────────────┐     airfoil_x     ┌──────────────────┐
│  NacaDiscipline  │────────────────────│  XfoilDiscipline │
│  (geometry)      │     airfoil_y     │  (aerodynamics)  │
│                  │────────────────────│                  │
│  Port 50051      │                    │  Port 50052      │
└──────────────────┘                    └──────────────────┘
     Inputs:                                 Inputs:
       camber                                  alpha
       camber_loc                              reynolds*
       thickness                               mach*
                                               airfoil_x
     Outputs:                                  airfoil_y
       airfoil_x
       airfoil_y                             Outputs:
                                               cl, cd, cm

                                         * viscous mode only
```

**NacaDiscipline** generates NACA 4-digit airfoil coordinates analytically. It accepts three scalar inputs (the digits of the NACA designation) and outputs the x/y coordinates of the airfoil contour in Selig format. It provides analytical gradients, so it is suitable for gradient-based optimization.

**XfoilDiscipline** wraps the XFOIL executable. It takes the airfoil coordinates plus flight conditions and returns aerodynamic coefficients. It supports both viscous (boundary-layer) and inviscid (potential flow) modes.

OpenMDAO connects the two disciplines by promoting `airfoil_x` and `airfoil_y` so that the NACA outputs feed directly into the XFOIL inputs.

## Running the Coupled Analysis

### Viscous analysis

The quickest way to run the example is with the all-in-one script. It starts both servers in background threads, builds the OpenMDAO problem, runs the analysis, and prints the results:

```bash
cd examples/naca_xfoil
python run_analysis.py
```

This evaluates a **NACA 2412** airfoil at 5 degrees angle of attack, Re = 1,000,000, and M = 0.0. Expected output:

```
NACA 2412 at alpha=5.0 deg, Re=1e+06, M=0.0
  Cl = 0.9471
  Cd = 0.008292
  Cm = -0.0569
```

### Inviscid analysis

For an inviscid (potential flow) analysis, which omits Reynolds and Mach inputs:

```bash
python run_inviscid_analysis.py
```

In inviscid mode, XFOIL computes the panel solution without a boundary layer, so Cd will be exactly 0.0:

```
NACA 2412 at alpha=5.0 deg (inviscid)
  Cl = 1.0218
  Cd = 0.000000
  Cm = -0.0588
```

## Running the Servers Independently

For integration into a larger MDO workflow -- or when you want to run the disciplines on separate machines -- you can start each server as a standalone process.

**Terminal 1** -- Start the NACA geometry server:

```bash
python naca_server.py
```

Output:

```
NACA server started. Listening on port 50051.
Airfoil contour configured for 100 points.
```

**Terminal 2** -- Start the XFOIL analysis server:

```bash
export XFOIL_PATH=/path/to/xfoil
python xfoil_server.py
```

Output:

```
XFOIL server started. Listening on port 50052.
Airfoil geometry configured for 100 points.
```

**Terminal 3** -- Run the coupled analysis with `start_servers=False`:

```python
from run_analysis import run

cl, cd, cm = run(start_servers=False)
```

When running in this mode, the analysis script connects to the already-running servers on ports 50051 and 50052.

## Understanding the Code

### How the coupled analysis works

The core of `run_analysis.py` is an OpenMDAO `Problem` that chains the two remote disciplines:

```python
prob = om.Problem()

# Geometry discipline -- promotes outputs so XFOIL can consume them
prob.model.add_subsystem(
    "naca",
    RemoteExplicitComponent(channel=naca_channel),
    promotes_outputs=["airfoil_x", "airfoil_y"],
)

# Aerodynamic discipline -- promotes matching inputs
prob.model.add_subsystem(
    "xfoil",
    RemoteExplicitComponent(channel=xfoil_channel),
    promotes_inputs=["airfoil_x", "airfoil_y"],
)

prob.setup()
```

`RemoteExplicitComponent` is a Philote-provided OpenMDAO component that delegates `compute()` calls to a remote gRPC server. From OpenMDAO's perspective, these components behave identically to local ones.

Variable promotion creates the data connection: the NACA discipline's `airfoil_x` and `airfoil_y` outputs are automatically routed to the XFOIL discipline's matching inputs. OpenMDAO resolves the execution order so that the geometry runs before the aerodynamic solver.

### Switching between viscous and inviscid modes

The only code difference is passing `viscous=False` as an option to the XFOIL `RemoteExplicitComponent`:

```python
# Viscous (default)
RemoteExplicitComponent(channel=xfoil_channel)

# Inviscid
RemoteExplicitComponent(channel=xfoil_channel, viscous=False)
```

In inviscid mode, the XFOIL discipline does not declare `reynolds` or `mach` inputs.

### Modifying the analysis parameters

To analyze a different airfoil or flight condition, change the values passed to `run()`:

```python
from run_analysis import run

# NACA 4421 at 8 degrees, Re=500000
cl, cd, cm = run(
    camber=4,
    camber_loc=4,
    thickness=21,
    alpha=8.0,
    reynolds=5e5,
    mach=0.1,
)
```

The NACA digit convention is:

| Parameter | NACA digit(s) | Example (NACA 2412) |
|-----------|---------------|---------------------|
| `camber` | 1st digit | 2 (2% max camber) |
| `camber_loc` | 2nd digit | 4 (at 40% chord) |
| `thickness` | 3rd-4th digits | 12 (12% thick) |

## Anatomy of a Philote Discipline

If you want to wrap your own external solver as a Philote discipline, the `XfoilDiscipline` is a good template to follow. This section walks through its structure so you can apply the same pattern to any file-based analysis tool (e.g., a mesh generator, a structural FEA solver, or a CFD code).

### Explicit vs. implicit disciplines

Philote supports two discipline types: **explicit** and **implicit**.

An **explicit discipline** (`pmdo.ExplicitDiscipline`) computes its outputs directly from its inputs -- call `compute()` once and you have the answer. This is the right choice whenever your solver manages its own internal convergence (iterative or not) and simply returns results for a given set of inputs. Most external-tool wrappers fall into this category: you hand XFOIL an airfoil and flight condition, it converges internally, and you read back Cl, Cd, Cm.

An **implicit discipline** (`pmdo.ImplicitDiscipline`) is used when the discipline defines a residual equation R(inputs, outputs) = 0 and the framework's nonlinear solver drives the outputs to satisfy that residual. This is appropriate when you need the outer framework to participate in the convergence loop -- for example, when coupling tightly with other disciplines that feed back into the residual.

For most engineering tools -- panel codes, FEA solvers, CFD codes, trajectory simulators -- **explicit is the right choice**. Use implicit only when you have a specific need for the framework to manage the solve.

### The overall pattern

An explicit Philote discipline for an external solver follows a predictable recipe:

1. Subclass `pmdo.ExplicitDiscipline`.
2. Declare any configurable options in `initialize()`.
3. Define inputs and outputs in `setup()`.
4. Implement the solver call in `compute()`: write input files, run the executable, and parse the output files.

Optionally, keep the low-level file I/O and subprocess calls in a separate wrapper module so the discipline class stays focused on the Philote interface.

### Step 1: Subclass and constructor

```python
import philote_mdo.general as pmdo

class XfoilDiscipline(pmdo.ExplicitDiscipline):

    def __init__(self, n_points: int):
        super().__init__()
        self.n_points = n_points
        self.xfoil_path = None
        self.viscous = True
```

The constructor stores any configuration that is known at instantiation time. Here, `n_points` determines the size of the airfoil coordinate arrays. `viscous` is a default that can be overridden by the client (see next step).

### Step 2: Declare options

```python
def initialize(self):
    self.add_option("viscous", "bool")

def set_options(self, options):
    if "viscous" in options:
        self.viscous = bool(options["viscous"])
```

Options let clients configure the discipline at connection time without changing server-side code. `initialize()` declares which options exist and their types. `set_options()` is called by the framework when the client provides values -- in this case, the `viscous=False` keyword passed to `RemoteExplicitComponent` on the client side.

### Step 3: Define the interface in `setup()`

```python
def setup(self):
    self.xfoil_path = os.environ.get("XFOIL_PATH")
    if self.xfoil_path is None:
        raise ValueError("XFOIL_PATH not set")

    self.add_input("alpha", shape=(1,), units="deg")
    if self.viscous:
        self.add_input("reynolds", shape=(1,), units="")
        self.add_input("mach", shape=(1,), units="")

    self.add_input("airfoil_x", shape=(self.n_points,), units="")
    self.add_input("airfoil_y", shape=(self.n_points,), units="")

    self.add_output("cl", shape=(1,), units="")
    self.add_output("cd", shape=(1,), units="")
    self.add_output("cm", shape=(1,), units="")
```

`setup()` is where the discipline's data interface is defined. Each call to `add_input()` or `add_output()` registers a named variable with a shape and optional units. These declarations are communicated to the client over gRPC so that OpenMDAO (or any other framework) can build the correct data connections.

A few things to note:

- **Conditional inputs.** The `reynolds` and `mach` inputs are only declared when `self.viscous` is `True`. This means the interface itself changes based on the option, keeping the inviscid problem cleaner.
- **Environment validation.** `setup()` is a natural place to validate external dependencies (like the XFOIL binary path) since it runs once before any analysis calls.
- **Shape matters.** Scalar quantities use `shape=(1,)`. Array quantities like the airfoil coordinates use `shape=(self.n_points,)`. The shapes must match between connected disciplines.

### Step 4: Implement `compute()`

This is where the actual work happens. The pattern for wrapping a file-based solver is always the same: extract inputs, write files, run the executable, parse outputs.

```python
def compute(self, inputs, outputs):
    alpha = float(inputs["alpha"][0])
    airfoil_x = inputs["airfoil_x"]
    airfoil_y = inputs["airfoil_y"]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 1. Write input files
        write_airfoil_file(airfoil_x, airfoil_y, tmpdir / "airfoil.dat")
        write_command_file(tmpdir / "commands.txt", ...)

        # 2. Run the solver
        run_xfoil(self.xfoil_path, tmpdir / "commands.txt")

        # 3. Parse output files
        results = parse_output_file(tmpdir / "output.dat")

    outputs["cl"] = np.array([results["cl"]])
    outputs["cd"] = np.array([results["cd"]])
    outputs["cm"] = np.array([results["cm"]])
```

Key patterns:

- **Temporary directory.** A `tempfile.TemporaryDirectory` ensures that each analysis call gets a clean workspace and that intermediate files are automatically cleaned up. This is critical when the discipline is called many times during an optimization.
- **Delegate file I/O.** The helper functions (`write_airfoil_file`, `write_command_file`, `run_xfoil`, `parse_output_file`) live in a separate `wrapper.py` module. This keeps the discipline class readable and makes the file-handling logic independently testable.
- **Output format.** All outputs must be NumPy arrays matching the declared shapes. A scalar output declared with `shape=(1,)` must be set as `np.array([value])`.

### The wrapper module

The wrapper module (`xfoil/wrapper.py`) handles four concerns, each as a standalone function:

| Function | Purpose |
|----------|---------|
| `write_airfoil_file` | Write x/y coordinates to XFOIL's airfoil format |
| `write_command_file` | Generate the XFOIL batch script (LOAD, OPER, etc.) |
| `run_xfoil` | Execute XFOIL via `subprocess.run` with a timeout |
| `parse_output_file` | Read the polar output file and return a dict of floats |

This separation means you can test and iterate on the file I/O independently of Philote. If you are wrapping a different solver, you would write analogous functions for your tool's input/output formats.

### Applying this pattern to your own solver

To wrap a different external tool, follow the same four steps:

1. **Subclass `pmdo.ExplicitDiscipline`** and store solver-specific configuration in the constructor.
2. **Declare options** for anything the client should be able to toggle (mesh density, turbulence model, convergence criteria, etc.).
3. **Define inputs and outputs** in `setup()` that map to your solver's physical quantities. Validate that required executables or licenses are available.
4. **Implement `compute()`** using the write-run-parse pattern with a temporary directory.

The resulting discipline can then be served over gRPC and composed with other Philote disciplines in OpenMDAO, exactly as shown in this example.

## Running the Tests

From the repository root:

```bash
# Run all NACA/XFOIL tests
pytest tests/test_naca_xfoil.py

# Run NACA gradient validation (no XFOIL required)
pytest tests/test_naca_gradients.py
```

The integration tests in `test_naca_xfoil.py` exercise both viscous and inviscid coupled analyses and assert that the aerodynamic coefficients fall within expected physical ranges. They require `XFOIL_PATH` to be set.

The gradient tests in `test_naca_gradients.py` validate the analytical Jacobians of the `NacaDiscipline` against central finite differences for several airfoil shapes (NACA 2412, 0012, 4421, 1508).

## Troubleshooting

**`ValueError: Environment variable XFOIL_PATH not set`**
Set the `XFOIL_PATH` environment variable to the full path of your XFOIL executable before running any script that uses `XfoilDiscipline`.

**`ValueError: XFOIL_PATH set to ... which is not a file`**
The path exists but does not point to a valid file. Verify the path and ensure the XFOIL binary is present.

**XFOIL times out or produces no output**
The default timeout is 30 seconds. If XFOIL hangs (e.g., the viscous solver does not converge), the subprocess will be killed after the timeout. Try reducing the angle of attack or checking that the airfoil geometry is well-formed.

**Port already in use**
The default ports are 50051 (NACA) and 50052 (XFOIL). If another process is using these ports, stop it or modify the port constants in the scripts.
