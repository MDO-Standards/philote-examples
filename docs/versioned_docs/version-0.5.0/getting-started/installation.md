---
sidebar_position: 1
title: Installation
---

# Installation

## Requirements

- Python 3.8 or later
- [philote-mdo](https://pypi.org/project/philote-mdo/) -- the Philote MDO framework
- [OpenMDAO](https://openmdao.org/) -- multidisciplinary design analysis and optimization
- [OpenAeroStruct](https://mdolab-openaerostruct.readthedocs-hosted.com/) -- aerostructural analysis (for the OAS VLM example)
- [NumPy](https://numpy.org/)

## Install from source

Clone the repository and install in editable mode:

```bash
git clone https://github.com/MDO-Standards/philote-examples.git
cd philote-examples
pip install -e .
```

### With development dependencies

To also install testing and linting tools (`pytest`, `ruff`, `pre-commit`):

```bash
pip install -e ".[dev]"
```

## Verify the installation

```python
from philote_examples import NacaDiscipline, OasDiscipline

# Create a NACA geometry discipline with 100 contour points
naca = NacaDiscipline(n_points=100)
print("NacaDiscipline created successfully")
```

## XFOIL setup (optional)

The XFOIL example requires a separate installation of the [XFOIL](https://web.mit.edu/drela/Public/web/xfoil/) executable.

1. Download XFOIL for your platform from the [XFOIL website](https://web.mit.edu/drela/Public/web/xfoil/).

2. Set the `XFOIL_PATH` environment variable to point to the executable:

```bash
# Linux / macOS
export XFOIL_PATH=/path/to/xfoil

# Windows
set XFOIL_PATH=C:\path\to\xfoil.exe
```

The `XfoilDiscipline` reads this variable at setup time and will raise a `ValueError` if it is unset or points to a nonexistent file.

:::note
The OpenAeroStruct VLM example does **not** require XFOIL. You can run it immediately after installing the package.
:::
