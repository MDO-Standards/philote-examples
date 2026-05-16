"""OpenAeroStruct VLM analysis with a large CRM wing mesh.

Same analysis as the small-mesh ``oas_vlm`` example but with 21 spanwise
and 7 chordwise panels for higher fidelity.

Usage:
    python run_analysis.py
"""

from concurrent import futures

import grpc
import numpy as np
import openmdao.api as om
import philote_mdo.general as pmdo
from philote_mdo.openmdao import RemoteExplicitComponent

from philote_examples import OasDiscipline

MESH_DICT = {
    "num_y": 21,
    "num_x": 7,
    "wing_type": "CRM",
    "symmetry": True,
    "num_twist_cp": 5,
}

SURFACE_OPTIONS = {
    "with_viscous": True,
    "CD0": 0.015,
}

PORT = 50051


def _start_server(discipline, port):
    """Start a Philote server in a background thread."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    wrapped = pmdo.ExplicitServer(discipline=discipline)
    wrapped.attach_to_server(server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    return server


def run(
    v=248.136,
    alpha=5.0,
    mach_number=0.84,
    re=1e6,
    rho=0.38,
    start_server=True,
):
    """Run an OAS VLM aerodynamic analysis (large mesh).

    Parameters
    ----------
    v : float
        Freestream velocity in m/s.
    alpha : float
        Angle of attack in degrees.
    mach_number : float
        Freestream Mach number.
    re : float
        Reynolds number per unit length in 1/m.
    rho : float
        Air density in kg/m**3.
    start_server : bool
        If True, start the gRPC server in-process. Set to False when
        connecting to an already-running server.
    """
    if start_server:
        oas_server = _start_server(
            OasDiscipline(mesh_dict=MESH_DICT, surface_options=SURFACE_OPTIONS),
            PORT,
        )

    channel = grpc.insecure_channel(f"localhost:{PORT}")

    try:
        prob = om.Problem()

        prob.model.add_subsystem(
            "oas",
            RemoteExplicitComponent(channel=channel),
        )

        prob.setup()

        prob.set_val("oas.v", v)
        prob.set_val("oas.alpha", alpha)
        prob.set_val("oas.Mach_number", mach_number)
        prob.set_val("oas.re", re)
        prob.set_val("oas.rho", rho)
        prob.set_val("oas.cg", np.zeros(3))

        prob.run_model()

        cl = prob.get_val("oas.CL")[0]
        cd = prob.get_val("oas.CD")[0]
        cm = prob.get_val("oas.CM")

        print(
            f"OAS VLM analysis (large mesh): v={v} m/s, alpha={alpha} deg, "
            f"M={mach_number}, Re={re:.0e}/m, rho={rho} kg/m^3"
        )
        print(f"  CL = {cl:.4f}")
        print(f"  CD = {cd:.6f}")
        print(f"  CM = [{cm[0]:.4f}, {cm[1]:.4f}, {cm[2]:.4f}]")

        return cl, cd, cm

    finally:
        channel.close()
        if start_server:
            oas_server.stop(grace=1)


if __name__ == "__main__":
    run()
