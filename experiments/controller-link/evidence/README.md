# Recorded feasibility result

Date: October 28, 2026 (America/Toronto).

Tested source commit: `2a52e79b5bd32f264e77e0e4319cd38c47cee142`, with a clean working tree before the run. Subsequent documentation, evidence and CI updates do not change the tested Python source.

Starting configuration: Windows, Python 3.12.4, pySerial 3.5 installed into a fresh virtual environment from requirements.txt. The host connected via pySerial's localhost TCP handler to a separate Python simulator process. Each scenario used a fresh simulator; fault cases retained that simulator across reconnects.

Commands:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe demo.py --output results/baseline.json
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Observed result: dependency installed successfully; all six demo scenarios passed; all ten automated tests passed (the integration test runs all six demo scenarios as subtests). See [raw demo evidence](2026-10-28-windows.json) for the environment, exact timestamp, expected/observed results and messages; see [test output](2026-10-28-windows-tests.txt).

Conclusion: this host-side library and proposed message handling run successfully on the tested computer using the simulated byte stream. Deliberate lost, malformed, mismatched and disconnected responses were recognized; the client did not automatically resend an uncertain operation. The simulator's same-process replay cache returned an earlier response without another simulated actuation.

Limits: no board, native serial/USB connection, physical sensor or mechanism was tested. No firmware protocol has been agreed. Replay history and unresolved-operation tracking are in memory; durable recovery and real-device behavior remain untested. These observations do not establish medication dispensing safety or exactly-once physical actuation.

Disposition: retain as a proposed software feasibility experiment for team review; no team approval or adoption is implied. Preparation and execution were assisted by OpenAI Codex. Cross-platform results, when available, are recorded separately in GitHub Actions.
