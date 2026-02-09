## HTTP vs FTP: The Key Difference

### HTTP: One Connection Per Request

```
HTTP Flow:

1. Open connection to server:80
2. Send: "GET /file.txt HTTP/1.1"
3. Receive: "200 OK" + file data
4. Close connection
5. Done!

Every request = new connection (unless using keep-alive)
```

### FTP: Two Connections That Stay Open

```
FTP Flow:

Connection 1 (CONTROL - port 21):
1. Open connection - stays open entire session
2. Send: "USER alice"
3. Receive: "331 Need password"
4. Send: "PASS secret123"
5. Receive: "230 Login OK"
6. Send: "RETR file.txt"
7. Receive: "150 Sending file..."
8. [Wait...]
9. Receive: "226 Transfer complete"
10. Send: "QUIT"
11. Close connection

Connection 2 (DATA - random port):
1. Server says: "Connect to port 12345"
2. Open connection to server:12345
3. Receive: [file bytes]
4. Server closes connection
5. Done with this file

For next file, repeat steps 1-5 with NEW port
```

**The Big Difference:**
- **HTTP:** One connection does everything
- **FTP:** Two connections - one for talking, one for data

---

## Think of FTP Like a Restaurant

### HTTP Restaurant:
```
You: "I'll have a burger"
Waiter: [brings burger]
You: "Thanks, bye!"
[You leave]

Next time:
You: "I'll have fries"  
Waiter: [brings fries]
[You leave again]
```

Every request = new interaction.

### FTP Restaurant:
```
You: "Hi, I'm Alice" (USER)
Waiter: "Password please" (331)
You: "opensesame" (PASS)
Waiter: "Welcome! Sit down" (230)

[You stay seated - connection stays open]

You: "I want the burger menu" (LIST)
Waiter: "Go to table 5, runner will bring it" (229 port)
[Runner at table 5 brings menu]
Runner: [leaves after delivery]

You: "I'll have a burger" (RETR)
Waiter: "Go to table 7, runner will bring it"
[Runner at table 7 brings burger]
Runner: [leaves after delivery]

You: "I'm done, check please" (QUIT)
Waiter: "Goodbye!" (221)
[You leave]
```

The **waiter** (control connection) stays with you the whole time.
The **runners** (data connections) bring items and leave.

---

## Comparing Protocols Side-by-Side

### HTTP GET Request

```http
# What you send:
GET /files/document.pdf HTTP/1.1
Host: example.com
Authorization: Basic dXNlcjpwYXNz


# What you receive:
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Length: 50000

[50,000 bytes of PDF data]
```

**Everything in ONE conversation over ONE connection.**

---

### FTP File Download

```
# Connection 1 (CONTROL):
CLIENT: USER alice
SERVER: 331 Password required

CLIENT: PASS secret123  
SERVER: 230 Login successful

CLIENT: EPSV
SERVER: 229 Extended Passive Mode (|||12345|)
        "Hey, connect to port 12345 for data"

# Connection 2 (DATA) - You open this now:
[Open socket to server:12345]

# Back to Connection 1 (CONTROL):
CLIENT: RETR document.pdf
SERVER: 150 Opening BINARY mode data connection

# Now read from Connection 2 (DATA):
[Receive 50,000 bytes of PDF data]
[Server closes this connection]

# Back to Connection 1 (CONTROL):
SERVER: 226 Transfer complete

CLIENT: QUIT
SERVER: 221 Goodbye
```

**Same file transfer, but split across TWO connections.**

---

## Status Codes: HTTP vs FTP

You know HTTP status codes. FTP codes work similarly:

### HTTP Status Codes

```
1xx - Informational (100 Continue)
2xx - Success (200 OK, 201 Created)
3xx - Redirection (301 Moved, 302 Found)
4xx - Client Error (404 Not Found, 403 Forbidden)
5xx - Server Error (500 Internal Error)
```

### FTP Status Codes

```
1xx - Positive Preliminary (150 Starting transfer)
2xx - Success (200 OK, 230 Login successful)
3xx - Need More Info (331 Need password)
4xx - Temporary Failure (450 File busy)
5xx - Permanent Failure (550 File not found)
```

### Direct Comparisons

| Scenario | HTTP | FTP |
|----------|------|-----|
| Success | 200 OK | 200 Command OK |
| Authenticated | 200 OK | 230 User logged in |
| File not found | 404 Not Found | 550 Requested action not taken |
| Permission denied | 403 Forbidden | 550 Permission denied |
| Need credentials | 401 Unauthorized | 331 User name okay, need password |
| Starting transfer | (no equivalent) | 150 File status okay |

---

## Authentication: HTTP vs FTP

### HTTP Basic Auth

