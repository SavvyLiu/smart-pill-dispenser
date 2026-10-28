# Software-to-controller communication feasibility experiment

**Question:** Can we install and run a host-side communication library, exchange compartment commands with a separate controller program, and recognize missing or invalid responses?

This is a small software experiment, not a dispenser prototype. It includes no medication scheduling, dispensing mechanism, sensor integration, or patient data.

## Visual demo for a meeting

Double-click **run-visual.cmd** on Windows, or run `python launch_visual.py` after installing the requirements. This opens **two independent desktop applications**: Host console and Controller simulator. Click **Start listening** on the controller, then **Connect** on the host. Press **Open**, **Close**, or **Check status** and compare the matching message IDs in both windows.

The controller draws a virtual compartment; it does not operate a motor. The host updates its confirmed state only from a validated response. There is no shared state or direct UI callback between the applications. The small process number in each footer helps distinguish them.

See [the short visual walkthrough](VISUAL-DEMO.md) for the optional second-computer setup and a one-checkbox lost-reply test. The existing automated CLI experiment is still available below.

[TCP explained: simple diagram and message example](TCP-EXPLAINED.md).

## Assumption and boundary

We provisionally assume a future controller accepts newline-delimited messages over a bidirectional byte stream. No controller, display, board, operating system, or firmware protocol has been selected by this experiment.

For this test, the host runs Python and pySerial. A **separate Python process** simulates a controller on localhost. pySerial's `socket://` handler carries the bytes over TCP. **This does not create a virtual COM port or test physical serial communication.** Serial settings such as baud rate have no effect on the socket transport.

```text
host.py -> pySerial socket:// -> localhost TCP -> simulator.py
 request OPEN compartment_1                  -> simulated state OPENED
 response with same request ID               <- simulated acknowledgment
```

The host can also open a native serial port using the same API, but that path has not been tested with a board. The firmware would need to implement the proposed protocol. These assumptions require team review before adoption.

## Run it (Windows)

