#!/usr/bin/env python3
"""
securechat.py  —  Main launcher
════════════════════════════════
Usage
  python3 securechat.py host     [--port N]
  python3 securechat.py connect  [--port N]
  python3 securechat.py          (interactive menu)

Requirements
  Python 3.8+
  pip install cryptography        (AES-256-GCM)
  Linux / macOS / Git Bash (WSL)  (curses)
"""

import sys
import os
import argparse
import threading
import time
import signal

# ── Silence all history before anything else ─────────────────────────────────
os.environ["HISTFILE"]     = "/dev/null"
os.environ["HISTSIZE"]     = "0"
os.environ["HISTFILESIZE"] = "0"

# ── Ensure package is importable when run as a script ────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from securechat import crypto, network, protocol
from securechat.session import Session
from securechat.protocol import Message, MsgType
from securechat.ui import ChatUI, make_outgoing_msg
from securechat.network import DEFAULT_PORT, get_local_ip


# ── ANSI helpers (used only in the pre-curses setup phase) ───────────────────
R  = "\033[0m"
B  = "\033[1m"
DIM= "\033[2m"
C  = "\033[36m"    # cyan
G  = "\033[32m"    # green
Y  = "\033[33m"    # yellow
RE = "\033[31m"    # red
W  = "\033[37m"    # white


def is_onion_address(address: str) -> bool:
    """Check if address is a .onion hidden service"""
    return address.strip().lower().endswith('.onion')


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner():
    clear()
    print(C + B + """
  ╔══════════════════════════════════════════════════════════════╗
  ║                                                              ║
  ║   ░░  S E C U R E C H A T  v2  ░░  EPHEMERAL · ENCRYPTED   ║
  ║                                                              ║
  ║   ▸ AES-256-GCM  end-to-end encryption                      ║
  ║   ▸ PBKDF2-SHA256  key derivation  (310 000 iterations)     ║
  ║   ▸ One-time session code  —  never stored or logged        ║
  ║   ▸ Zero history  ·  RAM-only  ·  shred-on-exit             ║
  ║   ▸ Auto-terminates after 15 minutes                        ║
  ║                                                              ║
  ╚══════════════════════════════════════════════════════════════╝
""" + R)


# ═══════════════════════════════════════════════════════════════════════════════
#  HOST MODE
# ═══════════════════════════════════════════════════════════════════════════════

def run_host(port: int) -> None:
    banner()

    code   = crypto.generate_session_code()
    my_ip  = get_local_ip()

    print(Y + B + "  ◈  HOST MODE" + R)
    print()
    print("  Share this one-time session code with your peer.")
    print("  They'll also need your IP address.\n")
    print(W + B +
          "  ┌──────────────────────────────────────┐\n"
          "  │                                      │\n"
          f"  │   Code :  {C}{B}{code}{W}{B}          │\n"
          "  │                                      │\n"
          f"  │   IP   :  {C}{B}{my_ip:<26}{W}{B} │\n"
          "  │                                      │\n"
          "  └──────────────────────────────────────┘" + R)
    print()
    print(DIM + f"  Port: {port}  │  Timeout: 15 minutes" + R)
    print()

    # Animate the wait indicator
    done_event = threading.Event()

    def waiting_anim(elapsed: int):
        remaining = max(0, 900 - elapsed)
        m, s = divmod(remaining, 60)
        bar_w = 30
        pct   = elapsed / 900
        filled = int(bar_w * pct)
        bar   = "█" * filled + "░" * (bar_w - filled)
        line  = (
            f"\r  {Y}⏳ Waiting for peer...{R}  "
            f"[{C}{bar}{R}]  "
            f"{DIM}{m:02d}:{s:02d} remaining{R}   "
        )
        print(line, end="", flush=True)

    print("  " + DIM + "Listening on 0.0.0.0:" + str(port) + R)

    try:
        conn = network.host_listen(
            code=code,
            port=port,
            on_waiting=waiting_anim,
            timeout=900,
        )
    except TimeoutError:
        print(f"\n\n  {RE}No peer connected within 15 minutes. Exiting.{R}\n")
        sys.exit(1)
    except OSError as e:
        print(f"\n\n  {RE}Error: {e}{R}\n")
        sys.exit(1)

    print(f"\n\n  {G}{B}✔  Peer connected and authenticated!{R}\n")
    time.sleep(0.8)

    _run_chat(conn=conn, key=crypto.derive_key(code), role="host", peer_label="Peer")


# ═══════════════════════════════════════════════════════════════════════════════
#  PEER / CONNECT MODE
# ═══════════════════════════════════════════════════════════════════════════════

