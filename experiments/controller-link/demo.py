"""Run the feasibility experiment against separate simulator processes."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import queue
import subprocess
import sys
import threading

from host import Client, LinkError, ResponseTimeout, UnresolvedOperation
from protocol import ProtocolError

ROOT = Path(__file__).resolve().parent


@contextmanager
def simulator(fault="none"):
    process = subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "simulator.py"), "--port", "0", "--fault", fault],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=ROOT,
    )
    ready = queue.Queue()
    threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True).start()
    try:
        try:
            line = ready.get(timeout=10)
        except queue.Empty as exc:
            raise RuntimeError("Simulator did not start within 10 seconds") from exc
        if not line:
            raise RuntimeError(f"Simulator failed: {process.stderr.read()}")
        yield f"socket://127.0.0.1:{json.loads(line)['port']}"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def round_trip():
    with simulator() as port, Client(port, timeout=0.5) as client:
        opened = client.command("OPEN", request_id="demo-open")
        closed = client.command("CLOSE", request_id="demo-close")
        require(opened["state"] == "OPENED" and closed["state"] == "CLOSED", "Incorrect state sequence")
        return {"observed": "OPEN -> OPENED; CLOSE -> CLOSED", "wire_log": client.events}


def replay():
    with simulator() as port, Client(port, timeout=0.5) as client:
        first = client.command("OPEN", request_id="same-command")
        second = client.command("OPEN", request_id="same-command")
        require(first == second and second["actuation_count"] == 1, "Duplicate caused another simulated actuation")
        return {"observed": "Identical request replayed; simulated actuation count remained 1", "wire_log": client.events}


def fault_case(fault, expected_error):
    with simulator(fault) as port, Client(port, timeout=0.5) as client:
        try:
            client.command("OPEN", request_id=f"fault-{fault}")
        except expected_error as exc:
            observed_error = str(exc)
        else:
            raise AssertionError("Fault was incorrectly accepted as success")
        require("compartment_1" in client.unresolved, "Uncertain operation was not tracked")
        writes = sum(e["direction"] == "TX" for e in client.events)
        try:
            client.command("OPEN")
        except UnresolvedOperation:
            pass
        else:
            raise AssertionError("Another operation was allowed before reconciliation")
        require(sum(e["direction"] == "TX" for e in client.events) == writes, "Blocked request was transmitted")
        client.connect()
        status = client.command("STATUS")
        require(status["state"] == "OPENED" and status["actuation_count"] == 1, "Simulator state not reconciled")
        require(not client.unresolved, "Unresolved flag not cleared")
        client.command("CLOSE")
        return {
            "observed": f"{observed_error}; no automatic retry; new OPEN blocked; reconnect + STATUS found OPENED; CLOSE succeeded",
            "wire_log": client.events,
        }


CASES = [
    ("round-trip", "Two programs exchange OPEN/CLOSE and validate responses", round_trip),
    ("duplicate", "Same ID and payload do not repeat a simulated actuation", replay),
    ("timeout", "Lost acknowledgment is unresolved, not retried", lambda: fault_case("timeout", ResponseTimeout)),
    ("malformed", "Malformed response is rejected", lambda: fault_case("malformed", ProtocolError)),
    ("wrong-id", "Unrelated response is rejected", lambda: fault_case("wrong-id", ProtocolError)),
    ("disconnect", "Connection loss is unresolved and can be queried after reconnect", lambda: fault_case("disconnect", LinkError)),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "latest.json")
    args = parser.parse_args()
    print("SMART PILL DISPENSER / SOFTWARE COMMUNICATION FEASIBILITY")
    print("Host <-> pySerial socket transport <-> separate simulated controller")
    print("No board, serial electrical link, sensor, or mechanism is being tested.\n")
    try:
        source_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        source_dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        ).strip())
    except (OSError, subprocess.CalledProcessError):
        source_commit, source_dirty = None, None
    report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit, "working_tree_dirty": source_dirty,
        "python": platform.python_version(), "platform": platform.platform(),
        "pyserial": importlib.metadata.version("pyserial"),
        "transport": "localhost TCP via pySerial socket://; not physical serial",
        "controller": "separate Python subprocess; proposed protocol v1; six illustrative compartments",
        "cases": [],
    }
    for name, expected, run in CASES:
        case = {"name": name, "expected": expected}
        try:
            case.update(run(), passed=True)
        except Exception as exc:
            case.update(passed=False, observed=f"{type(exc).__name__}: {exc}")
        report["cases"].append(case)
        print(f"[{'PASS' if case['passed'] else 'FAIL'}] {name}: {case['observed']}")
    report["passed"] = all(case["passed"] for case in report["cases"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nEvidence saved: {args.output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
