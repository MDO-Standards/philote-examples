"""NACA 4-digit airfoil Philote discipline."""

import logging

import numpy as np
import philote_mdo.general as pmdo

logger = logging.getLogger(__name__)


class NacaDiscipline(pmdo.ExplicitDiscipline):
    """Philote discipline that generates NACA 4-digit airfoil coordinates.

    Produces airfoil coordinates in XFOIL Selig format
    (TE -> upper -> LE -> lower -> TE), compatible with the XfoilDiscipline
    inputs.

    Parameters
    ----------
    n_points : int
        Total number of coordinate points in the output contour.
    """

    def __init__(self, n_points: int):
        super().__init__()
        self.n_points = n_points
        self._is_continuous = True
        self._is_differentiable = True
        self._provides_gradients = True

    def setup(self):
        """Define inputs and outputs for the NACA discipline."""
        self.add_input("camber", shape=(1,), units="")
        self.add_input("camber_loc", shape=(1,), units="")
        self.add_input("thickness", shape=(1,), units="")

        self.add_output("airfoil_x", shape=(self.n_points,), units="")
        self.add_output("airfoil_y", shape=(self.n_points,), units="")

        logger.info("NacaDiscipline setup complete (n_points=%d)", self.n_points)

    def setup_partials(self):
        """Declare all partial derivatives."""
        for output in ("airfoil_x", "airfoil_y"):
            for inp in ("camber", "camber_loc", "thickness"):
                self.declare_partials(output, inp)

    def compute(self, inputs, outputs):
        """Generate NACA 4-digit airfoil coordinates.

        Parameters
        ----------
        inputs : dict
            Input dictionary containing camber, camber_loc, and thickness.
        outputs : dict
            Output dictionary populated with airfoil_x and airfoil_y.
        """
        m = float(inputs["camber"][0]) / 100.0
        p = float(inputs["camber_loc"][0]) / 10.0
        t = float(inputs["thickness"][0]) / 100.0

        logger.debug(
            "NacaDiscipline.compute called (camber=%.1f, camber_loc=%.1f, thickness=%.1f)",
            inputs["camber"][0],
            inputs["camber_loc"][0],
            inputs["thickness"][0],
        )

        x_upper, x_lower = self._x_stations()

        # Compute upper surface
        yt_u = _thickness(x_upper, t)
        yc_u, dyc_u = _camber(x_upper, m, p)
        theta_u = np.arctan(dyc_u)
        xu = x_upper - yt_u * np.sin(theta_u)
        yu = yc_u + yt_u * np.cos(theta_u)

        # Compute lower surface
        yt_l = _thickness(x_lower, t)
        yc_l, dyc_l = _camber(x_lower, m, p)
        theta_l = np.arctan(dyc_l)
        xl = x_lower + yt_l * np.sin(theta_l)
        yl = yc_l - yt_l * np.cos(theta_l)

        # Selig format: TE -> upper -> LE -> lower -> TE
        outputs["airfoil_x"] = _selig(xu, xl)
        outputs["airfoil_y"] = _selig(yu, yl)

    def compute_partials(self, inputs, partials):
        """Compute analytical partial derivatives.

        Derivatives are computed via chain rule through the NACA 4-digit
        thickness distribution and mean camber line formulas.

        Parameters
        ----------
        inputs : dict
            Input dictionary containing camber, camber_loc, and thickness.
        partials : PairDict
            Jacobian dictionary to be populated.
        """
        m = float(inputs["camber"][0]) / 100.0
        p = float(inputs["camber_loc"][0]) / 10.0
        t = float(inputs["thickness"][0]) / 100.0

        x_upper, x_lower = self._x_stations()

        # Thickness polynomial (yt = 5*t*poly) and dyt/dt = 5*poly
        poly_u = _thickness_poly(x_upper)
        poly_l = _thickness_poly(x_lower)
        yt_u = 5.0 * t * poly_u
        yt_l = 5.0 * t * poly_l
        dyt_dt_u = 5.0 * poly_u
        dyt_dt_l = 5.0 * poly_l

        # Camber, slope, and their partials w.r.t. m and p
        _, dyc_u = _camber(x_upper, m, p)
        _, dyc_l = _camber(x_lower, m, p)
        dyc_dm_u, dyc_dp_u, ddyc_dm_u, ddyc_dp_u = _camber_partials(x_upper, m, p)
        dyc_dm_l, dyc_dp_l, ddyc_dm_l, ddyc_dp_l = _camber_partials(x_lower, m, p)

        # Precompute trig and arctan derivative factor
        theta_u = np.arctan(dyc_u)
        theta_l = np.arctan(dyc_l)
        cos_u = np.cos(theta_u)
        sin_u = np.sin(theta_u)
        cos_l = np.cos(theta_l)
        sin_l = np.sin(theta_l)
        atan_deriv_u = 1.0 / (1.0 + dyc_u**2)
        atan_deriv_l = 1.0 / (1.0 + dyc_l**2)

        # Upper surface: xu = x - yt*sin(theta), yu = yc + yt*cos(theta)
        # w.r.t. t
        dxu_dt = -sin_u * dyt_dt_u
        dyu_dt = cos_u * dyt_dt_u
        # w.r.t. m (via camber)
        dxu_dm = -yt_u * cos_u * atan_deriv_u * ddyc_dm_u
        dyu_dm = dyc_dm_u - yt_u * sin_u * atan_deriv_u * ddyc_dm_u
        # w.r.t. p (via camber)
        dxu_dp = -yt_u * cos_u * atan_deriv_u * ddyc_dp_u
        dyu_dp = dyc_dp_u - yt_u * sin_u * atan_deriv_u * ddyc_dp_u

        # Lower surface: xl = x + yt*sin(theta), yl = yc - yt*cos(theta)
        # w.r.t. t
        dxl_dt = sin_l * dyt_dt_l
        dyl_dt = -cos_l * dyt_dt_l
        # w.r.t. m
        dxl_dm = yt_l * cos_l * atan_deriv_l * ddyc_dm_l
        dyl_dm = dyc_dm_l + yt_l * sin_l * atan_deriv_l * ddyc_dm_l
        # w.r.t. p
        dxl_dp = yt_l * cos_l * atan_deriv_l * ddyc_dp_l
        dyl_dp = dyc_dp_l + yt_l * sin_l * atan_deriv_l * ddyc_dp_l

        # Chain rule: dm/d(camber)=0.01, dp/d(camber_loc)=0.1,
        #             dt/d(thickness)=0.01
        partials["airfoil_x", "camber"] = _selig(dxu_dm, dxl_dm) * 0.01
        partials["airfoil_x", "camber_loc"] = _selig(dxu_dp, dxl_dp) * 0.1
        partials["airfoil_x", "thickness"] = _selig(dxu_dt, dxl_dt) * 0.01

        partials["airfoil_y", "camber"] = _selig(dyu_dm, dyl_dm) * 0.01
        partials["airfoil_y", "camber_loc"] = _selig(dyu_dp, dyl_dp) * 0.1
        partials["airfoil_y", "thickness"] = _selig(dyu_dt, dyl_dt) * 0.01

    def _x_stations(self):
        """Compute cosine-spaced x coordinates for upper and lower surfaces."""
        n_upper = (self.n_points + 1) // 2
        n_lower = self.n_points - n_upper + 1

        beta_upper = np.linspace(0.0, np.pi, n_upper)
        x_upper = 0.5 * (1.0 - np.cos(beta_upper))

        beta_lower = np.linspace(0.0, np.pi, n_lower)
        x_lower = 0.5 * (1.0 - np.cos(beta_lower))

        return x_upper, x_lower


