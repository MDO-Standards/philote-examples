"""NACA 4-digit airfoil Philote discipline."""

import numpy as np
import philote_mdo.general as pmdo


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

    def setup(self):
        """Define inputs and outputs for the NACA discipline."""
        self.add_input("digit_1", shape=(1,), units="")
        self.add_input("digit_2", shape=(1,), units="")
        self.add_input("digit_3", shape=(1,), units="")
        self.add_input("digit_4", shape=(1,), units="")

        self.add_output("airfoil_x", shape=(self.n_points,), units="")
        self.add_output("airfoil_y", shape=(self.n_points,), units="")

    def compute(self, inputs, outputs):
        """Generate NACA 4-digit airfoil coordinates.

        Parameters
        ----------
        inputs : dict
            Input dictionary containing digit_1 through digit_4.
        outputs : dict
            Output dictionary populated with airfoil_x and airfoil_y.
        """
        d1 = float(inputs["digit_1"][0])
        d2 = float(inputs["digit_2"][0])
        d3 = float(inputs["digit_3"][0])
        d4 = float(inputs["digit_4"][0])

        m = d1 / 100.0  # max camber
        p = d2 / 10.0  # position of max camber
        t = (d3 * 10.0 + d4) / 100.0  # thickness ratio

        # Split points between upper and lower surfaces.
        # The LE point is shared, so n_upper + n_lower - 1 = n_points.
        n_upper = (self.n_points + 1) // 2
        n_lower = self.n_points - n_upper + 1

        # Cosine-spaced x coordinates from LE (0) to TE (1)
        beta_upper = np.linspace(0.0, np.pi, n_upper)
        x_upper = 0.5 * (1.0 - np.cos(beta_upper))

        beta_lower = np.linspace(0.0, np.pi, n_lower)
        x_lower = 0.5 * (1.0 - np.cos(beta_lower))

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
        # Upper reversed (TE to LE), then lower without duplicate LE (LE+1 to TE)
        outputs["airfoil_x"] = np.concatenate([xu[::-1], xl[1:]])
        outputs["airfoil_y"] = np.concatenate([yu[::-1], yl[1:]])


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
    return (
        5.0
        * t
        * (
            0.2969 * np.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x**2
            + 0.2843 * x**3
            - 0.1015 * x**4
        )
    )


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

    yc[aft] = (m / (1.0 - p) ** 2) * (
        (1.0 - 2.0 * p) + 2.0 * p * x[aft] - x[aft] ** 2
    )
    dyc[aft] = (2.0 * m / (1.0 - p) ** 2) * (p - x[aft])

    return yc, dyc
