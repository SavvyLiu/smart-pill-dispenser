# TCP: from button press to controller action

![How our command reaches the controller](docs/tcp-explained.png)

[Slide image (PNG)](docs/tcp-explained.png) | [Editable vector (SVG)](docs/tcp-explained.svg)

**TCP carries a reliable, ordered stream of bytes between two programs. Our application code gives those bytes meaning.**

1. **Create a command.** Pressing Open makes the host build JSON containing the command, compartment and request ID.
2. **Send bytes over the connection.** The destination IP identifies the computer; the port identifies its listening endpoint. Our controller listens on port 8765 by default.
3. **Receive and interpret.** The operating system buffers the arriving bytes in memory. The controller program reads through its socket, waits for a newline, parses the JSON and checks the fields. Its command-handling code then changes the simulated compartment state.
4. **Return the result.** The controller sends an acknowledgment with the same request ID. The host checks that it matches before showing a confirmed result.

The actual OPEN request is a single UTF-8 JSON line followed by a newline:

```json
{"v":1,"id":"abc123","command":"OPEN","compartment":"compartment_1"}
```

An example successful response, also followed by a newline:

```json
{"v":1,"id":"abc123","command":"OPEN","compartment":"compartment_1","state":"OPENED","actuation_count":1}
```

TCP does not understand OPEN or move a motor. It also does not preserve our command boundaries: bytes may arrive in pieces or several commands may arrive together. Our newline marks the end of one application message. An application acknowledgment reports the controller's result; it is different from TCP's own transport acknowledgments.

In the current demo both programs run on the same computer: `127.0.0.1` means this computer. The optional second-computer setup uses the controller computer's LAN address instead. The bytes go to the receiving program's socket buffer, not automatically to a file or the cloud. Our programs choose to display a message history.

**What this demonstrates:** the host can connect to an independent program, exchange the proposed messages, and recognize a matching response. The controller graphic is a software model. Real firmware, motor operation, sensors and board compatibility remain separate integration tests.

For the meeting: point to the command, follow the arrow to the receiver's memory and code, then follow the acknowledgment back. The essential distinction is **TCP delivers bytes; controller code performs the action.**
