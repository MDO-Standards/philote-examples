"""NACA 4-digit airfoil optimization using OpenMDAO and Scirocco.

Gradient-based airfoil shape optimization that minimizes drag subject to
lift and cross-sectional area constraints.  The geometry is parameterized
by NACA 4-digit variables (camber, camber location, thickness) plus the
angle of attack.  Scirocco provides viscous aerodynamic coefficients and
analytical adjoint sensitivities via a Philote gRPC server.

Architecture::

    [NACA4Geometry]  --x-->  [Scirocco (Philote)]  --cl,cd,cm-->  [SLSQP]
      analytical       |      analytical adjoint
      gradients        |      sensitivities
                       +-->  [AirfoilArea]  --area-->

Usage:
    # Start the Scirocco Philote server:
    #   scirocco_server localhost:50051
    #
    # Then run:
    #   python run_optimization.py
"""

from pathlib import Path

import grpc
import numpy as np
import openmdao.api as om
from philote_mdo.openmdao import RemoteExplicitComponent

# ---------------------------------------------------------------------------
# NACA 4-digit helper functions
# ---------------------------------------------------------------------------


def _thickness_poly(x):
    """NACA 4-digit thickness polynomial (without the 5t scaling)."""
    return (
        0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4
    )


def _thickness(x, t):
    """NACA 4-digit half-thickness distribution."""
    return 5.0 * t * _thickness_poly(x)


def _camber(x, m, p):
    """Mean camber line and slope dy_c/dx."""
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
    """Partials of camber (yc) and camber slope (dyc/dx) w.r.t. m and p."""
    dyc_dm = np.zeros_like(x)
    dyc_dp = np.zeros_like(x)
    ddyc_dm = np.zeros_like(x)
    ddyc_dp = np.zeros_like(x)

    if p == 0.0:
        return dyc_dm, dyc_dp, ddyc_dm, ddyc_dp

    fwd = x < p
    aft = ~fwd

    xf = x[fwd]
    dyc_dm[fwd] = (1.0 / p**2) * (2.0 * p * xf - xf**2)
    ddyc_dm[fwd] = (2.0 / p**2) * (p - xf)

    xa = x[aft]
    q = 1.0 - p
    dyc_dm[aft] = (1.0 / q**2) * ((1.0 - 2.0 * p) + 2.0 * p * xa - xa**2)
    ddyc_dm[aft] = (2.0 / q**2) * (p - xa)

    if m != 0.0:
        dyc_dp[fwd] = 2.0 * m * xf * (xf - p) / p**3
        ddyc_dp[fwd] = 2.0 * m * (2.0 * xf - p) / p**3
        dyc_dp[aft] = 2.0 * m * (1.0 - xa) * (xa - p) / q**3
        ddyc_dp[aft] = 2.0 * m * (1.0 + p - 2.0 * xa) / q**3

    return dyc_dm, dyc_dp, ddyc_dm, ddyc_dp


def _panel_order(upper, lower):
    """Combine upper/lower in Scirocco panel order (TE-lower-LE-upper-TE)."""
    return np.concatenate([lower[::-1], upper[1:]])


# ---------------------------------------------------------------------------
# NACA 4-digit geometry OpenMDAO component
# ---------------------------------------------------------------------------


