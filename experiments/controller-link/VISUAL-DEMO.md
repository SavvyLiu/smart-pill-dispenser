# Visual communication demo

Two small applications demonstrate one question: **can the host establish a connection, send a command, and receive a matching reply?**

See the [UML sequence diagram](TCP-EXPLAINED.md) for the connection and command exchange.

## On one computer

1. Run `run-visual.cmd` on Windows. It handles the Python environment and dependency, then opens two separate applications. Python must include Tkinter (normally provided by the standard Windows Python installer).
2. In **Controller simulator**, click **Start listening**. Leave the LAN checkbox off.
3. In **Host console**, keep address `127.0.0.1` and port `8765`, then click **Connect**. It sends a STATUS query to verify communication.
4. Click **Open**. The controller receives the command, changes its virtual lid, and sends a reply. Only then does the host confirm OPENED.
5. Click **Close** and compare the matching message IDs in each window's history.

The two windows run in different operating-system processes with separate memory. They communicate over TCP through the existing pySerial client; neither window writes the other's state. The two process numbers appear in the footers. The graphic shows compartment 1; the underlying CLI protocol still supports six illustrative addresses.

After setting up the environment, this is also available on macOS/Linux:

```text
python launch_visual.py
```

Use the Python interpreter from your virtual environment. A desktop environment and Tkinter are required. Only Windows visuals have been manually checked; the protocol and server are tested on Windows and Linux.

## Optional: show a lost reply

Close the compartment first. On the controller, tick **Drop the next Open reply**, then click **Open** on the host. The controller opens its virtual lid, but the host times out and displays **Outcome unknown**. Reconnect: the host queries status and confirms the existing OPENED state, without sending another OPEN.

Or stop the controller listener and then click **Check status** on the host to show connection failure. Restart the listener and reconnect. The controller's state survives stopping its listener, but not exiting its application. Host uncertainty is process-local and does not survive exiting the host.

## Optional: on two computers

Put the same repository branch on both computers. Both need Python with Tkinter; the host also needs the pinned pySerial dependency. The Windows launcher installs the dependency for either role for convenience. No virtual serial-port driver or board is needed.

On the computer acting as the controller:

```text
run-visual.cmd --role controller
```

Tick **Allow a host on another computer (LAN)** before clicking **Start listening**. This opts in to listening on local IPv4 interfaces (`0.0.0.0`) rather than localhost. Find this computer's LAN IPv4 address in its network settings.

On the host computer:

```text
run-visual.cmd --role host
```

Enter the controller computer's LAN IPv4 address (not `127.0.0.1` or `0.0.0.0`), use the same port on both, and click **Connect**. Run the same Open/Close exchange. From a prepared Python environment, the role commands are `python launch_visual.py --role controller` and `python launch_visual.py --role host`.

Both computers must be on a network that permits direct connections. Campus/guest Wi-Fi can isolate clients; a shared private hotspot may be simpler. The operating system may require allowing Python on the private network. The application does not change firewall settings. Use a trusted local network: this lab protocol is not authenticated or encrypted, and is not intended for internet exposure.

If connection fails, check that the listener is started, the LAN checkbox is enabled, the address is the controller computer's address, the ports match, and the network allows the connection. The listener handles one host at a time; disconnect the original host before connecting another. Start failures such as an occupied port appear in the controller window.

## What can we conclude?

Reasonable claim: **our chosen host communication tools can connect to an independent endpoint, send the proposed commands, and validate the responses in the tested environment.**

The simulator stands in for controller command handling and motor/lid state. It does not emulate the electronics, processor architecture, firmware timing, motor dynamics, mechanics, or sensors of the final device. Its graphics show instantaneous model state changes, not a measured motion profile.

Using a second computer establishes a real network exchange between computers if the team runs it; it still does not establish compatibility with the eventual embedded device. A later test must repeat the exchange with the selected board, transport and firmware. LAN support has been tested locally by enabling the network listener and connecting over loopback; a physical second computer was not available during implementation.

That boundary is appropriate for this small feasibility experiment. A full dispenser application is outside its scope.
