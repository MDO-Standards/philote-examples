"""Example server script for the OAS structural discipline (split aerostructural).

Usage:
    python struct_server.py
"""

from concurrent import futures

import grpc
import philote_mdo.general as pmdo

from philote_examples import OasSplitStructDiscipline


def run(port: int = 50053):
    """Start the OAS structural discipline server.

    Parameters
    ----------
    port : int, optional
        Port to listen on, by default 50053.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    discipline = pmdo.ExplicitServer(discipline=OasSplitStructDiscipline())
    discipline.attach_to_server(server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"OAS structural server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    run()
