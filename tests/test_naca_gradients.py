"""Verify NacaDiscipline analytical gradients against finite differences."""

import numpy as np
import pytest

from philote_examples.naca import NacaDiscipline

INPUTS = ("camber", "camber_loc", "thickness")
OUTPUTS = ("airfoil_x", "airfoil_y")


def _eval(discipline, camber, camber_loc, thickness):
    """Run compute and return (airfoil_x, airfoil_y)."""
    inputs = {
        "camber": np.array([camber]),
        "camber_loc": np.array([camber_loc]),
        "thickness": np.array([thickness]),
    }
    outputs = {
        "airfoil_x": np.zeros(discipline.n_points),
        "airfoil_y": np.zeros(discipline.n_points),
    }
    discipline.compute(inputs, outputs)
    return outputs["airfoil_x"].copy(), outputs["airfoil_y"].copy()


def _fd_partials(discipline, camber, camber_loc, thickness, h=1e-6):
    """Compute all partials via central finite differences."""
    vals = [camber, camber_loc, thickness]
    fd = {}

    for i, name in enumerate(INPUTS):
        dp = vals.copy()
        dm = vals.copy()
        dp[i] += h
        dm[i] -= h

        xp, yp = _eval(discipline, *dp)
        xm, ym = _eval(discipline, *dm)

        fd["airfoil_x", name] = (xp - xm) / (2.0 * h)
        fd["airfoil_y", name] = (yp - ym) / (2.0 * h)

    return fd


def _analytical_partials(discipline, camber, camber_loc, thickness):
    """Compute analytical partials."""
    inputs = {
        "camber": np.array([camber]),
        "camber_loc": np.array([camber_loc]),
        "thickness": np.array([thickness]),
    }
    from philote_mdo.utils import PairDict

    partials = PairDict()
    n = discipline.n_points
    for out in OUTPUTS:
        for inp in INPUTS:
            partials[out, inp] = np.zeros(n)

    discipline.compute_partials(inputs, partials)
    return partials


@pytest.mark.parametrize(
    "camber,camber_loc,thickness",
    [
        (2, 4, 12),  # NACA 2412 (cambered)
        (0, 0, 12),  # NACA 0012 (symmetric)
        (4, 4, 21),  # NACA 4421 (high camber)
        (1, 5, 8),   # NACA 1508 (thin, camber at mid-chord)
    ],
    ids=["NACA2412", "NACA0012", "NACA4421", "NACA1508"],
)
def test_gradients_vs_fd(camber, camber_loc, thickness):
    n_points = 50
    disc = NacaDiscipline(n_points)
    disc.setup()
    disc.setup_partials()

    analytical = _analytical_partials(disc, camber, camber_loc, thickness)
    fd = _fd_partials(disc, camber, camber_loc, thickness)

    for out in OUTPUTS:
        for inp in INPUTS:
            a = analytical[out, inp]
            f = fd[out, inp]
            np.testing.assert_allclose(
                a,
                f,
                atol=1e-7,
                rtol=1e-5,
                err_msg=f"d({out})/d({inp}) for NACA "
                f"{camber}{camber_loc}{thickness:02d}",
            )
