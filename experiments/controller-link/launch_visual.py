"""Launch two independent applications, or just one role for two computers."""

import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("both", "host", "controller"), default="both")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    # Each window owns its own process, memory and event loop. Neither receives
    # the other's process handle, model or UI variables.
    roles = ("controller", "host") if args.role == "both" else (args.role,)
    python = Path(sys.executable)
    if sys.platform == "win32" and python.with_name("pythonw.exe").exists():
        python = python.with_name("pythonw.exe")
    for role in roles:
        subprocess.Popen([str(python), str(root / f"{role}_gui.py")], cwd=root)


if __name__ == "__main__":
    main()