```http
GET /file.txt HTTP/1.1
Authorization: Basic YWxpY2U6c2VjcmV0MTIz
                     ↑ base64("alice:secret123")

HTTP/1.1 200 OK
[file data]
```

**One header, done.**

### FTP Auth

```
CLIENT: USER alice
SERVER: 331 User name okay, need password

CLIENT: PASS secret123
SERVER: 230 User logged in, proceed
```

**Two-step handshake** (like a login form on a website).

**Why?** FTP was designed in 1971, before the concept of "headers" existed. They literally had a conversation:
- "Who are you?"
- "I'm Alice"
- "What's your password?"
- "secret123"

---

## The Passive Mode Puzzle (FTP's Weird Part)

This is where FTP gets weird compared to HTTP.

### HTTP Data Flow (Simple)

```
CLIENT                     SERVER
   |                          |
   |--- GET /file.txt ------->|
   |                          |
   |<----- 200 OK + data -----|
   |                          |
```

One connection. Data comes back on same connection.

### FTP Data Flow (Complex)

```
CLIENT                     SERVER
   |                          |
CONTROL CONNECTION (port 21):
   |--- USER alice ---------->|
   |<------ 331 Need pass ----|
   |--- PASS secret --------->|
   |<------ 230 Login OK -----|
   |                          |
   |--- EPSV --------------->| "I need a data connection"
   |<------ 229 Use port 12345|
   |                          |
   
DATA CONNECTION (port 12345):
   |===== Opens connection ===>|
   |                          |
   
Back to CONTROL:
   |--- RETR file.txt ------->| "Send me file.txt"
   |<------ 150 Sending -------|
   |                          |
   
On DATA connection:
   |<===== [file bytes] =======|
   |                          |
   [Server closes data conn]
   
Back to CONTROL:
   |<------ 226 Complete ------|
```

**Why so complicated?**

In 1971, they thought:
- "Commands are lightweight, keep that connection open"
- "Data is heavy, open a new connection for each transfer"

In 2025, we think:
- "This is insane, just use one connection" (hence HTTPS)

---

## The "PASV" Command Explained

Think of PASV like saying "Where should I pick up my order?"

### Analogy: HTTP (Delivery to Your Door)

```http
You: "Send me file.txt"
Server: "Here it is!" [sends data back to you]
```

Server delivers to where you are.

### Analogy: FTP (Pickup Counter)

```
You: "Where can I pick up my order?" (EPSV)
Server: "Counter #12345" (229 |||12345|)

You: [Walk to counter #12345]
You: "I'm here for file.txt" (RETR file.txt)
Server: [Hands you file.txt at counter #12345]
```

**PASV/EPSV** = "Tell me which pickup counter to go to"

---

## Code Comparison: HTTP vs FTP

### Downloading a File with HTTP (Python)

```python
import requests

# One function call!
response = requests.get('http://example.com/file.txt')

if response.status_code == 200:
    with open('file.txt', 'wb') as f:
        f.write(response.content)
```

**Simple. One request. Done.**

---

### Downloading a File with FTP (Using Our Code)

```python
from ftp_client.services.ftp_core import FTPClient

# Create client
client = FTPClient('ftp.example.com')

# Step 1: Connect
client.connect()

# Step 2: Login
client.login('alice', 'secret123')

# Step 3: Download
client.download_file('file.txt', 'local_file.txt')

# Step 4: Disconnect
client.quit()
```

**More steps, but similar concept.**

---

### What Happens Under the Hood

#### HTTP (Simplified):

```python
import socket

# 1. Connect
sock = socket.socket()
sock.connect(('example.com', 80))

# 2. Send request
sock.sendall(b'GET /file.txt HTTP/1.1\r\nHost: example.com\r\n\r\n')

# 3. Receive response
response = sock.recv(4096)
# "HTTP/1.1 200 OK\r\n...headers...\r\n\r\n[file data]"

# 4. Close
sock.close()
```

**One socket. Send request. Get response. Done.**

---

#### FTP (What We Built):

```python
import socket

# CONTROL CONNECTION
control = socket.socket()
control.connect(('ftp.example.com', 21))

# Receive welcome
welcome = control.recv(4096)  # "220 Ready"

# Login
control.sendall(b'USER alice\r\n')
response = control.recv(4096)  # "331 Need password"

control.sendall(b'PASS secret123\r\n')
response = control.recv(4096)  # "230 Login OK"

# Request passive mode
control.sendall(b'EPSV\r\n')
response = control.recv(4096)  # "229 Extended Passive Mode (|||12345|)"

# Parse port number
port = 12345  # Extracted from response

# DATA CONNECTION
data = socket.socket()
data.connect(('ftp.example.com', port))

# Request file on CONTROL
control.sendall(b'RETR file.txt\r\n')
response = control.recv(4096)  # "150 Sending..."

# Receive file on DATA
file_bytes = b''
while True:
    chunk = data.recv(8192)
    if not chunk:  # Connection closed = done
        break
    file_bytes += chunk

data.close()

# Confirm on CONTROL
response = control.recv(4096)  # "226 Transfer complete"

# Quit
control.sendall(b'QUIT\r\n')
response = control.recv(4096)  # "221 Goodbye"

control.close()
```