class NACA4Geometry(om.ExplicitComponent):
    """NACA 4-digit airfoil geometry with analytical gradients.

    Produces airfoil coordinates in the panel ordering that Scirocco expects
    (trailing edge along the lower surface to the leading edge, then along the
    upper surface back to the trailing edge).

    The output ``x`` is a flat array of length ``2 * n_nodes`` laid out as
    ``[x_0 .. x_{N-1}, z_0 .. z_{N-1}]``, matching the Scirocco Philote
    discipline input.
    """

    def initialize(self):
        self.options.declare(
            "n_nodes", default=101, types=int, desc="Total number of panel nodes"
        )

    def setup(self):
        nn = self.options["n_nodes"]

        self.add_input("camber", val=2.0, desc="Max camber (first NACA digit, e.g. 2)")
        self.add_input(
            "camber_loc", val=4.0, desc="Camber location (second NACA digit, e.g. 4)"
        )
        self.add_input(
            "thickness", val=12.0, desc="Thickness (last two NACA digits, e.g. 12)"
        )

        self.add_output(
            "x", shape=(2 * nn,), units="m", desc="Panel coordinates [x; z] flattened"
        )

        self.declare_partials("x", ["camber", "camber_loc", "thickness"])

    def _x_stations(self):
        """Cosine-spaced chordwise stations for upper and lower surfaces."""
        nn = self.options["n_nodes"]
        n_upper = (nn + 1) // 2
        n_lower = nn - n_upper + 1

        beta_u = np.linspace(0.0, np.pi, n_upper)
        x_upper = 0.5 * (1.0 - np.cos(beta_u))

        beta_l = np.linspace(0.0, np.pi, n_lower)
        x_lower = 0.5 * (1.0 - np.cos(beta_l))

        return x_upper, x_lower

    def compute(self, inputs, outputs):
        m = float(inputs["camber"][0]) / 100.0
        p = float(inputs["camber_loc"][0]) / 10.0
        t = float(inputs["thickness"][0]) / 100.0

        x_upper, x_lower = self._x_stations()

        yt_u = _thickness(x_upper, t)
        yc_u, dyc_u = _camber(x_upper, m, p)
        theta_u = np.arctan(dyc_u)
        xu = x_upper - yt_u * np.sin(theta_u)
        yu = yc_u + yt_u * np.cos(theta_u)

        yt_l = _thickness(x_lower, t)
        yc_l, dyc_l = _camber(x_lower, m, p)
        theta_l = np.arctan(dyc_l)
        xl = x_lower + yt_l * np.sin(theta_l)
        yl = yc_l - yt_l * np.cos(theta_l)

        nn = self.options["n_nodes"]
        outputs["x"][:nn] = _panel_order(xu, xl)
        outputs["x"][nn:] = _panel_order(yu, yl)

    def compute_partials(self, inputs, partials):
        m = float(inputs["camber"][0]) / 100.0
        p = float(inputs["camber_loc"][0]) / 10.0
        t = float(inputs["thickness"][0]) / 100.0

        x_upper, x_lower = self._x_stations()
        nn = self.options["n_nodes"]

        poly_u = _thickness_poly(x_upper)
        poly_l = _thickness_poly(x_lower)
        yt_u = 5.0 * t * poly_u
        yt_l = 5.0 * t * poly_l
        dyt_dt_u = 5.0 * poly_u
        dyt_dt_l = 5.0 * poly_l

        _, dyc_u = _camber(x_upper, m, p)
        _, dyc_l = _camber(x_lower, m, p)
        dyc_dm_u, dyc_dp_u, ddyc_dm_u, ddyc_dp_u = _camber_partials(x_upper, m, p)
        dyc_dm_l, dyc_dp_l, ddyc_dm_l, ddyc_dp_l = _camber_partials(x_lower, m, p)

        theta_u = np.arctan(dyc_u)
        theta_l = np.arctan(dyc_l)
        cos_u, sin_u = np.cos(theta_u), np.sin(theta_u)
        cos_l, sin_l = np.cos(theta_l), np.sin(theta_l)
        at_u = 1.0 / (1.0 + dyc_u**2)
        at_l = 1.0 / (1.0 + dyc_l**2)

        dxu_dt = -sin_u * dyt_dt_u
        dyu_dt = cos_u * dyt_dt_u
        dxu_dm = -yt_u * cos_u * at_u * ddyc_dm_u
        dyu_dm = dyc_dm_u - yt_u * sin_u * at_u * ddyc_dm_u
        dxu_dp = -yt_u * cos_u * at_u * ddyc_dp_u
        dyu_dp = dyc_dp_u - yt_u * sin_u * at_u * ddyc_dp_u

        dxl_dt = sin_l * dyt_dt_l
        dyl_dt = -cos_l * dyt_dt_l
        dxl_dm = yt_l * cos_l * at_l * ddyc_dm_l
        dyl_dm = dyc_dm_l + yt_l * sin_l * at_l * ddyc_dm_l
        dxl_dp = yt_l * cos_l * at_l * ddyc_dp_l
        dyl_dp = dyc_dp_l + yt_l * sin_l * at_l * ddyc_dp_l

        jac_m = np.zeros(2 * nn)
        jac_p = np.zeros(2 * nn)
        jac_t = np.zeros(2 * nn)

        jac_m[:nn] = _panel_order(dxu_dm, dxl_dm) * 0.01
        jac_m[nn:] = _panel_order(dyu_dm, dyl_dm) * 0.01

        jac_p[:nn] = _panel_order(dxu_dp, dxl_dp) * 0.1
        jac_p[nn:] = _panel_order(dyu_dp, dyl_dp) * 0.1

        jac_t[:nn] = _panel_order(dxu_dt, dxl_dt) * 0.01
        jac_t[nn:] = _panel_order(dyu_dt, dyl_dt) * 0.01

        partials["x", "camber"] = jac_m
        partials["x", "camber_loc"] = jac_p
        partials["x", "thickness"] = jac_t


