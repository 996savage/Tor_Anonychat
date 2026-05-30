# SecureChat v2
### Zero-Knowledge · Ephemeral · Encrypted Terminal Chat

```
  ╔══════════════════════════════════════════════════════════════╗
  ║   ░░  S E C U R E C H A T  v2  ░░  EPHEMERAL · ENCRYPTED   ║
  ║                                                              ║
  ║   ▸ AES-256-GCM  end-to-end encryption                      ║
  ║   ▸ PBKDF2-SHA256  key derivation  (310 000 iterations)     ║
  ║   ▸ One-time session code — never stored or logged          ║
  ║   ▸ Zero history · RAM-only · shred-on-exit                 ║
  ║   ▸ Auto-terminates after 15 minutes                        ║
  ╚══════════════════════════════════════════════════════════════╝
```

---

## What is it?

SecureChat is a peer-to-peer encrypted terminal chat application with **no server, no accounts, no logs, and no persistent data**. Two people connect directly using a one-time session code. When the session ends — or times out — every trace is wiped from memory.

---

## Requirements

| Requirement | Details |
|---|---|
| **OS** | Linux (Kali, Ubuntu, Debian), macOS, Git Bash / WSL on Windows |
| **Python** | 3.8 or newer (`python3 --version`) |
| **Library** | `cryptography` — auto-installed by `run.sh` |
| **Network** | Both machines must be able to reach each other over TCP (same LAN, or VPN, or port-forwarded) |

---

## Installation

```bash
# 1. Clone or download and unzip
git clone https://github.com/you/securechat   # or unzip securechat.zip
cd securechat

# 2. Make the launcher executable
chmod +x run.sh

# 3. (Optional) Install the Python dependency manually
pip install cryptography
```

That's it. No build step. No compilation.

---

## Usage

### Quick start (interactive menu)

```bash
bash run.sh
```

You'll see a menu:
```
  [1]  Host a session  (generate a code, wait for peer)
  [2]  Connect         (enter a code from the host)
  [3]  Exit
```

---

### Host a session

```bash
bash run.sh host
```

SecureChat will:
1. Generate a random one-time code like `R7KP-Q2MN-A5VX`
2. Display your LAN IP address
3. Wait for the peer to connect (up to 15 minutes)

Share **both the code and your IP** with the other person over any channel (phone call, Signal, etc.).

---

### Connect to a session

```bash
bash run.sh connect
```

SecureChat will prompt for:
1. The host's IP address
2. The session code

---

### Command-line options

```bash
bash run.sh host    --port 9999      # use a custom port (default: 57311)
bash run.sh connect --port 9999
```

---

## In-chat commands

| Command | Action |
|---|---|
| `/quit` or `/exit` | Close the session and wipe data |
| `/clear` | Clear the message history from the screen |
| `/help` | Show the command list |
| `↑` / `↓` | Scroll through message history |
| `Ctrl-W` | Clear the current input line |
| `Ctrl-C` | Force quit |

---

## Security Architecture

### End-to-end encryption

Every byte that travels between the two machines is encrypted. Nothing is ever sent in plaintext — not even the handshake.

```
Session code (human-readable)
         │
         ▼  PBKDF2-HMAC-SHA256 (310 000 iterations)
       AES-256 key (32 bytes, in RAM only)
         │
         ▼  per-message random nonce (12 bytes)
       AES-256-GCM ciphertext + 16-byte authentication tag
         │
         ▼  2-byte length header
       TCP socket
```

### Key properties

| Property | Value |
|---|---|
| Cipher | AES-256-GCM (authenticated encryption) |
| Key derivation | PBKDF2-HMAC-SHA256 |
| KDF iterations | 310 000 (OWASP 2023 minimum) |
| Nonce | 12 bytes, cryptographically random, per-message |
| Auth tag | 16 bytes (GCM) — any tampering is detected |
| Code entropy | ~46 bits (sufficient for a 15-min window) |

### One-time session code

The code is:
- Generated fresh for every session using `secrets.choice()` (CSPRNG)
- Never written to disk, environment, or any log file
- Used only to derive the AES key via PBKDF2 — the raw code is not transmitted
- After the session ends, it has no value (replay is impossible — no server to replay to)

### No server

The two machines connect **directly** over TCP. There is no relay server, no intermediary, no metadata logged anywhere. An attacker tapping the wire sees only AES-256-GCM ciphertext with random-looking nonces.

### Zero persistence

- Temp files (if any) go to `/dev/shm` (Linux RAM filesystem) — never written to a disk block
- Shell history is disabled (`HISTFILE=/dev/null`) before the process starts
- On exit: all Python objects go out of scope; RAM is zeroed by the OS on process death
- The terminal screen is cleared after the session ends

### What SecureChat does NOT provide

- **Forward secrecy**: The session key is derived from the code for the entire session. A compromise of the code retroactively breaks the session. For true forward secrecy, a Diffie-Hellman key exchange (e.g. X25519) would be added — a planned v3 feature.
- **Anonymity**: Your IP address is shared with the peer (you gave it to them). It is also visible to your ISP and anyone monitoring your network.
- **Multi-party**: Exactly two people per session.
- **File transfer**: Text only in v2.

---

## Network setup

### Same LAN

Works out of the box. Use the IP shown by `run.sh host` (typically `192.168.x.x`).

### Over the internet

The host needs to be reachable from the peer. Options:
1. **Port forwarding** on your router: forward TCP port 57311 (or your chosen port) to your machine.
2. **Tailscale / WireGuard VPN**: gives both machines private IPs that can reach each other.
3. **SSH tunnel**: `ssh -L 57311:localhost:57311 user@host` — then the peer connects to `127.0.0.1`.

### Firewall

Allow the chosen TCP port inbound on the host machine:

```bash
# UFW (Ubuntu)
sudo ufw allow 57311/tcp

# iptables
sudo iptables -A INPUT -p tcp --dport 57311 -j ACCEPT

# Kali (usually no firewall by default)
```

---

## File layout

```
securechat/
├── run.sh                  ← Start here. Bash launcher.
├── README.md               ← This file.
└── securechat/
    ├── __init__.py
    ├── securechat.py       ← Main entry point + pre-connection UI
    ├── crypto.py           ← AES-256-GCM, PBKDF2, wire framing
    ├── protocol.py         ← Message types, serialisation, handshake
    ├── session.py          ← Live session (threads, keepalive, timeout)
    ├── network.py          ← TCP host/connect logic
    └── ui.py               ← Curses terminal chat interface
```

---

## Troubleshooting

**`Address already in use`**
The port is taken. Use a different one: `bash run.sh host --port 9999`

**`Handshake failed`**
The codes don't match, or the connection was intercepted. Verify you entered the exact code (case-insensitive, hyphens optional).

**`Connection refused`**
The host isn't listening yet, or a firewall is blocking the port. Try again after the host is running.

**Curses display glitches**
Resize the terminal to at least 80×24. On Windows Git Bash, ensure your terminal emulator supports ANSI colours.

**`pip install cryptography` fails**
```bash
# Debian/Ubuntu with PEP 668
pip install cryptography --break-system-packages

# Or with a virtual environment
python3 -m venv venv && source venv/bin/activate && pip install cryptography
```

---

## Planned v3 features

- X25519 Diffie-Hellman key exchange (true forward secrecy)
- Tor hidden service mode (IP anonymity)
- Encrypted file transfer
- QR code for session code sharing
- Multi-OS installer script

---

*SecureChat is provided for educational and personal privacy purposes. You are responsible for complying with local laws regarding encryption.*