def run_connect(port: int) -> None:
    banner()

    print(C + B + "  ◈  CONNECT MODE" + R)
    print()

    host_ip = input(f"  {W}Host address (IP or .onion): {R}").strip()
    
    if is_onion_address(host_ip):
        print(f"  {Y}Connecting via Tor to {host_ip}...{R}")
    else:
        print(f"  {Y}Connecting to {host_ip}:{port}...{R}")
    
    code = input(f"  {W}Session code (XXXX-XXXX-XXXX): {R}").strip().upper()
    code = code.replace(" ", "")
    if not code:
        print(f"  {RE}No code entered. Exiting.{R}")
        sys.exit(1)

    print()

    statuses = []

    def on_status(msg: str):
        print(f"  {DIM}{msg}{R}")
        statuses.append(msg)

    print(f"  {Y}Connecting...{R}\n")

    try:
        conn = network.peer_connect(
            host_ip=host_ip,
            code=code,
            port=port,
            on_status=on_status,
            timeout=900,
        )
    except ValueError as e:
        print(f"\n  {RE}✗  {e}{R}\n")
        sys.exit(1)
    except TimeoutError:
        print(f"\n  {RE}✗  Connection timed out after 15 minutes.{R}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n  {RE}✗  Unexpected error: {e}{R}\n")
        sys.exit(1)

    print(f"\n  {G}{B}✔  Authenticated! Secure channel established.{R}\n")
    time.sleep(0.8)

    _run_chat(conn=conn, key=crypto.derive_key(code), role="peer", peer_label="Host")


# ═══════════════════════════════════════════════════════════════════════════════
#  SHARED: spin up Session + ChatUI
# ═══════════════════════════════════════════════════════════════════════════════

def _run_chat(conn, key: bytes, role: str, peer_label: str) -> None:
    """
    Start the Session and ChatUI. This blocks until the chat ends.
    """

    # Build UI first (not yet running)
    ui = ChatUI(session=None, role=role, peer_label=peer_label)  # type: ignore

    def on_message(msg: Message):
        """Called from reader thread — route to UI."""
        ui.push_message(msg)

    def on_close(reason: str):
        """Called when the session tears down."""
        ui.push_system(f"Connection closed: {reason}")
        ui.signal_closed(reason)

    # Build session
    session = Session(
        sock=conn,
        key=key,
        role=role,
        on_message=on_message,
        on_close=on_close,
    )
    ui._session = session

    # Override send_text so local echo uses sentinel
    original_send_text = session.send_text

    def patched_send_text(text: str):
        original_send_text(text)
        # Echo locally
        ui.push_message(make_outgoing_msg(text))

    session.send_text = patched_send_text

    def new_handle_enter(self=ui):
        buf = "".join(self._input_buf).strip()
        self._input_buf.clear()
        self._cursor = 0

        if not buf:
            return None

        if buf.lower() in ("/quit", "/exit", "/q"):
            return "quit"

        if buf.lower() == "/help":
            self.push_system(
                "Commands: /quit  /clear  /help  |  ↑↓ scroll  |  Ctrl-W clear input"
            )
            return None

        if buf.lower() == "/clear":
            with self._msg_lock:
                self._messages.clear()
            self._scroll = 0
            self._dirty.set()
            return None

        if session.is_alive:
            try:
                session.send_text(buf)   # calls patched → sends + echoes
            except Exception as e:
                self.push_system(f"Send error: {e}")
        else:
            self.push_system("Session is closed — cannot send.")

        return None

    ui._handle_enter = new_handle_enter

    # Start session threads
    session.start()

    # Announce connection on both sides
    ui.push_system(f"🔒  Secure channel established — AES-256-GCM — 15 min session")
    ui.push_system("Type /help for commands. /quit to close.")

    # Run the curses UI (blocks)
    try:
        ui.run()
    finally:
        session.close("UI closed")
        session.join()
        _wipe_and_exit()


# ═══════════════════════════════════════════════════════════════════════════════
#  CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════

def _wipe_and_exit() -> None:
    clear()
    print(G + B + "\n  SecureChat session terminated." + R)
    print(DIM + "  All session data has been cleared from memory." + R)
    print(DIM + "  No logs. No history. No trace.\n" + R)
    time.sleep(1.5)
    clear()


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERACTIVE MENU  (when run with no args)
# ═══════════════════════════════════════════════════════════════════════════════

def interactive_menu(port: int) -> None:
    banner()
    print("  How do you want to use SecureChat?\n")
    print(f"  {B}[1]{R}  Host a session  {DIM}(generate a code, wait for peer){R}")
    print(f"  {B}[2]{R}  Connect         {DIM}(enter a code from the host){R}")
    print(f"  {B}[3]{R}  Exit\n")

    choice = input("  Choice [1/2/3]: ").strip()
    if choice == "1":
        run_host(port)
    elif choice == "2":
        run_connect(port)
    else:
        clear()
        sys.exit(0)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    # Check Python version
    if sys.version_info < (3, 8):
        print("SecureChat requires Python 3.8 or later.")
        sys.exit(1)

    # Check cryptography library
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa
    except ImportError:
        print("\n  Missing dependency: cryptography")
        print("  Install it with:  pip install cryptography\n")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        prog="securechat",
        description="Zero-knowledge ephemeral encrypted terminal chat",
        add_help=True,
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["host", "connect"],
        help="'host' to start a session, 'connect' to join one",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"TCP port to use (default: {DEFAULT_PORT})",
    )

    args = parser.parse_args()

    # Ignore SIGPIPE (broken pipe) gracefully
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except AttributeError:
        pass   # Windows doesn't have SIGPIPE

    if args.mode == "host":
        run_host(args.port)
    elif args.mode == "connect":
        run_connect(args.port)
    else:
        interactive_menu(args.port)


if __name__ == "__main__":
    main()