# Deep Dive: How FTP Actually Works

## The Big Picture: Two Conversations Happening At Once

FTP is unique because it uses **two separate TCP connections** running simultaneously:

```
CLIENT                                    SERVER

Control Connection (Port 21) - The "Brain"
├─ Sends commands ────────────────────→  Receives & executes
├─ "USER anonymous" ──────────────────→  Checks username
│                    ←──────────────── "331 Need password"
├─ "PASS guest@" ─────────────────────→  Validates login
│                    ←──────────────── "230 Login OK"
├─ "LIST" ────────────────────────────→  Prepares directory data
│                    ←──────────────── "150 Sending data..."
│  [waits for data connection to finish]
│                    ←──────────────── "226 Transfer complete"
└─ Stays open entire session

Data Connection (Random Port) - The "Worker"
├─ Opens on-demand ───────────────────→  Server listens on random port
├─ Receives bytes ←──────────────────   Sends directory listing
└─ Closes automatically when done
```

**Why two connections?**
- Historical reasons (1971 design)
- Separates "commands" from "data"
- Allows you to cancel transfers without killing the session

---

## The Protocol Flow: Step-by-Step Anatomy

Let me trace through a complete FTP session showing **exactly** what happens:

### Phase 1: Connection & Authentication

```
[CLIENT OPENS SOCKET TO SERVER:21]

Client: [TCP SYN] → 
Server: [TCP SYN-ACK] ←
Client: [TCP ACK] →

[TCP CONNECTION ESTABLISHED]

Server → Client:
"220 GNU FTP server ready.\r\n"

Client → Server:
"USER anonymous\r\n"

Server → Client:
"230-NOTICE: Welcome message...\r\n"
"230-More info...\r\n"
"230 Login successful.\r\n"
```

**Key insights:**

1. **Server speaks first** - Immediately sends "220 Ready"
2. **Every command ends with `\r\n`** (CRLF - Carriage Return + Line Feed)
3. **Multi-line responses** have special format:
   - First lines: `"230-Message"` (hyphen after code)
   - Last line: `"230 Final message"` (space after code)

---

### Phase 2: Passive Mode Negotiation

This is where the **second connection** gets set up:

```
Client → Server (control connection):
"EPSV\r\n"

Server → Client (control connection):
"229 Extended Passive Mode Entered (|||27546|).\r\n"
         ^                           ^^^^^
         |                           PORT NUMBER
         Success code
```

**What just happened:**

1. Client asks: "Hey, I want to receive data. Where should I connect?"
2. Server responds: "Open a connection to me on port 27546"

**The format `(|||27546|)`:**
- Old PASV format: `(h1,h2,h3,h4,p1,p2)` → IP + port calculation
- New EPSV format: `(|||port|)` → Just the port, use same IP

**Port calculation (PASV only):**
```python
# PASV response: (209,51,188,20,234,10)
ip = f"{209}.{51}.{188}.{20}"  # → 209.51.188.20
port = 234 * 256 + 10          # → 59,914

# Why? FTP uses 2 bytes to encode port:
# High byte (234) * 256 + Low byte (10) = full 16-bit port number
```

---

### Phase 3: Data Transfer - LIST Example

Now we have TWO connections open. Watch what happens:

```
CONTROL CONNECTION (Port 21):
Client → Server:
"LIST .\r\n"

Server → Client:
"150 Here comes the directory listing.\r\n"
         ^
         "I'm about to send data on the OTHER connection"

[CLIENT WAITS... data is coming on separate connection]

Server → Client:
"226 Directory send OK.\r\n"
         ^
         "Data transfer finished successfully"


DATA CONNECTION (Port 27546):
[CLIENT OPENS NEW SOCKET TO SERVER:27546]

Server → Client (raw bytes):
"drwxrwxr-x  326 0  3003  12288 Jan 21 19:58 gnu\r\n"
"-rw-rw-r--    1 0  3003 257944 Feb 04 14:50 find.txt.gz\r\n"
"drwxr-xr-x    3 0     0   4096 Apr 20  2005 mirrors\r\n"
...

[SERVER CLOSES CONNECTION]
```

**Critical sequence:**

1. **Client sends LIST** on control → Server says "150 Starting..."
2. **Server sends actual data** on data connection
3. **Server closes data connection** when done
4. **Server sends "226 Complete"** on control connection

**Why this order matters:**
- If you read "226" before reading data, you'll miss the file listing!
- Must read from data connection first, then check for completion

---

### Phase 4: File Download - RETR Example

