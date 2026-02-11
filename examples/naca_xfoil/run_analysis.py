"""Coupled NACA + XFOIL analysis using OpenMDAO clients.

Starts NACA and XFOIL Philote servers in-process, builds an OpenMDAO
model that chains them, and evaluates aerodynamic coefficients for a
specified NACA 4-digit airfoil.

Usage:
    python run_analysis.py
"""

from concurrent import futures

import grpc
import openmdao.api as om
import philote_mdo.general as pmdo
from philote_mdo.openmdao import RemoteExplicitComponent

from philote_examples import NacaDiscipline, XfoilDiscipline

NACA_PORT = 50051
XFOIL_PORT = 50052
N_POINTS = 100


def _start_server(discipline, port):
    """Start a Philote server in a background thread."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    wrapped = pmdo.ExplicitServer(discipline=discipline)
    wrapped.attach_to_server(server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    return server


def run(camber=2, camber_loc=4, thickness=12, alpha=5.0, reynolds=1e6, mach=0.0):
    """Run a coupled NACA -> XFOIL analysis.

    Parameters
    ----------
    camber : float
        Max camber (first NACA digit, e.g. 2 for NACA 2412).
    camber_loc : float
        Max camber location (second NACA digit, e.g. 4 for NACA 2412).
    thickness : float
        Thickness (last two NACA digits, e.g. 12 for NACA 2412).
    alpha : float
        Angle of attack in degrees.
    reynolds : float
        Reynolds number.
    mach : float
        Mach number.
    """
    # Start servers
    naca_server = _start_server(NacaDiscipline(n_points=N_POINTS), NACA_PORT)
    xfoil_server = _start_server(XfoilDiscipline(n_points=N_POINTS), XFOIL_PORT)

    naca_channel = grpc.insecure_channel(f"localhost:{NACA_PORT}")
    xfoil_channel = grpc.insecure_channel(f"localhost:{XFOIL_PORT}")

    try:
        prob = om.Problem()

        prob.model.add_subsystem(
            "naca",
            RemoteExplicitComponent(channel=naca_channel),
            promotes_outputs=["airfoil_x", "airfoil_y"],
        )
        prob.model.add_subsystem(
            "xfoil",
            RemoteExplicitComponent(channel=xfoil_channel),
            promotes_inputs=["airfoil_x", "airfoil_y"],
        )

        prob.setup()

        prob.set_val("naca.camber", camber)
        prob.set_val("naca.camber_loc", camber_loc)
        prob.set_val("naca.thickness", thickness)

        prob.set_val("xfoil.alpha", alpha)
        prob.set_val("xfoil.reynolds", reynolds)
        prob.set_val("xfoil.mach", mach)

        prob.run_model()

        cl = prob.get_val("xfoil.cl")[0]
        cd = prob.get_val("xfoil.cd")[0]
        cm = prob.get_val("xfoil.cm")[0]

        print(
            f"NACA {camber}{camber_loc}{thickness:02g} at alpha={alpha} deg, "
            f"Re={reynolds:.0e}, M={mach}"
        )
        print(f"  Cl = {cl:.4f}")
        print(f"  Cd = {cd:.6f}")
        print(f"  Cm = {cm:.4f}")

        return cl, cd, cm

    finally:
        naca_channel.close()
        xfoil_channel.close()
        naca_server.stop(grace=1)
        xfoil_server.stop(grace=1)


if __name__ == "__main__":
    run()
