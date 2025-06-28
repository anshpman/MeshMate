# node.py - Main Entry Point

import argparse
from tui import NodeApp

def main():
    """
    Parses command-line arguments and launches the Textual application.
    """
    parser = argparse.ArgumentParser(description="Run a MeshMate node.")
    parser.add_argument("--port", type=int, required=True, help="Port for this node to listen on.")
    parser.add_argument("--peers", type=str, default="", help="Comma-separated list of peer ports to connect to.")
    
    args = parser.parse_args()
    peer_ports = [int(p) for p in args.peers.split(',') if p]
    
    # Create an instance of our Textual app and run it
    app = NodeApp(host="127.0.0.1", port=args.port, peers=peer_ports)
    app.run()

if __name__ == "__main__":
    main()