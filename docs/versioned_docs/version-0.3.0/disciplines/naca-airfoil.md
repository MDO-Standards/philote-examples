---
sidebar_position: 1
title: NACA Airfoil Geometry
---

# NACA Airfoil Geometry

The `NacaDiscipline` generates NACA 4-digit airfoil coordinates analytically. It accepts three scalar inputs (the digits of the NACA designation) and outputs the x/y coordinates of the airfoil contour in Selig format. It provides analytical gradients, making it suitable for gradient-based optimization.

## NACA 4-Digit Parameterization

A NACA 4-digit airfoil (e.g., NACA 2412) is defined by three parameters:

| Parameter | NACA digit(s) | Example (NACA 2412) |
|-----------|---------------|---------------------|
| `camber` | 1st digit | 2 (2% max camber) |
| `camber_loc` | 2nd digit | 4 (at 40% chord) |
| `thickness` | 3rd-4th digits | 12 (12% thick) |

## Thickness Distribution

The NACA 4-digit thickness distribution is:

$$
y_t = 5t \left( 0.2969\sqrt{x} - 0.1260\,x - 0.3516\,x^2 + 0.2843\,x^3 - 0.1015\,x^4 \right)
$$

where $t$ is the maximum thickness as a fraction of chord and $x$ is the chordwise position normalized to $[0, 1]$.

## Mean Camber Line

The mean camber line is a piecewise function split at the position of maximum camber $p$:

$$
y_c = \begin{cases}
\displaystyle \frac{m}{p^2}\left(2px - x^2\right) & \text{for } x < p \\[8pt]
\displaystyle \frac{m}{(1-p)^2}\left(1 - 2p + 2px - x^2\right) & \text{for } x \ge p
\end{cases}
$$

where $m$ is the maximum camber as a fraction of chord.

The slope of the camber line is:

$$
\frac{dy_c}{dx} = \begin{cases}
\displaystyle \frac{2m}{p^2}(p - x) & \text{for } x < p \\[8pt]
\displaystyle \frac{2m}{(1-p)^2}(p - x) & \text{for } x \ge p
\end{cases}
$$

## Surface Coordinates

The upper and lower surface coordinates are computed by applying the thickness distribution perpendicular to the camber line:

$$
\begin{aligned}
x_U &= x - y_t \sin\theta, \quad y_U = y_c + y_t \cos\theta \\
x_L &= x + y_t \sin\theta, \quad y_L = y_c - y_t \cos\theta
\end{aligned}
$$

where $\theta = \arctan(dy_c/dx)$.

## Selig Format Output

The coordinates are output in **Selig format**: starting at the trailing edge, traversing the upper surface to the leading edge, then continuing along the lower surface back to the trailing edge. This format is directly compatible with XFOIL and other panel-method solvers.

## Inputs and Outputs

### Inputs

| Name | Shape | Units | Description |
|------|-------|-------|-------------|
| `camber` | (1,) | -- | Maximum camber (1st NACA digit, e.g., 2 for 2%) |
| `camber_loc` | (1,) | -- | Location of maximum camber (2nd digit, e.g., 4 for 40%) |
| `thickness` | (1,) | -- | Maximum thickness (3rd-4th digits, e.g., 12 for 12%) |

### Outputs

| Name | Shape | Units | Description |
|------|-------|-------|-------------|
| `airfoil_x` | (n_points,) | -- | Airfoil x-coordinates in Selig format |
| `airfoil_y` | (n_points,) | -- | Airfoil y-coordinates in Selig format |

## Analytical Gradients

The `NacaDiscipline` provides analytical partial derivatives of all outputs with respect to all inputs. Derivatives are computed via the chain rule through the thickness distribution and mean camber line formulas. This includes:

- $\partial(\text{airfoil\_x}, \text{airfoil\_y}) / \partial\text{camber}$
- $\partial(\text{airfoil\_x}, \text{airfoil\_y}) / \partial\text{camber\_loc}$
- $\partial(\text{airfoil\_x}, \text{airfoil\_y}) / \partial\text{thickness}$

The analytical gradients have been validated against central finite differences for several airfoil shapes (NACA 2412, 0012, 4421, 1508).

## Example Usage

```python
from philote_examples import NacaDiscipline
from philote_mdo.general import run_server

# Create the discipline with 100 contour points
discipline = NacaDiscipline(n_points=100)

# Start the gRPC server on port 50051
run_server(discipline, port=50051)
```
