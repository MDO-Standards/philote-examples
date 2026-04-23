---
sidebar_position: 1
title: NacaDiscipline
---

# NacaDiscipline

```python
from philote_examples import NacaDiscipline
```

Philote discipline that generates NACA 4-digit airfoil coordinates.

Produces airfoil coordinates in XFOIL Selig format (TE -> upper -> LE -> lower -> TE), compatible with the `XfoilDiscipline` inputs.

**Inherits from:** `philote_mdo.general.ExplicitDiscipline`

## Constructor

```python
NacaDiscipline(n_points: int)
```

### Parameters

| Name | Type | Description |
|------|------|-------------|
| `n_points` | `int` | Total number of coordinate points in the output contour |

### Properties set by constructor

| Property | Value | Description |
|----------|-------|-------------|
| `_is_continuous` | `True` | Discipline outputs are continuous |
| `_is_differentiable` | `True` | Discipline outputs are differentiable |
| `_provides_gradients` | `True` | Discipline provides analytical gradients |

## Methods

### `setup()`

Defines inputs and outputs for the NACA discipline.

**Inputs:**

| Name | Shape | Units | Description |
|------|-------|-------|-------------|
| `camber` | (1,) | -- | Maximum camber (1st NACA digit) |
| `camber_loc` | (1,) | -- | Location of maximum camber (2nd NACA digit) |
| `thickness` | (1,) | -- | Maximum thickness (3rd-4th NACA digits) |

**Outputs:**

| Name | Shape | Units | Description |
|------|-------|-------|-------------|
| `airfoil_x` | (n_points,) | -- | Airfoil x-coordinates in Selig format |
| `airfoil_y` | (n_points,) | -- | Airfoil y-coordinates in Selig format |

### `setup_partials()`

Declares all partial derivatives. Declares partials of both outputs (`airfoil_x`, `airfoil_y`) with respect to all three inputs (`camber`, `camber_loc`, `thickness`).

### `compute(inputs, outputs)`

Generates NACA 4-digit airfoil coordinates.

The input values are internally rescaled:

- `camber` is divided by 100 (e.g., 2 becomes 0.02)
- `camber_loc` is divided by 10 (e.g., 4 becomes 0.4)
- `thickness` is divided by 100 (e.g., 12 becomes 0.12)

Coordinates are computed using cosine-spaced x-stations and output in Selig format (upper surface reversed, concatenated with lower surface).

### `compute_partials(inputs, partials)`

Computes analytical partial derivatives via chain rule through the NACA 4-digit thickness distribution and mean camber line formulas.

The Jacobian includes scaling factors for the input transformations:

- $\partial / \partial\text{camber}$: scaled by 0.01
- $\partial / \partial\text{camber\_loc}$: scaled by 0.1
- $\partial / \partial\text{thickness}$: scaled by 0.01

## Module-Level Functions

The following functions in `philote_examples.naca` support the discipline:

### `_thickness_poly(x)`

NACA 4-digit thickness polynomial (without the $5t$ scaling factor).

$$
\text{poly}(x) = 0.2969\sqrt{x} - 0.1260\,x - 0.3516\,x^2 + 0.2843\,x^3 - 0.1015\,x^4
$$

### `_thickness(x, t)`

Full NACA 4-digit thickness distribution: $y_t = 5t \cdot \text{poly}(x)$.

### `_camber(x, m, p)`

Mean camber line $y_c$ and its slope $dy_c/dx$ for given max camber $m$ and position $p$.

### `_camber_partials(x, m, p)`

Partial derivatives of the camber line and slope with respect to $m$ and $p$:

- `dyc_dm`, `dyc_dp` -- partials of $y_c$
- `ddyc_dm`, `ddyc_dp` -- partials of $dy_c/dx$

### `_selig(upper, lower)`

Combines upper and lower surface arrays in Selig order: upper reversed, concatenated with lower (excluding the shared leading-edge point).

## Example

```python
from philote_examples import NacaDiscipline
from philote_mdo.general import run_server

# Create discipline with 100 contour points
discipline = NacaDiscipline(n_points=100)

# Serve over gRPC
run_server(discipline, port=50051)
```
