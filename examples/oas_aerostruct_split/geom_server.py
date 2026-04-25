"""Example server script for the OAS geometry discipline (split aerostructural).

Usage:
    python geom_server.py
"""

from concurrent import futures

import grpc
import philote_mdo.general as pmdo

from philote_examples import OasGeomDiscipline


def run(port: int = 50051):
    """Start the OAS geometry discipline server.

    Parameters
    ----------
    port : int, optional
        Port to listen on, by default 50051.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    discipline = pmdo.ExplicitServer(discipline=OasGeomDiscipline())
    discipline.attach_to_server(server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"OAS geometry server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    run()
