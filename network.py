"""
securechat/network.py
─────────────────────
TCP socket management for host (listener) and peer (connector).

  Host   : binds to 0.0.0.0:PORT, waits for exactly one connection,
           performs the encrypted handshake, returns the socket.

  Peer   : connects to HOST:PORT, performs the encrypted handshake,
           returns the socket.

Both sides derive the AES-256 key from the session code before
the handshake, so the very first byte exchanged is already encrypted.
No plaintext ever travels the wire.
"""

import socket
import time
import sys

from . import crypto
from . import protocol


DEFAULT_PORT  = 57311     # Unlikely to be in use; well above 1024
CONNECT_RETRY = 3         # seconds between connection retries
BACKLOG       = 1         # only one peer allowed


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_local_ip() -> str:
    """Best-effort: get the LAN IP of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ── Host ─────────────────────────────────────────────────────────────────────

def host_listen(
    code: str,
    port: int = DEFAULT_PORT,
    on_waiting: callable = None,
    timeout: int = 900,
) -> socket.socket:
    """
    Bind and listen for exactly one incoming connection.
    Performs the encrypted handshake.
    Returns the authenticated socket, or raises on failure/timeout.

    Parameters
    ----------
    code       : session code (used to derive the AES key)
    port       : TCP port to bind
    on_waiting : optional callback(seconds_elapsed) called every second while waiting
    timeout    : seconds before giving up
    """
    key = crypto.derive_key(code)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(("0.0.0.0", port))
    except OSError as e:
        raise OSError(
            f"Cannot bind to port {port}: {e}\n"
            f"Try a different port with --port, or free the port."
        ) from e

    srv.listen(BACKLOG)
    srv.settimeout(1.0)    # 1-second accept timeout so we can count elapsed time

    start   = time.monotonic()
    elapsed = 0

    try:
        while True:
            elapsed = int(time.monotonic() - start)
            if elapsed >= timeout:
                raise TimeoutError("No peer connected within the timeout window")

            if on_waiting:
                on_waiting(elapsed)

            try:
                conn, addr = srv.accept()
            except socket.timeout:
                continue

            # Got a connection — authenticate
            conn.settimeout(15)
            ok = protocol.perform_handshake_host(conn, key)
            if not ok:
                conn.close()
                # Keep listening — could be a probe or wrong code attempt
                continue

            # Handshake passed
            conn.settimeout(None)   # session module sets its own timeout
            return conn

    finally:
        srv.close()


# ── Peer ─────────────────────────────────────────────────────────────────────

def peer_connect(
    host_ip: str,
    code: str,
    port: int = DEFAULT_PORT,
    on_status: callable = None,
    timeout: int = 900,
) -> socket.socket:
    """
    Connect to the host and perform the encrypted handshake.
    Returns the authenticated socket, or raises on failure/timeout.

    Parameters
    ----------
    host_ip   : IP address of the host
    code      : session code (must match host's code)
    port      : TCP port of the host
    on_status : optional callback(message: str) for status updates
    timeout   : seconds before giving up
    """
    key   = crypto.derive_key(code)
    start = time.monotonic()

    def _status(msg):
        if on_status:
            on_status(msg)

    while True:
        elapsed = time.monotonic() - start
        if elapsed >= timeout:
            raise TimeoutError("Could not connect within the timeout window")

        _status(f"Connecting to {host_ip}:{port}...")

        try:
            conn = socket.create_connection((host_ip, port), timeout=10)
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            _status(f"Not reachable yet ({e}) — retrying in {CONNECT_RETRY}s...")
            time.sleep(CONNECT_RETRY)
            continue

        _status("TCP connected — authenticating session code...")

        conn.settimeout(15)
        ok = protocol.perform_handshake_peer(conn, key)
        if not ok:
            conn.close()
            raise ValueError(
                "Handshake failed — wrong session code, or host rejected the connection."
            )

        conn.settimeout(None)
        _status("Authenticated!")
        return conn
