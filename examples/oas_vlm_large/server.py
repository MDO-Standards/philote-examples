"""Example server script for the OAS VLM discipline (large mesh).

Uses a CRM wing with 21 spanwise and 7 chordwise panels for higher
fidelity compared to the default small-mesh example.

Usage:
    python server.py
"""

from concurrent import futures

import grpc
import philote_mdo.general as pmdo

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


def run(port: int = 50051):
    """Start the OAS VLM discipline server (large mesh).

    Parameters
    ----------
    port : int, optional
        Port to listen on, by default 50051.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    discipline = pmdo.ExplicitServer(
        discipline=OasDiscipline(mesh_dict=MESH_DICT, surface_options=SURFACE_OPTIONS)
    )
    discipline.attach_to_server(server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"OAS VLM server (large mesh) started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    run()
