"""Example server script for the OpenAeroStruct VLM discipline.

This script demonstrates how to run the OasDiscipline as a Philote server.

Usage:
    python server.py
"""

from concurrent import futures

import grpc
import philote_mdo.general as pmdo

from philote_examples import OasDiscipline


def run(port: int = 50051):
    """Start the OAS VLM discipline server.

    Parameters
    ----------
    port : int, optional
        Port to listen on, by default 50051.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    discipline = pmdo.ExplicitServer(discipline=OasDiscipline())
    discipline.attach_to_server(server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"OAS VLM server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    run()