Same pattern, but receiving file bytes:

```
CONTROL:
Client: "TYPE I\r\n"              (Set to binary mode)
Server: "200 Type set to I.\r\n"

Client: "EPSV\r\n"
Server: "229 Entering Extended Passive Mode (|||28451|).\r\n"

Client: "RETR README\r\n"
Server: "150 Opening BINARY mode data connection for README (2814 bytes).\r\n"
                                                             ^^^^^^^^^^^
                                    (Server tells you file size - helpful!)

[Wait for data...]

Server: "226 Transfer complete.\r\n"


DATA:
[Client connects to port 28451]

Server → Client (raw bytes):
0x54 0x68 0x69 0x73 0x20 0x66 0x69 0x6C ...
 T    h    i    s         f    i    l   ...
 
[Exactly 2,814 bytes sent]
[Server closes connection]
```

**File transfer specifics:**

1. **TYPE I (binary)** - Send bytes exactly as-is
2. **TYPE A (ASCII)** - Convert line endings (rarely used now)
3. **Server closes data connection** = transfer done
4. **Empty recv()** = Connection closed by server

---

## Response Code Architecture

FTP uses **3-digit response codes** like HTTP:

### Code Structure: `XYZ Message`

**First digit (X) - Category:**
```
1xx - Positive Preliminary (wait, more coming)
2xx - Positive Completion (success!)
3xx - Positive Intermediate (need more info from you)
4xx - Transient Negative (try again later)
5xx - Permanent Negative (don't retry, it won't work)
```

**Second digit (Y) - Grouping:**
```
x0x - Syntax
x1x - Information
x2x - Connections
x3x - Authentication
x4x - Unspecified
x5x - File system
```

**Third digit (Z) - Specific meaning**

### Common Codes We Use:

```python
# Connection
220 - "Service ready for new user" (welcome)
221 - "Service closing" (goodbye)

# Authentication  
230 - "User logged in"
331 - "User name okay, need password"
530 - "Not logged in"

# File operations
150 - "File status okay; about to open data connection"
125 - "Data connection already open; transfer starting"
226 - "Closing data connection; transfer complete"
250 - "Requested file action okay"

# Passive mode
227 - "Entering Passive Mode (h1,h2,h3,h4,p1,p2)"
229 - "Extended Passive Mode (|||port|)"

# Errors
425 - "Can't open data connection"
450 - "File unavailable (busy)"
550 - "File not found or no permission"
```

---

## Data Parsing: Three Levels

### Level 1: Socket-Level (Bytes)

```python
# Reading from socket
chunk = sock.recv(4096)  # Returns bytes object
# b'220 Welcome\r\n'
```

**What we deal with:**
- Raw bytes (not strings)
- Arbitrary chunk sizes (might get 100 bytes, might get 4000)
- Need to decode: `bytes → str`

### Level 2: Protocol-Level (FTP Responses)

```python
# Complete response reading
def _read_response(self):
    response = b''
    
    while True:
        chunk = sock.recv(4096)
        response += chunk
        
        # Check if we have complete response
        if ends_with_complete_line(response):
            break
    
    return response.decode('utf-8')
```

**Challenges:**

1. **Multi-line responses:**
```
"230-Line 1\r\n"
"230-Line 2\r\n"  
"230 Final line\r\n"  ← Stop here (space, not hyphen)
```

2. **Buffering:** Response might arrive in chunks
```
First recv():  "230-Welcome to\r\n230-FTP se"
Second recv(): "rver\r\n230 Login OK\r\n"
```

Must reassemble before parsing!

### Level 3: Semantic-Level (Extracting Meaning)

```python
# Parse EPSV response
response = "229 Extended Passive Mode Entered (|||27546|).\r\n"

# Extract code
code = response[:3]  # "229"

# Extract port
match = re.search(r'\(\|\|\|(\d+)\|\)', response)
port = int(match.group(1))  # 27546

# Now we know: Connect to port 27546 for data
```

---

## The State Machine

FTP client goes through states:

```
DISCONNECTED
    ↓ connect()
CONNECTED (got 220 welcome)
    ↓ login()
AUTHENTICATED (got 230 login success)
    ↓ Can now use: LIST, RETR, STOR, CWD, etc.
READY
    ↓ For each data transfer:
    ├→ PASV/EPSV → Got port
    ├→ Open data connection
    ├→ Send command (LIST/RETR/STOR)
    ├→ TRANSFERRING DATA
    └→ Close data connection → READY again
    
    ↓ quit()
DISCONNECTED
```