def _selig(upper, lower):
    """Combine upper/lower arrays in Selig order: upper reversed + lower[1:]."""
    return np.concatenate([upper[::-1], lower[1:]])


def _thickness_poly(x):
    """NACA 4-digit thickness polynomial (without 5t scaling factor).

    Parameters
    ----------
    x : numpy.ndarray
        Chordwise positions (0 to 1).

    Returns
    -------
    numpy.ndarray
        Polynomial values such that yt = 5 * t * poly(x).
    """
    return (
        0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4
    )


def _thickness(x, t):
    """NACA 4-digit thickness distribution.

    Parameters
    ----------
    x : numpy.ndarray
        Chordwise positions (0 to 1).
    t : float
        Maximum thickness as fraction of chord.

    Returns
    -------
    numpy.ndarray
        Half-thickness at each x position.
    """
    return 5.0 * t * _thickness_poly(x)


def _camber(x, m, p):
    """NACA 4-digit mean camber line and its derivative.

    Parameters
    ----------
    x : numpy.ndarray
        Chordwise positions (0 to 1).
    m : float
        Maximum camber as fraction of chord.
    p : float
        Position of maximum camber as fraction of chord.

    Returns
    -------
    yc : numpy.ndarray
        Camber line y-coordinates.
    dyc : numpy.ndarray
        Camber line slope (dy_c/dx).
    """
    yc = np.zeros_like(x)
    dyc = np.zeros_like(x)

    if m == 0.0 or p == 0.0:
        return yc, dyc

    fwd = x < p
    aft = ~fwd

    yc[fwd] = (m / p**2) * (2.0 * p * x[fwd] - x[fwd] ** 2)
    dyc[fwd] = (2.0 * m / p**2) * (p - x[fwd])

    yc[aft] = (m / (1.0 - p) ** 2) * ((1.0 - 2.0 * p) + 2.0 * p * x[aft] - x[aft] ** 2)
    dyc[aft] = (2.0 * m / (1.0 - p) ** 2) * (p - x[aft])

    return yc, dyc


