"""Integration test: NACA discipline -> XFOIL discipline chain.

Starts both servers, builds an OpenMDAO model that chains them, and
computes aero coefficients for a NACA 2412 airfoil.
"""

import time
from concurrent import futures

import grpc
import numpy as np
import openmdao.api as om
import philote_mdo.general as pmdo
from philote_mdo.openmdao import RemoteExplicitComponent

from philote_examples import NacaDiscipline, XfoilDiscipline

N_POINTS = 100
NACA_PORT = 50070
XFOIL_PORT = 50071


def _start_server(discipline, port):
    """Start a Philote server in a background thread."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    wrapped = pmdo.ExplicitServer(discipline=discipline)
    wrapped.attach_to_server(server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    return server


def test_naca_xfoil_chain():
    # Start servers
    naca_server = _start_server(NacaDiscipline(n_points=N_POINTS), NACA_PORT)
    xfoil_server = _start_server(XfoilDiscipline(n_points=N_POINTS), XFOIL_PORT)
    time.sleep(0.5)

    try:
        # Build OpenMDAO model
        prob = om.Problem()

        naca_channel = grpc.insecure_channel(f"localhost:{NACA_PORT}")
        xfoil_channel = grpc.insecure_channel(f"localhost:{XFOIL_PORT}")

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

        # NACA 2412
        prob.set_val("naca.camber", 2.0)
        prob.set_val("naca.camber_loc", 4.0)
        prob.set_val("naca.thickness", 12.0)

        # Flight conditions
        prob.set_val("xfoil.alpha", 5.0)
        prob.set_val("xfoil.reynolds", 1e6)
        prob.set_val("xfoil.mach", 0.0)

        prob.run_model()

        cl = prob.get_val("xfoil.cl")[0]
        cd = prob.get_val("xfoil.cd")[0]
        cm = prob.get_val("xfoil.cm")[0]

        print(f"NACA 2412 at alpha=5 deg, Re=1e6:")
        print(f"  Cl = {cl:.4f}")
        print(f"  Cd = {cd:.6f}")
        print(f"  Cm = {cm:.4f}")

        # Sanity checks for NACA 2412 at 5 deg AoA
        assert 0.5 < cl < 1.5, f"Cl={cl} out of expected range"
        assert 0.0 < cd < 0.05, f"Cd={cd} out of expected range"
        assert -0.15 < cm < 0.0, f"Cm={cm} out of expected range"

    finally:
        naca_server.stop(grace=1)
        xfoil_server.stop(grace=1)
        naca_channel.close()
        xfoil_channel.close()


def test_naca_xfoil_inviscid():
    # Start servers
    naca_server = _start_server(NacaDiscipline(n_points=N_POINTS), NACA_PORT)
    xfoil_server = _start_server(XfoilDiscipline(n_points=N_POINTS), XFOIL_PORT)
    time.sleep(0.5)

    try:
        # Build OpenMDAO model
        prob = om.Problem()

        naca_channel = grpc.insecure_channel(f"localhost:{NACA_PORT}")
        xfoil_channel = grpc.insecure_channel(f"localhost:{XFOIL_PORT}")

        prob.model.add_subsystem(
            "naca",
            RemoteExplicitComponent(channel=naca_channel),
            promotes_outputs=["airfoil_x", "airfoil_y"],
        )
        prob.model.add_subsystem(
            "xfoil",
            RemoteExplicitComponent(channel=xfoil_channel, viscous=False),
            promotes_inputs=["airfoil_x", "airfoil_y"],
        )

        prob.setup()

        # NACA 2412
        prob.set_val("naca.camber", 2.0)
        prob.set_val("naca.camber_loc", 4.0)
        prob.set_val("naca.thickness", 12.0)

        # Flight conditions (no reynolds/mach needed for inviscid)
        prob.set_val("xfoil.alpha", 5.0)

        prob.run_model()

        cl = prob.get_val("xfoil.cl")[0]
        cd = prob.get_val("xfoil.cd")[0]
        cm = prob.get_val("xfoil.cm")[0]

        print(f"NACA 2412 at alpha=5 deg (inviscid):")
        print(f"  Cl = {cl:.4f}")
        print(f"  Cd = {cd:.6f}")
        print(f"  Cm = {cm:.4f}")

        # Sanity checks for inviscid NACA 2412 at 5 deg AoA
        assert 0.5 < cl < 1.5, f"Cl={cl} out of expected range"
        assert cd == 0.0, f"Cd={cd} should be zero for inviscid"
        assert -0.15 < cm < 0.0, f"Cm={cm} out of expected range"

    finally:
        naca_server.stop(grace=1)
        xfoil_server.stop(grace=1)
        naca_channel.close()
        xfoil_channel.close()


if __name__ == "__main__":
    test_naca_xfoil_chain()
