"""Verify OasAerostructDiscipline partials against finite differences."""

import numpy as np
import pytest
from openaerostruct.utils.constants import grav_constant

from philote_examples import OasAerostructDiscipline

OUTPUTS = ("CD", "CL")

FLIGHT_CONDITIONS = {
    "v": np.array([248.136]),
    "Mach_number": np.array([0.84]),
    "re": np.array([1e6]),
    "rho": np.array([0.38]),
    "CT": np.array([grav_constant * 17.0e-6]),
    "R": np.array([11.165e6]),
    "W0": np.array([0.4 * 3e5]),
    "speed_of_sound": np.array([295.4]),
    "load_factor": np.array([1.0]),
    "empty_cg": np.zeros(3),
}


@pytest.fixture(scope="module")
def discipline():
    disc = OasAerostructDiscipline()
    disc.setup()
    disc.setup_partials()
    return disc


def _inputs(alpha):
    return {**FLIGHT_CONDITIONS, "alpha": np.array([alpha])}


def _eval(discipline, alpha):
    """Run compute and return the outputs of interest."""
    outputs = {}
    discipline.compute(_inputs(alpha), outputs)
    return {name: np.asarray(outputs[name]).copy() for name in OUTPUTS}


def test_declares_lift_and_drag_partials(discipline):
    declared = {(p.name, p.subname) for p in discipline._partials_meta}
    assert declared == {("CD", "alpha"), ("CL", "alpha")}


def test_partials_match_finite_differences(discipline):
    alpha, h = 5.0, 1e-4

    partials = {}
    discipline.compute_partials(_inputs(alpha), partials)

    plus = _eval(discipline, alpha + h)
    minus = _eval(discipline, alpha - h)

    for name in OUTPUTS:
        fd = (plus[name] - minus[name]) / (2 * h)
        np.testing.assert_allclose(np.ravel(partials[name, "alpha"]), fd, rtol=1e-4)