# ---------------------------------------------------------------------------
# Airfoil area component (shoelace formula)
# ---------------------------------------------------------------------------


class AirfoilArea(om.ExplicitComponent):
    """Cross-sectional area from panel coordinates via the shoelace formula."""

    def initialize(self):
        self.options.declare("n_nodes", default=101, types=int)

    def setup(self):
        nn = self.options["n_nodes"]
        self.add_input("x", shape=(2 * nn,), units="m")
        self.add_output("area", val=0.0, units="m**2")
        self.declare_partials("area", "x")

    def compute(self, inputs, outputs):
        nn = self.options["n_nodes"]
        xc = inputs["x"][:nn]
        zc = inputs["x"][nn:]
        xn = np.roll(xc, -1)
        zn = np.roll(zc, -1)
        outputs["area"] = 0.5 * np.abs(np.sum(xc * zn - xn * zc))

    def compute_partials(self, inputs, partials):
        nn = self.options["n_nodes"]
        xc = inputs["x"][:nn]
        zc = inputs["x"][nn:]
        xn = np.roll(xc, -1)
        zn = np.roll(zc, -1)

        cross_sum = np.sum(xc * zn - xn * zc)
        sign = np.sign(cross_sum) if cross_sum != 0.0 else 1.0

        da_dxc = 0.5 * sign * (zn - np.roll(zc, 1))
        da_dzc = 0.5 * sign * (np.roll(xc, 1) - xn)

        jac = np.zeros(2 * nn)
        jac[:nn] = da_dxc
        jac[nn:] = da_dzc
        partials["area", "x"] = jac


# ---------------------------------------------------------------------------
# Reference area computation
# ---------------------------------------------------------------------------


def _reference_area(nn, camber=2.0, camber_loc=4.0, thickness=12.0):
    """Compute the cross-sectional area for a reference NACA airfoil."""
    ref = om.Problem()
    ref.model.add_subsystem("g", NACA4Geometry(n_nodes=nn))
    ref.model.add_subsystem("a", AirfoilArea(n_nodes=nn))
    ref.model.connect("g.x", "a.x")
    ref.setup()
    ref.set_val("g.camber", camber)
    ref.set_val("g.camber_loc", camber_loc)
    ref.set_val("g.thickness", thickness)
    ref.run_model()
    return float(ref.get_val("a.area")[0]), ref.get_val("g.x").copy()


# ---------------------------------------------------------------------------
# Single-point analysis
# ---------------------------------------------------------------------------


