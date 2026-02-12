# Complete FTP Implementation Guide

## Overview

This document provides a comprehensive explanation of the FTP (File Transfer Protocol) concepts and implementation in this project.

## Table of Contents

1. [FTP Protocol Basics](#ftp-protocol-basics)
2. [Control vs Data Connections](#control-vs-data-connections)
3. [Passive Mode (PASV/EPSV)](#passive-mode-pasvepsv)
4. [Transfer Types](#transfer-types)
5. [Command Categories](#command-categories)
6. [Response Codes](#response-codes)
7. [Implementation Architecture](#implementation-architecture)

---

## FTP Protocol Basics

### What is FTP?

FTP (File Transfer Protocol) is a standard network protocol used for transferring files between a client and server over a TCP/IP network. It was created in 1971 and is one of the oldest protocols still in use today.

### Key Characteristics

- **Port**: Default is 21 for control connection
- **Protocol**: TCP-based (reliable, ordered delivery)
- **Text-based**: Commands and responses are human-readable
- **Stateful**: Server maintains session state (login, current directory, etc.)
- **Two connections**: Separate control and data channels

### FTP vs HTTP

| Feature | FTP | HTTP |
|---------|-----|------|
| Purpose | File transfer | Web content |
| Connections | 2 (control + data) | 1 |
| Commands | Explicit (LIST, RETR, STOR) | Methods (GET, POST) |
| State | Stateful | Stateless |
| Current directory | Yes | No |
| Authentication | Built-in (USER/PASS) | Optional (Basic/Digest) |

---

## Control vs Data Connections

### The Two-Connection Architecture

FTP uniquely uses **two separate TCP connections**:

#### 1. Control Connection (Command Channel)

- **Purpose**: Send commands and receive responses
- **Port**: 21 (default)
- **Lifetime**: Stays open for entire session
- **Content**: Text commands (USER, PASS, LIST, etc.)

```
CLIENT                    SERVER
  |------------------------->|  USER alice
  |<-------------------------|  331 Need password
  |------------------------->|  PASS secret
  |<-------------------------|  230 Login successful
  |------------------------->|  PWD
  |<-------------------------|  257 "/" is current directory
```

#### 2. Data Connection (Data Channel)

- **Purpose**: Transfer actual file data or directory listings
- **Port**: Varies (negotiated via PASV/PORT)
- **Lifetime**: Opened per transfer, then closed
- **Content**: Binary file data or directory listings

```
CLIENT                    SERVER
  |------------------------->|  LIST
  |                          |  (Opens data connection)
  |<=========DATA============|  (Directory listing)
  |                          |  (Closes data connection)
  |<-------------------------|  226 Transfer complete
```

### Why Two Connections?

1. **Separation of concerns**: Commands don't interfere with data
2. **Parallel operations**: Can send commands while data transfers
3. **Security**: Different firewall rules for control vs data
4. **Legacy reasons**: Historical design from 1971

---

## Passive Mode (PASV/EPSV)

### The Problem: Active vs Passive Mode

**Active Mode (PORT)** - Client's nightmare:
```
1. Client tells server: "Connect to MY port X"
2. Server initiates connection to client
3. ❌ Blocked by client firewall (incoming connection)
```

**Passive Mode (PASV)** - Solution:
```
1. Client asks: "Where should I connect?"
2. Server says: "Connect to MY port Y"
3. Client initiates connection to server
4. ✅ Works through firewalls (outgoing connection)
```

### PASV Command Flow

```
CLIENT                          SERVER
  |------- PASV --------------->|
  |                             |  (Server creates listener on port 5001)
  |<------ 227 (h,h,h,h,p,p) ---|
  |                             |
  |===== CONNECT TO 5001 ======>|  (Data connection established)
  |------- LIST --------------->|
  |<===== DIRECTORY DATA =======|
  |<------ 226 Complete ---------|
```

### PASV Response Format

Response: `227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)`

**Decoding:**
- **h1,h2,h3,h4**: IP address octets
  - Example: `192,168,1,100` → `192.168.1.100`
- **p1,p2**: Port calculation
  - Formula: `port = p1 * 256 + p2`
  - Example: `19,136` → `19 * 256 + 136 = 5000`

### EPSV (Extended Passive Mode)

Simpler format introduced in 1998 (RFC 2428):

Response: `229 Entering Extended Passive Mode (|||port|)`

**Advantages:**
- Simpler parsing (just the port number)
- No IP address needed (use same as control connection)
- IPv6 compatible

**Example:**
```
SERVER: 229 Entering Extended Passive Mode (|||5001|)
CLIENT: (Connects to same IP as control connection, port 5001)
```

---

## Transfer Types

FTP supports two transfer modes:

### ASCII Mode (TYPE A)

- **Use**: Text files
- **Behavior**: Converts line endings
  - Windows: `\r\n` (CRLF)
  - Unix/Linux: `\n` (LF)
  - Mac (old): `\r` (CR)
- **Command**: `TYPE A`

**When to use:**
- `.txt` files
- `.csv` files
- `.html`, `.xml` files
- Any human-readable text

### Binary Mode (TYPE I)

- **Use**: Everything else
- **Behavior**: Byte-for-byte transfer (no conversion)
- **Command**: `TYPE I`

**When to use:**
- Images (`.jpg`, `.png`)
- Videos (`.mp4`, `.avi`)
- Archives (`.zip`, `.tar`)
- Executables (`.exe`, `.bin`)
- **Default choice when unsure**

### Why Binary is Safer

ASCII mode line-ending conversion can corrupt binary files:
```
Binary file: [0A 1B 2C]  (0A happens to be LF)
After ASCII: [0D 0A 1B 2C]  (Corrupted! Added CR)
```

---

## Command Categories

### 1. Access Control

| Command | Purpose | Example |
|---------|---------|---------|
| `USER` | Send username | `USER alice` |
| `PASS` | Send password | `PASS secret123` |
| `ACCT` | Account info (rare) | `ACCT billing` |
| `REIN` | Reinitialize session | `REIN` |
| `QUIT` | Logout | `QUIT` |

### 2. Transfer Parameters

| Command | Purpose | Example |
|---------|---------|---------|
| `PASV` | Enter passive mode | `PASV` |
| `EPSV` | Extended passive mode | `EPSV` |
| `TYPE` | Set transfer type | `TYPE I` |
| `MODE` | Set transfer mode | `MODE S` |
| `STRU` | Set file structure | `STRU F` |

### 3. File Operations

| Command | Purpose | Example |
|---------|---------|---------|
| `RETR` | Download file | `RETR file.txt` |
| `STOR` | Upload file | `STOR newfile.txt` |
| `DELE` | Delete file | `DELE oldfile.txt` |
| `RNFR/RNTO` | Rename file | `RNFR old.txt` → `RNTO new.txt` |
| `SIZE` | Get file size | `SIZE file.txt` |
| `MDTM` | Get modification time | `MDTM file.txt` |

### 4. Directory Operations

| Command | Purpose | Example |
|---------|---------|---------|
| `PWD` | Print working directory | `PWD` |
| `CWD` | Change directory | `CWD /pub` |
| `CDUP` | Go to parent directory | `CDUP` |
| `MKD` | Make directory | `MKD newfolder` |
| `RMD` | Remove directory | `RMD oldfolder` |
| `LIST` | List directory | `LIST` or `LIST /pub` |
| `NLST` | Name list (simpler) | `NLST` |

### 5. Informational

| Command | Purpose | Example |
|---------|---------|---------|
| `SYST` | Get system type | `SYST` |
| `STAT` | Get status | `STAT` |
| `HELP` | Get help | `HELP LIST` |
| `NOOP` | Keep alive | `NOOP` |

---

## Response Codes

### Code Structure

Format: `XYZ Message`
- **X**: Category (1-5)
- **Y**: Subcategory
- **Z**: Specific meaning

### Categories (First Digit)

| Code | Meaning | Example |
|------|---------|---------|
| **1xx** | Positive Preliminary | `150 Opening data connection` |
| **2xx** | Positive Completion | `226 Transfer complete` |
| **3xx** | Positive Intermediate | `331 Need password` |
| **4xx** | Transient Negative | `421 Service not available` |
| **5xx** | Permanent Negative | `550 File not found` |

### Common Response Codes

| Code | Meaning | When It Appears |
|------|---------|-----------------|
| `220` | Service ready | Server welcome message |
| `221` | Goodbye | Response to QUIT |
| `226` | Transfer complete | After LIST/RETR/STOR |
| `227` | Passive mode | Response to PASV |
| `229` | Extended passive | Response to EPSV |
| `230` | Login successful | After USER/PASS |
| `250` | File action okay | After DELE, RMD, etc. |
| `257` | Path created | After MKD, or PWD response |
| `331` | Need password | After USER |
| `350` | Pending further info | After RNFR (before RNTO) |
| `421` | Service unavailable | Server shutting down |
| `425` | Can't open data connection | Passive mode failed |
| `426` | Connection closed | Transfer aborted |
| `450` | File unavailable | File busy/locked |
| `500` | Syntax error | Unknown command |
| `501` | Invalid arguments | Missing required argument |
| `502` | Command not implemented | Unsupported command |
| `503` | Bad command sequence | RNTO without RNFR |
| `530` | Not logged in | Command requires authentication |
| `550` | Action not taken | File not found, permission denied |
| `553` | Filename not allowed | Invalid filename |

### Multi-line Responses

Some servers send multi-line responses:

```
SERVER: 211-Status of server:
        Connected to ftp.example.com
        Logged in as anonymous
        TYPE: ASCII
        211 End of status
```

Format:
- First line: `XXX-Message`
- Middle lines: Anything
- Last line: `XXX Message` (same code, space instead of dash)

---

## Implementation Architecture

### Client Architecture

```
┌─────────────────────────────────────────┐
│          FTPClient (ftp_core.py)        │
│  - login(), quit(), list_files()       │
│  - download_file(), upload_file()      │
│  - pwd(), cwd(), cdup()                │
│  - delete_file(), make_directory()     │
│  - rename(), get_file_size()           │
└────────────────┬────────────────────────┘
                 │
                 │ uses
                 ▼
┌─────────────────────────────────────────┐
│     FTPConnection (connection.py)       │
│  - connect(), send_command()           │
│  - _read_response(), close()           │
│  (Handles raw socket communication)    │
└─────────────────────────────────────────┘
```

**Separation of Concerns:**
- `FTPConnection`: Raw TCP socket (protocol-agnostic)
- `FTPClient`: FTP protocol logic (knows about commands, codes)

### Server Architecture

```
┌─────────────────────────────────────────┐
│       FTPServer (server_core.py)        │
│  - start(), handle_client()            │
│  - handle_pasv(), handle_list()        │
│  - handle_retr(), handle_stor()        │
│  - handle_dele(), handle_mkd()         │
└────────┬────────────────────────────────┘
         │
         │ uses
         ▼
┌─────────────────────────────────────────┐
│      FTPSession (session.py)            │
│  - Authentication state                │
│  - Current directory tracking          │
│  - Path security (prevent traversal)   │
└────────┬────────────────────────────────┘
         │
         ├───> PassiveModeManager (data_connection.py)
         │     - setup_passive_mode()
         │     - accept_data_connection()
         │     - send_data(), receive_data()
         │
         └───> FileSystemHelper (file_system.py)
               - list_directory()
               - read_file(), write_file()
               - delete_file(), make_directory()
```

### Key Design Patterns

#### 1. Session Management
```python
class FTPSession:
    def __init__(self, client_socket, root_dir):
        self.is_authenticated = False
        self.current_dir = "/"
        self.username = None
        # ... per-client state
```

#### 2. Path Security (Sandbox)
```python
def get_real_path(self, ftp_path):
    # Convert /pub/file.txt to /var/ftp/pub/file.txt
    real_path = os.path.join(self.root_dir, ftp_path.lstrip("/"))
    
    # Security: Ensure path stays inside root_dir
    if not real_path.startswith(self.root_dir):
        raise PermissionError("Path traversal detected")
    
    return real_path
```

**Prevents attacks like:**
```
CWD ../../../../etc
RETR passwd
```

#### 3. Passive Mode State Machine
```python
# State 1: Client sends PASV
server.handle_pasv()  # Creates listener

# State 2: Server tells client where to connect
# Response: 227 Entering Passive Mode (...)

# State 3: Client connects to data port

# State 4: Client sends command requiring data
server.handle_list()  # Uses passive connection

# State 5: Server sends data, closes connection
```

---

## Complete FTP Session Example

### Client-Server Dialogue

```
# Connection
CLIENT: (TCP connect to server:21)
SERVER: 220 Welcome to FTP Server

# Authentication
CLIENT: USER alice
SERVER: 331 Password required
CLIENT: PASS secret123
SERVER: 230 Login successful

# Get system type
CLIENT: SYST
SERVER: 215 UNIX Type: L8

# Check current directory
CLIENT: PWD
SERVER: 257 "/" is current directory

# Set binary mode
CLIENT: TYPE I
SERVER: 200 Type set to I

# List files (requires data connection)
CLIENT: PASV
SERVER: 227 Entering Passive Mode (127,0,0,1,19,137)
CLIENT: (Opens connection to 127.0.0.1:5001)
CLIENT: LIST
SERVER: 150 Opening data connection
SERVER: (Sends directory listing via port 5001)
SERVER: (Closes port 5001)
SERVER: 226 Transfer complete

# Download file
CLIENT: PASV
SERVER: 227 Entering Passive Mode (127,0,0,1,19,138)
CLIENT: (Opens connection to 127.0.0.1:5002)
CLIENT: RETR sample.txt
SERVER: 150 Opening data connection (1234 bytes)
SERVER: (Sends file data via port 5002)
SERVER: (Closes port 5002)
SERVER: 226 Transfer complete

# Upload file
CLIENT: PASV
SERVER: 227 Entering Passive Mode (127,0,0,1,19,139)
CLIENT: (Opens connection to 127.0.0.1:5003)
CLIENT: STOR newfile.txt
SERVER: 150 Ready to receive
CLIENT: (Sends file data via port 5003)
CLIENT: (Closes connection)
SERVER: 226 Transfer complete (5678 bytes received)

# Create directory
CLIENT: MKD uploads
SERVER: 257 "uploads" directory created

# Change directory
CLIENT: CWD uploads
SERVER: 250 Directory changed successfully

# Rename file
CLIENT: RNFR oldname.txt
SERVER: 350 Ready for RNTO
CLIENT: RNTO newname.txt
SERVER: 250 Rename successful

# Delete file
CLIENT: DELE temp.txt
SERVER: 250 File deleted

# Disconnect
CLIENT: QUIT
SERVER: 221 Goodbye
CLIENT: (Closes TCP connection)
```

---

## Security Considerations

### Path Traversal Prevention

**Attack:**
```
CWD ../../../etc
RETR passwd
```

**Defense:**
```python
def get_real_path(self, ftp_path):
    real_path = os.path.abspath(os.path.join(self.root_dir, ftp_path))
    
    if not real_path.startswith(self.root_dir):
        raise PermissionError("Access denied")
    
    return real_path
```

### Anonymous FTP

**Safe configuration:**
```python
if username == "anonymous":
    # Read-only access
    # Restrict to public directory
    session.root_dir = "/var/ftp/pub"
    session.read_only = True
```

### Connection Timeouts

Prevent resource exhaustion:
```python
socket.settimeout(30)  # 30 second timeout
```

---

## Testing Your Implementation

### Manual Testing with Telnet

```bash
telnet localhost 2121

# Type commands manually:
USER test
PASS test
PWD
LIST
QUIT
```

### Manual Testing with FTP Client

```bash
ftp localhost 2121

# Or Python:
python manage.py ftp_test
```

### Unit Testing

Test individual components:
```python
# Test path security
session = FTPSession(sock, ("127.0.0.1", 5000), "/var/ftp")
try:
    session.get_real_path("../../../etc/passwd")
    assert False, "Should raise PermissionError"
except PermissionError:
    pass  # Expected
```

---

## Common Implementation Challenges

### 1. Firewall Issues

**Problem**: Passive mode ports blocked

**Solution**: Configure firewall to allow port range
```bash
# Linux iptables
iptables -A INPUT -p tcp --dport 2121 -j ACCEPT
iptables -A INPUT -p tcp --dport 50000:51000 -j ACCEPT
```

### 2. Line Ending Issues

**Problem**: Text files corrupted

**Solution**: Always use binary mode unless specifically need ASCII
```python
client.set_transfer_type('I')  # Binary mode
```

### 3. Response Parsing

**Problem**: Multi-line responses break parser

**Solution**: Check for last line properly
```python
if response_code == last_line[:3] and last_line[3] == ' ':
    break  # Final line
```

### 4. Data Connection Timeout

**Problem**: Client doesn't connect to passive port

**Solution**: Add timeout and error handling
```python
passive_socket.settimeout(30)
try:
    data_sock, addr = passive_socket.accept()
except socket.timeout:
    return "425 Can't open data connection"
```

---

## References

- **RFC 959**: FTP Protocol Specification (1985)
- **RFC 2228**: FTP Security Extensions
- **RFC 2428**: FTP Extensions for IPv6 and NATs (EPSV/EPRT)
- **RFC 3659**: Extensions to FTP (MLSD, SIZE, MDTM)

---

## Conclusion

FTP is a mature protocol with many nuances. This implementation covers:

✅ Complete command set (USER, PASS, LIST, RETR, STOR, etc.)  
✅ Passive mode (PASV/EPSV) for firewall compatibility  
✅ Binary and ASCII transfer modes  
✅ Path security and sandboxing  
✅ Proper response codes  
✅ Two-connection architecture  

The separation of control and data connections, while complex, enables robust and flexible file transfers that have stood the test of time since 1971.