Prerequisite: Python 3.10 or newer with pip and venv. Open a terminal in this folder, then:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe demo.py
```

Alternatively, double-click **run-demo.cmd**. It creates a local environment, installs the pinned dependency, runs the experiment, and keeps the result visible. The first installation requires internet; after setup the experiment communicates only on localhost.

On macOS/Linux, use `.venv/bin/python` instead of `.venv/Scripts/python.exe` after creating the environment.

Expected: six `PASS` lines, an exit code of zero, and `results/latest.json` containing the environment, expected/observed results, and transmitted/received messages. The command returns a nonzero exit code if any case fails. Generated results are ignored by Git; a dated baseline is in [evidence](evidence/).

## What the demo checks

| Case | Experiment | Passing observation |
| --- | --- | --- |
| Round trip | Send OPEN, then CLOSE | Matching replies report OPENED, then CLOSED |
| Duplicate | Send identical request ID and payload twice | One simulated actuation; cached reply repeated |
| Timeout | Simulator opens, but drops its reply | Host reports uncertainty, sends no retry, and blocks another operation until STATUS succeeds |
| Malformed | Simulator replies with invalid JSON | Host rejects the reply and requires reconciliation |
| Wrong ID | Simulator replies with an unrelated request ID | Host rejects the reply and requires reconciliation |
| Disconnect | Simulator opens, then closes the connection | Host reports failure, reconnects, and queries the simulated state |

The four fault cases deliberately change the simulator's state **before** damaging/dropping the response. This demonstrates why a timeout cannot establish that a command was not executed.

## Try commands yourself

Terminal 1:

```powershell
.venv/Scripts/python.exe simulator.py --port 8765
```

Terminal 2:

```powershell
.venv/Scripts/python.exe host.py --command OPEN
.venv/Scripts/python.exe host.py --command STATUS
.venv/Scripts/python.exe host.py --command CLOSE
```

Use `--compartment compartment_2` to address another illustrative compartment. Stop the simulator with Ctrl+C. It binds only to `127.0.0.1`. Use `--fault timeout`, `malformed`, `wrong-id`, or `disconnect` to fault the first OPEN once per simulator process. `demo.py` automates these scenarios and reconciliation using the same client instance.

## Proposed wire format

UTF-8 JSON, one object per LF-terminated line, maximum **512 bytes including LF**. Protocol version 1. Requests contain exactly:

```json
{"v":1,"id":"demo-open","command":"OPEN","compartment":"compartment_1"}
```

Commands: `OPEN`, `CLOSE`, `STATUS`. Illustrative addresses: `compartment_1` to `compartment_6`; these are not a decision on the physical layout. IDs: 1-64 ASCII letters, digits, underscores or hyphens.

Successful reply echoes all request fields and adds the simulated state and a process-wide count of state-changing actuations:

```json
{"v":1,"id":"demo-open","command":"OPEN","compartment":"compartment_1","state":"OPENED","actuation_count":1}
```

Malformed requests produce `{"v":1,"error":"..."}` and no state change. Oversized input closes the connection. The host treats an error object or any mismatched/invalid response as failure, never as a successful acknowledgment.

Within the simulator process, a cache retains the most recent 256 request IDs and replies. Replaying a retained ID with the same payload repeats its original reply; changing that payload is rejected. A replayed reply describes the original command outcome and can be stale; query STATUS for current state. The cache is lost at restart and IDs can be evicted. It is not a durable or physical exactly-once guarantee.

## Error handling and limits

- A host command is sent once. There is no automatic retry.
- On a timeout, malformed reply, mismatch, or connection failure, the host closes the stream. This avoids reusing a stream with partial or late replies.
- An ambiguous OPEN/CLOSE marks that compartment unresolved **in the current Client instance**. Another operation on it is blocked until reconnection and a valid STATUS reply. A failed STATUS does not clear the flag.
- This process-local flag is lost if the client program exits. The one-command CLI starts a new client each time; it does not provide cross-process protection. Restart recovery, durable transaction tracking, and device reset behavior are outside this experiment.
- Simulated OPENED/CLOSED states are not sensor observations. STATUS reconciliation only queries the simulator's state. Actual hardware would need trustworthy status reporting and separately tested reconciliation behavior.
- The simulator is sequential, supports one client at a time, and starts with all six compartments CLOSED. It is a lab tool with no authentication or encryption; it binds to localhost by default. The visual controller's LAN checkbox (or CLI `--bind 0.0.0.0`) explicitly enables connections from another computer on a trusted local network.
- No compatibility with a specific board, USB driver, electrical serial settings, sensor, pill mechanism, embedded runtime, or deployment platform is established.

## Automated verification

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Tests cover independent-process exchanges and injected faults, split/combined TCP frames, invalid messages, conflicting request IDs, bounded replay history, read-only STATUS, and timeout validation. GitHub Actions runs the same suite and demo on Windows and Linux.

## Moving to a real controller later

Agree a board, transport, message format, timeout, boot/ready behavior, status semantics and error handling with the hardware team first. List native ports with:

```powershell
.venv/Scripts/python.exe -m serial.tools.list_ports
```

Once matching firmware and a board exist, a manual query would look like:

```powershell
.venv/Scripts/python.exe host.py --port COM5 --baudrate 115200 --command STATUS
```

`COM5` and `115200` are examples, not discovered device settings. Native ports may reset a board on open depending on DTR/RTS and the driver; this has not been investigated. The simulator result is a first software feasibility result, not evidence of that future hardware test.

## Team walkthrough (about three minutes)

1. State the uncertainty: our host-side communication environment and message handling have not yet been demonstrated.
2. State the provisional byte-stream assumption and show the two-process diagram.
3. Run `demo.py`; show normal replies and a lost reply with no blind retry.
4. Open `results/latest.json` and inspect an actual message exchange.
5. Conclude only that this software path works in the recorded environment. The next test is a round trip with the team's chosen board and firmware.

## References and AI assistance

- [pySerial URL handlers](https://pyserial.readthedocs.io/en/latest/url_handlers.html): `socket://` uses TCP and ignores serial control/settings.
- [pySerial API](https://pyserial.readthedocs.io/en/latest/pyserial_api.html): native ports, timeouts and `serial_for_url`.
- Code, tests, and documentation in this experiment were generated with OpenAI Codex in collaboration with the project owner. Actual validation results are recorded separately in evidence. Team review remains pending.

Course handouts, private messages, past submissions and submission-ready reports are intentionally kept outside this code repository.
