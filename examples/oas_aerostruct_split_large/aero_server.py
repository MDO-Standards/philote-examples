"""Example server script for the OAS aero discipline (large mesh).

Usage:
    python aero_server.py
"""

from concurrent import futures

import grpc
import philote_mdo.general as pmdo

from philote_examples import OasSplitAeroDiscipline

MESH_DICT = {
    "num_y": 21,
    "num_x": 7,
    "wing_type": "CRM",
    "symmetry": True,
    "num_twist_cp": 5,
}


def run(port: int = 50052):
    """Start the OAS aero discipline server (large mesh).

    Parameters
    ----------
    port : int, optional
        Port to listen on, by default 50052.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    discipline = pmdo.ExplicitServer(
        discipline=OasSplitAeroDiscipline(mesh_dict=MESH_DICT)
    )
    discipline.attach_to_server(server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"OAS aero server (large mesh) started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    run()
