from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve SanMitra local frontend workspace.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=3300, type=int)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    frontend_root = repo_root / "frontend"
    handler = partial(SimpleHTTPRequestHandler, directory=str(frontend_root))
    server = ThreadingHTTPServer((args.host, args.port), handler)

    print(f"Serving SanMitra frontends from {frontend_root}")
    print(f"Index: http://{args.host}:{args.port}/")
    print(f"MitraBooks ERP: http://{args.host}:{args.port}/mitrabooks-erp/")
    print(f"LegalMitra: http://{args.host}:{args.port}/legalmitra/")
    print(f"InvestMitra: http://{args.host}:{args.port}/investmitra/")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping frontend server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
