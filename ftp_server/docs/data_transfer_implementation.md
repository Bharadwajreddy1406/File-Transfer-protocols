# FTP Data Transfer Deep Dive

## Overview

This document explains how FTP handles data transfers using the two-connection architecture, focusing on the implementation details of LIST, RETR, and STOR commands.

## Table of Contents

1. [Why Two Connections?](#why-two-connections)
2. [Data Connection Lifecycle](#data-connection-lifecycle)
3. [Passive Mode Implementation](#passive-mode-implementation)
4. [LIST Command Walkthrough](#list-command-walkthrough)
5. [RETR Command Walkthrough](#retr-command-walkthrough)
6. [STOR Command Walkthrough](#stor-command-walkthrough)
7. [Error Handling](#error-handling)
8. [Performance Considerations](#performance-considerations)

---

## Why Two Connections?

### The Problem FTP Solves

Imagine trying to transfer files using only one connection:

```
CLIENT: LIST /pub
SERVER: -rw-r--r-- 1 ftp ftp 1234 Jan 01 12:00 file1.txt
        -rw-r--r-- 1 ftp ftp 5678 Jan 01 12:01 file2.txt
        226 Transfer complete
```

**Issues:**
- Can't tell where file data ends and response begins
- Commands blocked during large transfers
- Complex protocol needed to multiplex data

### FTP's Solution: Separate Channels

```
Control Connection (Port 21):
CLIENT: LIST /pub
SERVER: 150 Opening data connection

Data Connection (Port 5001):
SERVER: -rw-r--r-- 1 ftp ftp 1234 Jan 01 12:00 file1.txt
        -rw-r--r-- 1 ftp ftp 5678 Jan 01 12:01 file2.txt
        (closes connection)

Control Connection:
SERVER: 226 Transfer complete
```

**Benefits:**
- Clean separation: control is text, data is binary
- Can send commands during transfer
- Connection close signals end of data
- Simple protocol design

---

## Data Connection Lifecycle

### State Machine

```
┌─────────────┐
│   NO DATA   │  (Initial state)
│ CONNECTION  │
└──────┬──────┘
       │
       │ 1. Client sends PASV
       ▼
┌─────────────┐
│   PASSIVE   │  (Server creates listener)
│   PENDING   │
└──────┬──────┘
       │
       │ 2. Server responds: 227 (h,h,h,h,p,p)
       │ 3. Client connects to data port
       ▼
┌─────────────┐
│    DATA     │  (Connection established)
│  CONNECTED  │
└──────┬──────┘
       │
       │ 4. Client sends LIST/RETR/STOR
       │ 5. Server transfers data
       ▼
┌─────────────┐
│    DATA     │  (Transferring)
│ TRANSFERRING│
└──────┬──────┘
       │
       │ 6. Transfer completes
       │ 7. Data connection closes
       ▼
┌─────────────┐
│   NO DATA   │  (Back to initial state)
│ CONNECTION  │
└─────────────┘
```

### Per-Transfer Pattern

**Every data-transferring command follows this pattern:**

```python
# 1. Setup passive mode
client.send_command("PASV")
# Response: 227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)

# 2. Parse response and connect
data_host, data_port = parse_pasv_response(response)
data_conn = socket.connect((data_host, data_port))

# 3. Send command that needs data
client.send_command("LIST")
# Response: 150 Opening data connection

# 4. Transfer data on data connection
data = data_conn.recv()

# 5. Close data connection
data_conn.close()

# 6. Read completion message on control connection
# Response: 226 Transfer complete
```

**Key Point**: Data connection is opened and closed for EACH transfer.

---

## Passive Mode Implementation

### Server Side

#### Step 1: Create Listener Socket

```python
class PassiveModeManager:
    def setup_passive_mode(self, server_host):
        # Create socket
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Reuse address (avoid "Address already in use" errors)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to random port (0 = let OS choose)
        self.listen_socket.bind((server_host, 0))
        
        # Get actual port assigned
        host, port = self.listen_socket.getsockname()
        
        # Listen for ONE connection
        self.listen_socket.listen(1)
        
        return host, port
```

**Why port 0?**
- Let OS choose available port
- Avoids conflicts
- Dynamic port range (usually 49152-65535)

#### Step 2: Format Response

```python
def handle_pasv(self, session):
    host, port = session.passive_manager.setup_passive_mode(self.host)
    
    # Convert IP: "192.168.1.100" → "192,168,1,100"
    h1, h2, h3, h4 = host.split('.')
    
    # Convert port: 5001 → (19, 137)
    # Formula: port = p1 * 256 + p2
    p1 = port // 256  # Integer division
    p2 = port % 256   # Remainder
    
    # Send response
    self.send_response(f"227 Entering Passive Mode ({h1},{h2},{h3},{h4},{p1},{p2})")
```

**Port calculation example:**
```
Port 5001:
p1 = 5001 // 256 = 19
p2 = 5001 % 256 = 137

Verification:
19 * 256 + 137 = 4864 + 137 = 5001 ✓
```

#### Step 3: Accept Client Connection

```python
def accept_data_connection(self, timeout=30):
    self.listen_socket.settimeout(timeout)
    
    try:
        # Accept ONE connection
        self.data_socket, client_addr = self.listen_socket.accept()
        return self.data_socket
    except socket.timeout:
        raise TimeoutError("Client didn't connect")
```

### Client Side

#### Step 1: Send PASV Command

```python
def _open_data_connection(self):
    # Try EPSV first (simpler)
    response = self.connection.send_command("EPSV")
    
    if response.startswith('229'):
        # EPSV format: 229 Entering Extended Passive Mode (|||port|)
        port = parse_epsv_response(response)
        host = self.host  # Use same host
    else:
        # Fall back to PASV
        response = self.connection.send_command("PASV")
        # PASV format: 227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)
        host, port = parse_pasv_response(response)
    
    return host, port
```

#### Step 2: Parse Response

```python
def _parse_pasv_response(self, response):
    import re
    
    # Extract 6 numbers from parentheses
    match = re.search(r'\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)', response)
    h1, h2, h3, h4, p1, p2 = match.groups()
    
    # Reconstruct host and port
    host = f"{h1}.{h2}.{h3}.{h4}"
    port = int(p1) * 256 + int(p2)
    
    return host, port
```

#### Step 3: Connect to Data Port

```python
# Create new connection for data
data_conn = FTPConnection(data_host, data_port, is_control=False)
data_conn.connect()  # No welcome message expected
```

---

## LIST Command Walkthrough

### Complete Flow

```
┌────────┐                    ┌────────┐
│ CLIENT │                    │ SERVER │
└───┬────┘                    └───┬────┘
    │                              │
    │ 1. PASV                      │
    ├─────────────────────────────>│
    │                              │ (Create listener on port 5001)
    │                              │
    │ 2. 227 (...,19,137)          │
    │<─────────────────────────────┤
    │                              │
    │ 3. TCP connect to :5001      │
    ├══════════════════════════════>│ (Data connection established)
    │                              │
    │ 4. LIST /pub                 │
    ├─────────────────────────────>│
    │                              │ (Read directory)
    │                              │
    │ 5. 150 Opening...            │
    │<─────────────────────────────┤
    │                              │
    │ 6. Directory listing         │
    │<══════════════════════════════┤ (Via data connection)
    │                              │
    │ 7. (Close data connection)   │
    │<══════════════════════════════┤
    │                              │
    │ 8. 226 Transfer complete     │
    │<─────────────────────────────┤
    │                              │
```

### Client Implementation

```python
def list_files(self, path='.'):
    # Step 1-3: Open data connection
    data_conn = self._open_data_connection()
    
    try:
        # Step 4: Send LIST command
        list_response = self.connection.send_command(f"LIST {path}")
        
        # Step 5: Verify server is sending data
        if not list_response.startswith('150'):
            raise Exception(f"LIST failed: {list_response}")
        
        # Step 6: Read directory listing from data connection
        listing = b''
        while True:
            chunk = data_conn.sock.recv(4096)
            if not chunk:  # Connection closed = complete
                break
            listing += chunk
        
        # Step 7: (Data connection closed by server)
        
        # Step 8: Read completion message
        completion = self.connection._read_response()
        if not completion.startswith('226'):
            print(f"Warning: {completion}")
        
        return listing.decode('utf-8')
        
    finally:
        # Always close data connection
        data_conn.close()
```

### Server Implementation

```python
def handle_list(self, session, path):
    # Security: Check authentication
    if not session.is_authenticated:
        self.send_response(session, "530 Not logged in")
        return
    
    # Verify passive mode was setup
    if not hasattr(session, 'passive_manager'):
        self.send_response(session, "425 Use PASV first")
        return
    
    try:
        # Get real filesystem path (with security checks)
        real_path = session.get_real_path(path)
        
        # Read directory
        listing = FileSystemHelper.list_directory(real_path)
        
        # Step 5: Tell client we're sending data
        self.send_response(session, "150 Opening data connection")
        
        # Step 3: Accept client's data connection
        session.passive_manager.accept_data_connection()
        
        # Step 6: Send listing
        session.passive_manager.send_data(listing.encode('utf-8'))
        
        # Step 7: Close data connection
        session.passive_manager.close()
        
        # Step 8: Send completion
        self.send_response(session, "226 Directory listing sent")
        
    except FileNotFoundError:
        session.passive_manager.close()
        self.send_response(session, "550 Directory not found")
```

### Directory Listing Format

FTP uses Unix `ls -l` format:

```
-rw-r--r--   1 ftp  ftp     1234 Jan  1 12:00 file.txt
drwxr-xr-x   1 ftp  ftp        0 Jan  1 12:00 folder
```

**Format breakdown:**
```
-rw-r--r--  │ 1 │ ftp │ ftp │  1234 │ Jan  1 12:00 │ file.txt
    │       │   │     │     │       │              │
Permissions Links Owner Group Size   Modification  Name
```

**Implementation:**
```python
def list_directory(real_path):
    entries = os.listdir(real_path)
    lines = []
    
    for entry in entries:
        stats = os.stat(os.path.join(real_path, entry))
        
        # Determine type
        if os.path.isdir(entry):
            perms = 'drwxr-xr-x'
            size = 0
        else:
            perms = '-rw-r--r--'
            size = stats.st_size
        
        # Format modification time
        mtime = time.localtime(stats.st_mtime)
        time_str = time.strftime("%b %d %H:%M", mtime)
        
        # Build line
        line = f"{perms} 1 ftp ftp {size:>12} {time_str} {entry}"
        lines.append(line)
    
    return "\r\n".join(lines) + "\r\n"
```

---

## RETR Command Walkthrough

### Complete Flow

```
┌────────┐                    ┌────────┐
│ CLIENT │                    │ SERVER │
└───┬────┘                    └───┬────┘
    │                              │
    │ 1-3. (Passive mode setup)    │
    │                              │
    │ 4. RETR file.txt             │
    ├─────────────────────────────>│
    │                              │ (Read file: 1234 bytes)
    │                              │
    │ 5. 150 Opening... (1234)     │
    │<─────────────────────────────┤
    │                              │
    │ 6. File data (1234 bytes)    │
    │<══════════════════════════════┤ (Via data connection)
    │                              │
    │ 7. (Close data connection)   │
    │<══════════════════════════════┤
    │                              │
    │ 8. 226 Transfer complete     │
    │<─────────────────────────────┤
    │                              │
```

### Client Implementation

```python
def download_file(self, remote_filename, local_filename=None):
    if local_filename is None:
        local_filename = remote_filename
    
    # Set binary mode (important!)
    self.connection.send_command("TYPE I")
    
    # Open data connection
    data_conn = self._open_data_connection()
    
    try:
        # Send RETR command
        retr_response = self.connection.send_command(f"RETR {remote_filename}")
        
        # Check for success (150 or 125)
        if not (retr_response.startswith('150') or retr_response.startswith('125')):
            if retr_response.startswith('550'):
                raise Exception(f"File not found: {remote_filename}")
            else:
                raise Exception(f"RETR failed: {retr_response}")
        
        # Read file data
        file_data = b''
        bytes_received = 0
        
        while True:
            chunk = data_conn.sock.recv(8192)  # 8KB chunks
            if not chunk:
                break
            
            file_data += chunk
            bytes_received += len(chunk)
            
            # Progress indicator
            if bytes_received % 102400 == 0:  # Every 100KB
                print(f"Received: {bytes_received:,} bytes")
        
        # Save to local file
        with open(local_filename, 'wb') as f:
            f.write(file_data)
        
        # Read completion
        completion = self.connection._read_response()
        
        return bytes_received
        
    finally:
        data_conn.close()
```

### Server Implementation

```python
def handle_retr(self, session, filename):
    if not session.is_authenticated:
        self.send_response(session, "530 Not logged in")
        return
    
    if not hasattr(session, 'passive_manager'):
        self.send_response(session, "425 Use PASV first")
        return
    
    try:
        # Get real path
        real_path = session.get_real_path(filename)
        
        # Read file
        file_data = FileSystemHelper.read_file(real_path)
        
        # Tell client file size
        self.send_response(session, 
            f"150 Opening data connection ({len(file_data)} bytes)")
        
        # Accept data connection
        session.passive_manager.accept_data_connection()
        
        # Send file
        session.passive_manager.send_data(file_data)
        
        # Close data connection
        session.passive_manager.close()
        
        # Send completion
        self.send_response(session, "226 Transfer complete")
        
    except FileNotFoundError:
        session.passive_manager.close()
        self.send_response(session, "550 File not found")
    except IsADirectoryError:
        session.passive_manager.close()
        self.send_response(session, "550 Is a directory, not a file")
```

---

## STOR Command Walkthrough

### Complete Flow

```
┌────────┐                    ┌────────┐
│ CLIENT │                    │ SERVER │
└───┬────┘                    └───┬────┘
    │                              │
    │ 1-3. (Passive mode setup)    │
    │                              │
    │ 4. STOR newfile.txt          │
    ├─────────────────────────────>│
    │                              │
    │ 5. 150 Ready to receive      │
    │<─────────────────────────────┤
    │                              │
    │ 6. File data (5678 bytes)    │
    ├══════════════════════════════>│ (Via data connection)
    │                              │
    │ 7. (Close data connection)   │
    ├══════════════════════════════>│ (Signals completion)
    │                              │
    │                              │ (Write to disk)
    │                              │
    │ 8. 226 Transfer complete     │
    │<─────────────────────────────┤
    │                              │
```

### Key Difference from RETR

**RETR (Download):**
- Server sends data
- Server closes data connection

**STOR (Upload):**
- Client sends data
- **Client closes data connection** (signals end of file)
- Server waits for close, then responds

### Client Implementation

```python
def upload_file(self, local_filename, remote_filename=None):
    if remote_filename is None:
        remote_filename = os.path.basename(local_filename)
    
    # Read local file
    with open(local_filename, 'rb') as f:
        file_data = f.read()
    
    # Set binary mode
    self.connection.send_command("TYPE I")
    
    # Open data connection
    data_conn = self._open_data_connection()
    
    try:
        # Send STOR command
        stor_response = self.connection.send_command(f"STOR {remote_filename}")
        
        # Check for success
        if not (stor_response.startswith('150') or stor_response.startswith('125')):
            raise Exception(f"STOR failed: {stor_response}")
        
        # Send file data in chunks
        bytes_sent = 0
        chunk_size = 8192
        
        for i in range(0, len(file_data), chunk_size):
            chunk = file_data[i:i+chunk_size]
            data_conn.sock.sendall(chunk)
            bytes_sent += len(chunk)
        
        # IMPORTANT: Close data connection to signal completion
        data_conn.close()
        
        # Read completion message
        completion = self.connection._read_response()
        
        if not completion.startswith('226'):
            print(f"Warning: {completion}")
        
        return bytes_sent
        
    except Exception:
        # On error, still try to close
        try:
            data_conn.close()
        except:
            pass
        raise
```

### Server Implementation

```python
def handle_stor(self, session, filename):
    if not session.is_authenticated:
        self.send_response(session, "530 Not logged in")
        return
    
    if not hasattr(session, 'passive_manager'):
        self.send_response(session, "425 Use PASV first")
        return
    
    try:
        # Get real path
        real_path = session.get_real_path(filename)
        
        # Tell client we're ready
        self.send_response(session, f"150 Ready to receive {filename}")
        
        # Accept data connection
        session.passive_manager.accept_data_connection()
        
        # Receive ALL data (blocks until client closes connection)
        file_data = session.passive_manager.receive_data()
        
        # Write to disk
        bytes_written = FileSystemHelper.write_file(real_path, file_data)
        
        # Close data connection
        session.passive_manager.close()
        
        # Send completion with byte count
        self.send_response(session, 
            f"226 Transfer complete ({bytes_written} bytes received)")
        
    except PermissionError:
        session.passive_manager.close()
        self.send_response(session, "550 Permission denied")
```

### How Server Knows Transfer is Complete

```python
def receive_data(self):
    data = b''
    
    while True:
        chunk = self.data_socket.recv(8192)
        
        if not chunk:
            # Empty chunk = client closed connection
            # This signals end of file
            break
        
        data += chunk
    
    return data
```

**Why this works:**
- `recv()` returns empty bytes when connection closed
- Client explicitly closes after sending all data
- Server reads until close, then proceeds

---

## Error Handling

### Common Errors

#### 1. No Passive Mode Setup

```python
# Client sends LIST without PASV
CLIENT: LIST
SERVER: 425 Use PASV or Port first
```

**Fix:**
```python
if not hasattr(session, 'passive_manager'):
    self.send_response(session, "425 Use PASV or EPSV first")
    return
```

#### 2. Client Connection Timeout

```python
# Server waits, but client never connects
SERVER: 227 Entering Passive Mode (...)
(30 seconds pass)
TIMEOUT: Client did not connect
```

**Fix:**
```python
self.listen_socket.settimeout(30)
try:
    data_sock, addr = self.listen_socket.accept()
except socket.timeout:
    return "425 Cannot open data connection"
```

#### 3. Data Connection Interrupted

```python
# Transfer starts, then network fails
CLIENT: RETR largefile.zip
SERVER: 150 Opening data connection
(connection drops mid-transfer)
```

**Client handling:**
```python
try:
    file_data = receive_all_data()
except ConnectionResetError:
    print("Transfer interrupted")
    # Don't save partial file
    return
```

#### 4. File Not Found

```python
CLIENT: RETR nonexistent.txt
SERVER: 550 File not found
```

**Server handling:**
```python
try:
    file_data = FileSystemHelper.read_file(real_path)
except FileNotFoundError:
    # Close passive connection first
    session.passive_manager.close()
    self.send_response(session, "550 File not found")
    return
```

### Always Close Data Connection

```python
try:
    # Transfer operations
    transfer_data()
    self.send_response("226 Complete")
except Exception as e:
    self.send_response("550 Failed")
finally:
    # ALWAYS close, even on error
    if session.passive_manager:
        session.passive_manager.close()
```

---

## Performance Considerations

### Chunk Size

```python
# Too small: Many system calls
chunk_size = 512  # ❌ Slow

# Too large: High memory usage
chunk_size = 10 * 1024 * 1024  # ❌ 10MB chunks

# Just right: Balance performance and memory
chunk_size = 8192  # ✅ 8KB (common)
```

### Progress Indicators

```python
bytes_received = 0
last_update = 0

while True:
    chunk = sock.recv(8192)
    if not chunk:
        break
    
    bytes_received += len(chunk)
    
    # Update every 100KB
    if bytes_received - last_update >= 102400:
        print(f"Progress: {bytes_received / 1024:.1f} KB")
        last_update = bytes_received
```

### Socket Buffering

```python
# Enable TCP buffering for better performance
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)

# Increase buffer sizes for large transfers
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
```

### Reusing Sockets

```python
# Allow quick socket reuse (avoid "Address in use" errors)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
```

---

## Conclusion

The FTP two-connection architecture, while complex, provides:

✅ Clean separation of control and data  
✅ Simple end-of-data signaling (connection close)  
✅ Ability to send commands during transfers  
✅ Flexible passive mode for firewall traversal  

Key implementation principles:

1. **One data connection per transfer** - Open, use, close
2. **Client closes for STOR** - Signals end of upload
3. **Server closes for RETR/LIST** - Signals end of download
4. **Always cleanup** - Close data connection in finally block
5. **Proper error handling** - Close connections on errors

This design has proven robust for over 50 years of file transfers across the internet.