def run_analysis(channel, npanel=100):
    """Run a single-point NACA 2412 analysis.

    Parameters
    ----------
    channel : grpc.Channel
        gRPC channel connected to the Scirocco Philote server.
    npanel : int
        Number of panels for the Scirocco analysis.
    """
    nn = npanel + 1

    prob = om.Problem()
    model = prob.model

    model.add_subsystem(
        "geometry",
        NACA4Geometry(n_nodes=nn),
        promotes_outputs=["x"],
    )
    model.add_subsystem(
        "analysis",
        RemoteExplicitComponent(channel=channel, naca="0012", npanel=npanel),
        promotes_inputs=["x"],
    )

    prob.setup()

    prob.set_val("geometry.camber", 2.0)
    prob.set_val("geometry.camber_loc", 4.0)
    prob.set_val("geometry.thickness", 12.0)
    prob.set_val("analysis.alpha", 5.0)
    prob.set_val("analysis.Re", 1e6)
    prob.set_val("analysis.Ma", 0.0)

    prob.run_model()

    cl = prob.get_val("analysis.cl")[0]
    cd = prob.get_val("analysis.cd")[0]
    cm = prob.get_val("analysis.cm")[0]

    print("=" * 60)
    print("Single-Point Analysis: NACA 2412")
    print("=" * 60)
    print("  alpha = 5.0 deg, Re = 1e6, Ma = 0.0")
    print(f"  Cl = {cl:.6f}")
    print(f"  Cd = {cd:.6f}")
    print(f"  Cm = {cm:.6f}")
    print("=" * 60)

    return prob


# ---------------------------------------------------------------------------
# Derivative check
# ---------------------------------------------------------------------------


def run_check_derivatives(channel, npanel=100):
    """Check total derivatives through both components.

    Parameters
    ----------
    channel : grpc.Channel
        gRPC channel connected to the Scirocco Philote server.
    npanel : int
        Number of panels for the Scirocco analysis.
    """
    nn = npanel + 1

    prob = om.Problem()
    model = prob.model

    model.add_subsystem(
        "geometry",
        NACA4Geometry(n_nodes=nn),
        promotes_outputs=["x"],
    )
    model.add_subsystem(
        "area_comp",
        AirfoilArea(n_nodes=nn),
        promotes_inputs=["x"],
    )
    model.add_subsystem(
        "analysis",
        RemoteExplicitComponent(channel=channel, naca="0012", npanel=npanel),
        promotes_inputs=["x"],
    )

    prob.setup()

    prob.set_val("geometry.camber", 2.0)
    prob.set_val("geometry.camber_loc", 4.0)
    prob.set_val("geometry.thickness", 12.0)
    prob.set_val("analysis.alpha", 5.0)
    prob.set_val("analysis.Re", 1e6)
    prob.set_val("analysis.Ma", 0.0)

    prob.run_model()

    print("\n" + "=" * 60)
    print("Derivative Check")
    print("=" * 60)

    totals = prob.check_totals(
        of=["analysis.cl", "analysis.cd", "analysis.cm", "area_comp.area"],
        wrt=[
            "geometry.camber",
            "geometry.camber_loc",
            "geometry.thickness",
            "analysis.alpha",
        ],
        compact_print=True,
    )

    print("=" * 60)
    return totals


# ---------------------------------------------------------------------------
# Optimization
# ---------------------------------------------------------------------------