**You can't skip states:**
- Can't LIST before login
- Can't RETR before PASV
- Must close data connection before next transfer

---

## Data Flow Visualization

Let me show you the **actual bytes** flowing:

### Example: Downloading "README"

```
TIME  CONNECTION  DIRECTION  DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

T0    Control     →          "TYPE I\r\n"
                             [54 59 50 45 20 49 0d 0a]

T1    Control     ←          "200 Type set to I.\r\n"
                             [32 30 30 20 54 79 70 65 ...]

T2    Control     →          "EPSV\r\n"

T3    Control     ←          "229 Extended Passive Mode (|||28451|).\r\n"

T4    Data        [CONNECT]  Client opens socket to port 28451

T5    Control     →          "RETR README\r\n"

T6    Control     ←          "150 Opening BINARY mode data connection.\r\n"

T7    Data        ←          [File bytes start]
                             54 68 69 73 20 66 69 6c 65 20 69 73 ...
                             "This file is README for the FTP..."

T8    Data        ←          [More bytes...]
                             
T9    Data        ←          [Last chunk]
                             
T10   Data        ←          [Empty recv() = connection closed]

T11   Control     ←          "226 Transfer complete.\r\n"
```

**Notice:**
- Control and data connections **interleave**
- Data flows while control waits
- Completion message comes AFTER data finishes

---

## Parsing Challenges We Solved

### Challenge 1: Multi-line Responses

**Problem:**
```python
# Naive approach - WRONG!
response = sock.recv(4096).decode('utf-8')
# Only gets first chunk, might miss rest of multi-line response
```

**Solution:**
```python
# Keep reading until final line
while True:
    chunk = sock.recv(4096)
    response += chunk
    
    lines = response.decode('utf-8').split('\n')
    last_line = lines[-1]
    
    # Check if last line is final (has space, not hyphen)
    if last_line[:3].isdigit() and last_line[3] == ' ':
        break  # Got complete response
```

### Challenge 2: Parsing PASV/EPSV

**Problem:** Two different formats to handle

**Solution:**
```python
def _parse_pasv_response(self, response):
    if response.startswith('229'):
        # EPSV: (|||port|)
        match = re.search(r'\(\|\|\|(\d+)\|\)', response)
        port = int(match.group(1))
        host = self.host  # Use same as control
        
    elif response.startswith('227'):
        # PASV: (h1,h2,h3,h4,p1,p2)
        match = re.search(r'\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)', response)
        h1, h2, h3, h4, p1, p2 = match.groups()
        host = f"{h1}.{h2}.{h3}.{h4}"
        port = int(p1) * 256 + int(p2)
    
    return host, port
```

### Challenge 3: Data Connection Lifecycle

**Problem:** When to open/close data connection?

**Solution:**
```python
# 1. Open BEFORE sending command
data_conn = self._open_data_connection()  # EPSV + connect

# 2. Send command on CONTROL
self.connection.send_command("RETR file")

# 3. Read from DATA connection
while True:
    chunk = data_conn.sock.recv(8192)
    if not chunk:  # Server closed = done
        break
    file_data += chunk

# 4. Close data connection
data_conn.close()

# 5. Read completion from CONTROL
completion = self.connection._read_response()  # "226 Transfer complete"
```

---

## Key Insights Summary

### 1. **Two Connections = Two Responsibilities**
- **Control:** Commands, responses, coordination
- **Data:** Actual file/listing bytes

### 2. **Response Codes Tell You What To Do**
- 1xx: Wait for more
- 2xx: Success, proceed
- 3xx: Need more input
- 4xx/5xx: Error, handle it

### 3. **Data Connection Pattern**
```
PASV/EPSV → Get port → Connect → Send command → 
Transfer data → Server closes → Read "226 Complete"
```

### 4. **Everything is Text (Control) or Bytes (Data)**
- Control connection: Text commands and responses
- Data connection: Raw bytes (could be text, could be binary)

### 5. **Parsing is Multi-Level**
```
Raw bytes → Complete responses → Extract codes → 
Parse parameters → Take action
```

### 6. **State Machine Enforces Order**
```
Connect → Auth → (Repeat: PASV → Transfer → Close) → Quit
```

---

## What Makes FTP Hard?

1. **Two connections** - Firewalls hate this
2. **No encryption** - All passwords/data in plaintext
3. **NAT problems** - Active mode doesn't work behind NAT
4. **Stateful** - Must track where you are in the flow
5. **Text protocol** - Parsing is error-prone

**This is why SFTP and HTTPS exist!**

---