**Two sockets. Multiple steps. More complex.**

---

## Multi-line Responses (Like HTTP Headers, But Weirder)

### HTTP Headers (Multi-line)

```http
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 1234
Set-Cookie: session=abc123

[body]
```

**Format:** Each line is separate. Empty line signals end of headers.

---

### FTP Multi-line Responses

```
230-Welcome to FTP Server!
230-Please read the rules.
230-No illegal content allowed.
230 Login successful.
```

**Format:**
- First line: `230-Message` (hyphen = more coming)
- Middle lines: `230-More messages`
- Last line: `230 Final message` (space = done)

**How to parse:**

```python
# HTTP way: Read until you see "\r\n\r\n"
# FTP way: Read until you see "XXX " (code + space)

def read_ftp_response(sock):
    response = b''
    
    while True:
        chunk = sock.recv(4096)
        response += chunk
        
        lines = response.decode('utf-8').split('\n')
        last_line = lines[-1]
        
        # Check if final line (has space after code)
        if len(last_line) >= 4 and last_line[3] == ' ':
            break
    
    return response.decode('utf-8')
```

---

## Binary vs ASCII Mode (FTP-Specific Concept)

### HTTP (Always Binary)

```http
GET /image.jpg HTTP/1.1

HTTP/1.1 200 OK
Content-Type: image/jpeg

[exact bytes of JPEG file]
```

HTTP sends bytes exactly as-is. No conversion.

---

### FTP (Two Modes)

**Binary Mode (TYPE I):**
```
CLIENT: TYPE I
SERVER: 200 Type set to I

CLIENT: RETR image.jpg
[Receives exact bytes, like HTTP]
```

**ASCII Mode (TYPE A):**
```
CLIENT: TYPE A
SERVER: 200 Type set to A

CLIENT: RETR readme.txt
[Server converts line endings]

Windows file: "Hello\r\nWorld\r\n"
Unix file: "Hello\nWorld\n"

FTP can convert between them!
```

**When to use:**
- **Binary (TYPE I):** Images, videos, executables, archives → ALWAYS use this
- **ASCII (TYPE A):** Text files where line endings matter → Rarely needed now

**Our code always uses binary:**
```python
self.connection.send_command("TYPE I")
```

---

## REST API vs FTP Commands

If you've built REST APIs, FTP commands will feel familiar:

### REST API

```http
POST /api/auth/login
{"username": "alice", "password": "secret"}

GET /api/files/list?path=/documents

GET /api/files/download/report.pdf

POST /api/files/upload
[file data in multipart form]
```

---

### FTP Commands

```
USER alice
PASS secret

LIST /documents

RETR report.pdf

STOR uploaded_file.pdf
```

**Same concepts, different syntax.**

| REST API | FTP Command | Purpose |
|----------|-------------|---------|
| POST /auth/login | USER + PASS | Authenticate |
| GET /files/list | LIST | Get directory listing |
| GET /files/:id | RETR filename | Download file |
| POST /files | STOR filename | Upload file |
| GET /current-dir | PWD | Get current path |
| POST /change-dir | CWD /path | Change directory |

---

## Why FTP is Harder Than HTTP

### HTTP Advantages:
✅ One connection = simpler
✅ Stateless = each request independent
✅ Firewall-friendly (single port)
✅ Built-in encryption (HTTPS)
✅ Human-readable headers

### FTP Disadvantages:
❌ Two connections = complex
❌ Stateful = must track login, current directory
❌ Firewall nightmare (random ports)
❌ No built-in encryption (need FTPS)
❌ Weird response format

**This is why modern apps use:**
- **HTTPS** for downloads (simpler)
- **SFTP** for file management (secure, one connection via SSH)
- **S3/Cloud APIs** for storage (better than both)

---

## Summary for HTTP Developers

If you know HTTP, think of FTP as:

1. **HTTP with separate control + data sockets**
   - Control = your HTTP request/response
   - Data = the file download stream

2. **Stateful HTTP**
   - Must login once
   - Stay logged in
   - Track current directory

3. **Status codes like HTTP**
   - 2xx = success
   - 4xx/5xx = errors
   - But format is different (3 digits + message, not headers)

4. **Multi-step requests**
   ```
   HTTP:  Request → Response (1 step)
   FTP:   PASV → RETR → Data → Complete (4 steps)
   ```

5. **Text protocol like HTTP/1.1**
   - Commands are human-readable text
   - Responses are human-readable text
   - Data can be binary or text

---