def run_optimization(channel, target_cl=0.5, npanel=100):
    """Minimize drag subject to lift and area constraints.

    Parameters
    ----------
    channel : grpc.Channel
        gRPC channel connected to the Scirocco Philote server.
    target_cl : float
        Target lift coefficient (equality constraint).
    npanel : int
        Number of panels for the Scirocco analysis.
    """
    nn = npanel + 1
    hdf5_path = str(Path(__file__).with_name("optimization_history.h5"))

    init_area, x_init = _reference_area(nn, camber=0.0, camber_loc=4.0, thickness=12.0)

    prob = om.Problem()
    model = prob.model

    model.add_subsystem(
        "geometry",
        NACA4Geometry(n_nodes=nn),
        promotes_outputs=["x"],
    )
    model.add_subsystem(
        "area_comp",
        AirfoilArea(n_nodes=nn),
        promotes_inputs=["x"],
    )
    model.add_subsystem(
        "analysis",
        RemoteExplicitComponent(
            channel=channel,
            naca="0012",
            npanel=npanel,
            hdf5_file=hdf5_path,
        ),
        promotes_inputs=["x"],
    )

    prob.driver = om.ScipyOptimizeDriver()
    prob.driver.options["optimizer"] = "SLSQP"
    prob.driver.options["tol"] = 1e-6
    prob.driver.options["maxiter"] = 200
    prob.driver.options["disp"] = True

    model.add_design_var("geometry.camber", lower=0.0, upper=9.0, ref=9.0)
    model.add_design_var("geometry.camber_loc", lower=1.0, upper=9.0, ref=9.0)
    model.add_design_var("geometry.thickness", lower=1.0, upper=40.0, ref=40.0)
    model.add_design_var("analysis.alpha", lower=-5.0, upper=15.0, ref=10.0)

    model.add_objective("analysis.cd", ref=0.01)
    model.add_constraint("analysis.cl", equals=target_cl, ref=target_cl)
    min_area = 0.8 * init_area
    model.add_constraint("area_comp.area", lower=min_area, ref=init_area)

    prob.setup()

    prob.set_val("geometry.camber", 0.0)
    prob.set_val("geometry.camber_loc", 4.0)
    prob.set_val("geometry.thickness", 12.0)
    prob.set_val("analysis.alpha", 5.0)
    prob.set_val("analysis.Re", 1e6)
    prob.set_val("analysis.Ma", 0.0)

    print("\n" + "=" * 60)
    print(f"Optimization: minimize Cd, target Cl = {target_cl}")
    print(f"  Area constraint: area >= {min_area:.6f} (80% of NACA 0012)")
    print("=" * 60 + "\n")

    prob.run_driver()

    camber = prob.get_val("geometry.camber")[0]
    camber_loc = prob.get_val("geometry.camber_loc")[0]
    thickness = prob.get_val("geometry.thickness")[0]
    alpha = prob.get_val("analysis.alpha")[0]
    cl = prob.get_val("analysis.cl")[0]
    cd = prob.get_val("analysis.cd")[0]
    cm = prob.get_val("analysis.cm")[0]
    area = prob.get_val("area_comp.area")[0]

    print("\n" + "=" * 60)
    print("Optimization Results")
    print("=" * 60)
    print(f"  camber     = {camber:.4f}  (m = {camber / 100:.4f})")
    print(f"  camber_loc = {camber_loc:.4f}  (p = {camber_loc / 10:.4f})")
    print(f"  thickness  = {thickness:.4f}  (t = {thickness / 100:.4f})")
    print(f"  alpha      = {alpha:.4f} deg")
    print(f"  Cl = {cl:.6f}")
    print(f"  Cd = {cd:.6f}")
    print(f"  Cm = {cm:.6f}")
    print(f"  Area = {area:.6f} (min = {min_area:.6f})")
    print(f"  Iteration history: {hdf5_path}")
    print("=" * 60)

    x_opt = prob.get_val("x").copy()
    _plot_results(x_init, x_opt, nn, target_cl, cd, alpha)

    return prob


def _plot_results(x_init, x_opt, nn, target_cl, opt_cd, opt_alpha):
    """Plot initial vs optimized airfoil shapes."""
    import matplotlib.pyplot as plt

    xi, zi = x_init[:nn], x_init[nn:]
    xo, zo = x_opt[:nn], x_opt[nn:]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(xi, zi, "b--", lw=1.2, label="Initial (NACA 0012)")
    ax.plot(xo, zo, "r-", lw=1.8, label="Optimized")
    ax.fill_between(xo, zo, alpha=0.08, color="red")
    ax.set_xlabel("x/c")
    ax.set_ylabel("z/c")
    ax.set_title(
        rf"NACA 4-Digit Optimization — min $C_d$ s.t. $C_l = {target_cl}$"
        "\n"
        rf"Optimized: $C_d = {opt_cd:.5f}$,  "
        rf"$\alpha = {opt_alpha:.2f}°$"
    )
    ax.set_aspect("equal")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = Path(__file__).with_name("naca_optimization_result.png")
    fig.savefig(out, dpi=150)
    plt.show()
    print(f"Plot saved to {out}")


if __name__ == "__main__":
    address = "localhost:50051"
    channel = grpc.insecure_channel(address)

    run_analysis(channel)
    run_check_derivatives(channel)
    run_optimization(channel, target_cl=0.5)

    channel.close()