def _camber_partials(x, m, p):
    """Partial derivatives of camber line and slope w.r.t. m and p.

    Parameters
    ----------
    x : numpy.ndarray
        Chordwise positions (0 to 1).
    m : float
        Maximum camber as fraction of chord.
    p : float
        Position of maximum camber as fraction of chord.

    Returns
    -------
    dyc_dm : numpy.ndarray
        Partial of camber y w.r.t. m.
    dyc_dp : numpy.ndarray
        Partial of camber y w.r.t. p.
    ddyc_dm : numpy.ndarray
        Partial of camber slope (dy_c/dx) w.r.t. m.
    ddyc_dp : numpy.ndarray
        Partial of camber slope (dy_c/dx) w.r.t. p.
    """
    dyc_dm = np.zeros_like(x)
    dyc_dp = np.zeros_like(x)
    ddyc_dm = np.zeros_like(x)
    ddyc_dp = np.zeros_like(x)

    if m == 0.0 or p == 0.0:
        return dyc_dm, dyc_dp, ddyc_dm, ddyc_dp

    fwd = x < p
    aft = ~fwd

    # Forward region (x < p)
    xf = x[fwd]
    dyc_dm[fwd] = (1.0 / p**2) * (2.0 * p * xf - xf**2)
    dyc_dp[fwd] = 2.0 * m * xf * (xf - p) / p**3
    ddyc_dm[fwd] = (2.0 / p**2) * (p - xf)
    ddyc_dp[fwd] = 2.0 * m * (2.0 * xf - p) / p**3

    # Aft region (x >= p)
    xa = x[aft]
    q = 1.0 - p
    dyc_dm[aft] = (1.0 / q**2) * ((1.0 - 2.0 * p) + 2.0 * p * xa - xa**2)
    dyc_dp[aft] = 2.0 * m * (1.0 - xa) * (xa - p) / q**3
    ddyc_dm[aft] = (2.0 / q**2) * (p - xa)
    ddyc_dp[aft] = 2.0 * m * (1.0 + p - 2.0 * xa) / q**3

    return dyc_dm, dyc_dp, ddyc_dm, ddyc_dp
