# Complete Guide to FTP Commands

## Command Categories

FTP commands fall into these groups:

1. **Access Control** - Login and permissions
2. **Transfer Parameters** - How to send data
3. **File Actions** - Upload, download, delete
4. **Directory Navigation** - Move around, list files
5. **Informational** - Get status, help
6. **Connection Management** - Setup, teardown

---

## 1. Access Control Commands

### USER - Send Username

**Syntax:** `USER <username>`

**What it does:** Identifies you to the server

**Example:**
```
CLIENT: USER alice
SERVER: 331 User name okay, need password
```

**Response codes:**
- `230` - User logged in (no password needed - rare)
- `331` - User name okay, need password (normal)
- `530` - Not logged in (invalid username)

**When to use:**
- First command after connecting
- Before you can do anything else

**Real-world example:**
```python
client.connection.send_command("USER anonymous")
# Response: "331 Please specify the password."
```

**Special username: `anonymous`**
- Used for public FTP servers
- No real password needed (convention: use your email)
- Limited permissions (usually read-only)

---

### PASS - Send Password

**Syntax:** `PASS <password>`

**What it does:** Authenticates your username

**Example:**
```
CLIENT: PASS secret123
SERVER: 230 Login successful
```

**Response codes:**
- `230` - Login successful
- `530` - Login incorrect (wrong password)
- `332` - Need account for login (rare)

**When to use:**
- Right after `USER` command returns `331`

**Security warning:**
```
⚠️ PASSWORD IS SENT IN PLAIN TEXT!

Anyone sniffing network traffic can see:
"PASS secret123\r\n"

This is why FTPS (FTP over TLS) exists.
```

**Real-world example:**
```python
client.connection.send_command("PASS mypassword")
# Response: "230 User alice logged in."
```

---

### ACCT - Account Information

**Syntax:** `ACCT <account>`

**What it does:** Some servers require an account code after login

**Example:**
```
CLIENT: ACCT billing_dept
SERVER: 230 Account accepted
```

**When to use:**
- Rarely! Most modern servers don't use this
- Only if server responds `332 Need account for login`

**Response codes:**
- `230` - Account accepted
- `530` - Not accepted

---

### REIN - Reinitialize Connection

**Syntax:** `REIN`

**What it does:** Logs you out but keeps connection open

**Example:**
```
CLIENT: REIN
SERVER: 220 Service ready for new user
```

**When to use:**
- Want to login as different user without reconnecting
- Rarely used in practice (easier to just reconnect)

---

### QUIT - Logout and Disconnect

**Syntax:** `QUIT`

**What it does:** Closes both control and data connections

**Example:**
```
CLIENT: QUIT
SERVER: 221 Goodbye
[Server closes connection]
```

**Response codes:**
- `221` - Service closing control connection

**When to use:**
- Always! Don't just close socket without QUIT
- Lets server clean up properly

**Real-world example:**
```python
def quit(self):
    self.connection.send_command("QUIT")
    # Response: "221 Goodbye"
    self.connection.close()
```

---

## 2. Transfer Parameter Commands

These commands configure HOW data will be transferred.

### TYPE - Set Transfer Type

**Syntax:** `TYPE <type-code>`

**Type codes:**
- `A` - ASCII (text mode)
- `I` - Image/Binary mode
- `E` - EBCDIC (ancient, ignore)
- `L 8` - Local byte size (rarely used)

**What it does:** Tells server how to send data

**Examples:**

**Binary Mode (recommended for everything):**
```
CLIENT: TYPE I
SERVER: 200 Type set to I
```

**ASCII Mode (for text files):**
```
CLIENT: TYPE A
SERVER: 200 Type set to A
```

**When to use:**
- **TYPE I (binary):** Images, videos, executables, archives, PDFs - 99% of the time
- **TYPE A (ASCII):** Plain text files where you want line-ending conversion

**What ASCII mode does:**
```
Windows file: "Hello\r\nWorld\r\n"
Unix file:    "Hello\nWorld\n"

Transfer Windows → Unix in ASCII mode:
Server automatically converts \r\n → \n

Transfer in Binary mode:
Bytes sent exactly as-is (what you want!)
```

**Real-world example:**
```python
# Always set binary mode before downloading
self.connection.send_command("TYPE I")

# Now download
self.connection.send_command("RETR image.jpg")
```

---

### MODE - Set Transfer Mode

**Syntax:** `MODE <mode-code>`

**Mode codes:**
- `S` - Stream (default, normal mode)
- `B` - Block (rare)
- `C` - Compressed (rare)

**What it does:** How data is structured during transfer

**Example:**
```
CLIENT: MODE S
SERVER: 200 Mode set to S
```

**When to use:**
- Almost never! Stream mode (S) is default and works fine
- Block and Compressed modes are barely supported

---

### STRU - File Structure

**Syntax:** `STRU <structure-code>`

**Structure codes:**
- `F` - File (normal, stream of bytes)
- `R` - Record (mainframe stuff)
- `P` - Page (ancient)

**What it does:** Defines file structure

**Example:**
```
CLIENT: STRU F
SERVER: 200 Structure set to F
```

**When to use:**
- Never in modern FTP! Always File structure

---

### PASV - Enter Passive Mode

**Syntax:** `PASV`

**What it does:** Server opens a port and tells you to connect

**Example:**
```
CLIENT: PASV
SERVER: 227 Entering Passive Mode (209,51,188,20,234,10)
```

**Parsing the response:**
```
227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)

IP address: h1.h2.h3.h4
Port: (p1 × 256) + p2

Example: (209,51,188,20,234,10)
IP: 209.51.188.20
Port: (234 × 256) + 10 = 59,914
```

**When to use:**
- Before every data transfer (LIST, RETR, STOR)
- Required when you're behind NAT/firewall

**Real-world flow:**
```python
# 1. Request passive mode
response = self.connection.send_command("PASV")
# "227 Entering Passive Mode (209,51,188,20,234,10)"

# 2. Parse IP and port
host, port = self._parse_pasv_response(response)
# host = "209.51.188.20", port = 59914

# 3. Open data connection
data_conn = FTPConnection(host, port)
data_conn.connect()

# 4. Now send file command
self.connection.send_command("RETR file.txt")
```

---

### EPSV - Extended Passive Mode

**Syntax:** `EPSV` or `EPSV <protocol>`

**What it does:** Like PASV but simpler, IPv6-friendly

**Example:**
```
CLIENT: EPSV
SERVER: 229 Extended Passive Mode Entered (|||59914|)
```

**Parsing the response:**
```
229 Extended Passive Mode Entered (|||port|)

Port: Just extract the number
IP: Use same as control connection

Example: (|||59914|)
Port: 59914
IP: Same as server's IP
```

**When to use:**
- Modern replacement for PASV
- Automatically handles IPv4 and IPv6
- Most servers support this now

**Comparison:**

| PASV | EPSV |
|------|------|
| `227 (209,51,188,20,234,10)` | `229 (|||59914|)` |
| Gives IP + port | Gives port only |
| IPv4 only | IPv4 + IPv6 |
| Complex parsing | Simple parsing |

**Real-world example:**
```python
# Try EPSV first (modern)
response = self.connection.send_command("EPSV")

if response.startswith('229'):
    # Extract port from (|||59914|)
    port = int(re.search(r'\|\|\|(\d+)\|', response).group(1))
    host = self.host  # Same as control connection
else:
    # Fall back to PASV
    response = self.connection.send_command("PASV")
    # Parse old format...
```

---

### PORT - Active Mode (Rarely Used)

**Syntax:** `PORT h1,h2,h3,h4,p1,p2`

**What it does:** YOU open a port, server connects to YOU

**Example:**
```
CLIENT: PORT 192,168,1,100,195,10
SERVER: 200 PORT command successful

[Server opens connection to 192.168.1.100:49930]
```

**When to use:**
- Almost never!
- Doesn't work behind NAT/firewall
- Use PASV/EPSV instead

**Why it exists:**
- Original FTP design (1971)
- Back then, no NAT existed
- Servers were trusted to connect to clients

---

## 3. File Action Commands

### RETR - Download File

**Syntax:** `RETR <filename>`

**What it does:** Download a file from server

**Example:**
```
[After PASV and opening data connection]

CLIENT: RETR report.pdf
SERVER: 150 Opening BINARY mode data connection for report.pdf (50000 bytes)

[Data flows on data connection]

SERVER: 226 Transfer complete
```

**Response codes:**
- `150`/`125` - Transfer starting
- `226` - Transfer complete
- `550` - File not found
- `450` - File unavailable (busy)

**Complete flow:**
```
1. TYPE I                    → "200 Type set to binary"
2. EPSV                      → "229 (|||12345|)"
3. [Open data connection to port 12345]
4. RETR report.pdf           → "150 Sending file..."
5. [Read bytes from data connection]
6. [Data connection closes]
7. [Control responds]        ← "226 Transfer complete"
```

**Real-world example:**
```python
def download_file(self, filename):
    # Set binary mode
    self.connection.send_command("TYPE I")
    
    # Open data connection
    data_conn = self._open_data_connection()
    
    # Request file
    response = self.connection.send_command(f"RETR {filename}")
    
    if not response.startswith('150'):
        if response.startswith('550'):
            raise FileNotFoundError(f"File not found: {filename}")
        else:
            raise Exception(f"RETR failed: {response}")
    
    # Read file data
    file_data = b''
    while True:
        chunk = data_conn.sock.recv(8192)
        if not chunk:
            break
        file_data += chunk
    
    # Close data connection
    data_conn.close()
    
    # Read completion
    completion = self.connection._read_response()
    # "226 Transfer complete"
    
    return file_data
```

---

### STOR - Upload File

**Syntax:** `STOR <filename>`

**What it does:** Upload a file to server

**Example:**
```
[After PASV and opening data connection]

CLIENT: STOR upload.zip
SERVER: 150 Ok to send data

[Client sends file bytes on data connection]
[Client closes data connection]

SERVER: 226 Transfer complete
```

**Response codes:**
- `150`/`125` - Ready to receive
- `226` - Transfer complete
- `550` - Permission denied
- `553` - Filename not allowed

**Complete flow:**
```
1. TYPE I                    → "200 Type set to binary"
2. EPSV                      → "229 (|||12345|)"
3. [Open data connection to port 12345]
4. STOR upload.zip           → "150 Ready to receive"
5. [Write bytes to data connection]
6. [Close data connection = signal upload complete]
7. [Control responds]        ← "226 Transfer complete"
```

**Real-world example:**
```python
def upload_file(self, local_file, remote_name):
    # Read local file
    with open(local_file, 'rb') as f:
        file_data = f.read()
    
    # Set binary mode
    self.connection.send_command("TYPE I")
    
    # Open data connection
    data_conn = self._open_data_connection()
    
    # Tell server we're uploading
    response = self.connection.send_command(f"STOR {remote_name}")
    
    if not response.startswith('150'):
        raise Exception(f"STOR failed: {response}")
    
    # Send file data
    data_conn.sock.sendall(file_data)
    
    # Close data connection (signals upload complete)
    data_conn.close()
    
    # Read completion
    completion = self.connection._read_response()
    # "226 Transfer complete"
```

---

### APPE - Append to File

**Syntax:** `APPE <filename>`

**What it does:** Upload data and append to existing file

**Example:**
```
CLIENT: APPE logfile.txt
SERVER: 150 Ok to send data

[Client sends data]

SERVER: 226 Transfer complete
```

**When to use:**
- Adding to log files
- Resuming partial uploads
- Appending data without overwriting

**Difference from STOR:**
- `STOR` - Overwrites or creates new file
- `APPE` - Adds to end of existing file

---

### DELE - Delete File

**Syntax:** `DELE <filename>`

**What it does:** Deletes a file on the server

**Example:**
```
CLIENT: DELE old_file.txt
SERVER: 250 File deleted
```

**Response codes:**
- `250` - File deleted successfully
- `550` - Permission denied or file not found
- `450` - File unavailable (locked)

**When to use:**
- Cleaning up after processing
- Removing temporary files

**Real-world example:**
```python
def delete_file(self, filename):
    response = self.connection.send_command(f"DELE {filename}")
    
    if response.startswith('250'):
        return True
    elif response.startswith('550'):
        raise Exception(f"Cannot delete {filename}: Permission denied or not found")
    else:
        raise Exception(f"DELE failed: {response}")
```

---

### RNFR & RNTO - Rename File

**Syntax:** 
```
RNFR <old-filename>
RNTO <new-filename>
```

**What it does:** Renames or moves a file (two-step process)

**Example:**
```
CLIENT: RNFR old_name.txt
SERVER: 350 File exists, ready for destination name

CLIENT: RNTO new_name.txt
SERVER: 250 Rename successful
```

**Why two commands?**
- RNFR = "Rename From" - Selects the file
- RNTO = "Rename To" - Specifies new name
- Must use both in sequence

**Response codes:**
- RNFR `350` - Ready for RNTO
- RNFR `550` - File not found
- RNTO `250` - Rename successful
- RNTO `553` - Destination name not allowed

**Real-world example:**
```python
def rename_file(self, old_name, new_name):
    # Step 1: Select file
    response = self.connection.send_command(f"RNFR {old_name}")
    
    if not response.startswith('350'):
        raise Exception(f"File not found: {old_name}")
    
    # Step 2: Specify new name
    response = self.connection.send_command(f"RNTO {new_name}")
    
    if response.startswith('250'):
        return True
    else:
        raise Exception(f"Rename failed: {response}")
```

**Tip:** Can also use RNFR/RNTO to move files between directories:
```
RNFR /folder1/file.txt
RNTO /folder2/file.txt
```

---

### REST - Restart Transfer

**Syntax:** `REST <byte-position>`

**What it does:** Resume a transfer from specific byte position

**Example:**
```
CLIENT: REST 500000
SERVER: 350 Restarting at 500000

CLIENT: RETR large_file.zip
SERVER: 150 Sending from byte 500000

[Sends bytes starting at position 500000]
```

**When to use:**
- Resuming interrupted downloads
- Downloading large files in chunks
- Avoiding re-downloading entire file after network failure

**Complete resume flow:**
```
# First attempt (fails at 500KB):
RETR large.zip → Downloaded 500,000 bytes → [Connection drops]

# Resume:
1. REST 500000        → "350 Restarting at 500000"
2. RETR large.zip     → "150 Sending from byte 500000"
3. [Receive remaining bytes]
4. [Combine: first_500KB + new_bytes = complete_file]
```

**Response codes:**
- `350` - Restart position accepted
- `554` - Feature not implemented (server doesn't support resume)

**Real-world example:**
```python
def download_file_with_resume(self, filename, local_file):
    # Check if partial file exists
    start_pos = 0
    if os.path.exists(local_file):
        start_pos = os.path.getsize(local_file)
        print(f"Resuming from byte {start_pos}")
        
        # Tell server to start from this position
        response = self.connection.send_command(f"REST {start_pos}")
        
        if not response.startswith('350'):
            print("Resume not supported, downloading from start")
            start_pos = 0
    
    # Open data connection
    data_conn = self._open_data_connection()
    
    # Request file
    self.connection.send_command(f"RETR {filename}")
    
    # Append to existing file or create new
    mode = 'ab' if start_pos > 0 else 'wb'
    with open(local_file, mode) as f:
        while True:
            chunk = data_conn.sock.recv(8192)
            if not chunk:
                break
            f.write(chunk)
```

---

## 4. Directory Navigation Commands

### PWD - Print Working Directory

**Syntax:** `PWD`

**What it does:** Returns current directory path

**Example:**
```
CLIENT: PWD
SERVER: 257 "/home/alice/documents" is current directory
```

**Response format:**
```
257 "<path>" is current directory
     ^^^^^^ Path is in quotes
```

**Response codes:**
- `257` - Path returned

**Parsing:**
```python
def pwd(self):
    response = self.connection.send_command("PWD")
    
    # Extract path from quotes
    match = re.search(r'"([^"]+)"', response)
    if match:
        return match.group(1)  # Returns: "/home/alice/documents"
```

**When to use:**
- Check where you are before changing directories
- Verify navigation worked
- Display current location to user

---

### CWD - Change Working Directory

**Syntax:** `CWD <directory>`

**What it does:** Navigate to a different directory

**Examples:**

**Absolute path:**
```
CLIENT: CWD /home/alice/documents
SERVER: 250 Directory successfully changed
```

**Relative path:**
```
CLIENT: CWD reports
SERVER: 250 Directory successfully changed
```

**Go up:**
```
CLIENT: CWD ..
SERVER: 250 Directory successfully changed
```

**Response codes:**
- `250` - Success
- `550` - Directory not found or no permission

**Real-world example:**
```python
def cwd(self, path):
    response = self.connection.send_command(f"CWD {path}")
    
    if response.startswith('250'):
        return True
    elif response.startswith('550'):
        raise Exception(f"Cannot change to {path}: Not found or no permission")
    else:
        return False
```

**Tip:** After CWD, all file operations use the new directory:
```
CWD /documents
RETR report.pdf    ← Downloads /documents/report.pdf
```

---

### CDUP - Change to Parent Directory

**Syntax:** `CDUP`

**What it does:** Go up one directory level (shortcut for `CWD ..`)

**Example:**
```
[Currently in: /home/alice/documents]

CLIENT: CDUP
SERVER: 250 Directory successfully changed

[Now in: /home/alice]
```

**Response codes:**
- `250` - Success
- `550` - Already at root or no permission

**When to use:**
- Navigating up directory tree
- Returning to parent after browsing subdirectory

**Equivalent commands:**
```
CDUP        ← Shortcut
CWD ..      ← Same thing
```

---

### MKD - Make Directory

**Syntax:** `MKD <directory-name>`

**What it does:** Creates a new directory

**Example:**
```
CLIENT: MKD new_folder
SERVER: 257 "/home/alice/new_folder" created
```

**Response codes:**
- `257` - Directory created
- `550` - Permission denied or already exists

**Real-world example:**
```python
def mkdir(self, dirname):
    response = self.connection.send_command(f"MKD {dirname}")
    
    if response.startswith('257'):
        # Extract created path from response
        match = re.search(r'"([^"]+)"', response)
        if match:
            created_path = match.group(1)
            print(f"Created: {created_path}")
            return created_path
    else:
        raise Exception(f"Cannot create {dirname}: {response}")
```

---

### RMD - Remove Directory

**Syntax:** `RMD <directory-name>`

**What it does:** Deletes an empty directory

**Example:**
```
CLIENT: RMD old_folder
SERVER: 250 Directory deleted
```

**Response codes:**
- `250` - Directory deleted
- `550` - Not empty, not found, or no permission

**Important:** Directory must be empty!
```
RMD folder_with_files → 550 Directory not empty

# Must delete files first:
DELE folder/file1.txt
DELE folder/file2.txt
RMD folder → 250 Success
```

---

### LIST - List Directory

**Syntax:** `LIST [path]`

**What it does:** Returns detailed directory listing (like `ls -l`)

**Example:**
```
[After PASV and opening data connection]

CLIENT: LIST
SERVER: 150 Here comes the directory listing

[Data connection receives:]
drwxr-xr-x   2 alice  staff    4096 Jan 15 12:00 documents
-rw-r--r--   1 alice  staff   50000 Jan 20 14:30 report.pdf
lrwxrwxrwx   1 alice  staff       8 Jan 10 09:00 link -> documents

SERVER: 226 Directory send OK
```

**Format (Unix-style):**
```
drwxr-xr-x   2 alice  staff    4096 Jan 15 12:00 documents
│││││││││    │   │      │       │      │          │
│││││││││    │   │      │       │      │          └─ Filename
│││││││││    │   │      │       │      └─ Modified date/time
│││││││││    │   │      │       └─ Size in bytes
│││││││││    │   │      └─ Group
│││││││││    │   └─ Owner
│││││││││    └─ Number of links
│││││││└─ Execute permission (others)
││││││└─ Write permission (others)
│││││└─ Read permission (others)
││││└─ Execute permission (group)
│││└─ Write permission (group)
││└─ Read permission (group)
│└─ Execute permission (owner)
└─ Write permission (owner)
Read permission (owner)

First character:
- = Regular file
d = Directory
l = Symbolic link
```

**Response codes:**
- `150`/`125` - Listing starting
- `226` - Listing complete
- `550` - Directory not found

**When to use:**
- Browsing server contents
- Checking file sizes/dates
- Verifying uploads

**Real-world example:**
```python
def list_files(self, path='.'):
    data_conn = self._open_data_connection()
    
    response = self.connection.send_command(f"LIST {path}")
    
    # Read listing from data connection
    listing = b''
    while True:
        chunk = data_conn.sock.recv(4096)
        if not chunk:
            break
        listing += chunk
    
    data_conn.close()
    
    # Get completion
    self.connection._read_response()  # "226 Transfer complete"
    
    return listing.decode('utf-8')
```

**Parsing LIST output:**
```python
def parse_list_line(line):
    # Example: "drwxr-xr-x   2 alice  staff    4096 Jan 15 12:00 documents"
    parts = line.split()
    
    return {
        'permissions': parts[0],
        'is_dir': parts[0].startswith('d'),
        'owner': parts[2],
        'group': parts[3],
        'size': int(parts[4]),
        'name': ' '.join(parts[8:])  # Filename might have spaces
    }
```

---

### NLST - Name List

**Syntax:** `NLST [path]`

**What it does:** Returns simple list of filenames only (like `ls`)

**Example:**
```
CLIENT: NLST
SERVER: 150 Here comes the directory listing

[Data connection receives:]
documents
report.pdf
archive.zip

SERVER: 226 Directory send OK
```

**Difference from LIST:**

| LIST | NLST |
|------|------|
| Full details | Names only |
| `drwxr-xr-x 2 alice staff 4096 Jan 15 documents` | `documents` |
| Like `ls -l` | Like `ls` |

**When to use:**
- Just need filenames
- Easier to parse than LIST
- Faster (less data)

**Real-world example:**
```python
def get_filenames(self):
    data_conn = self._open_data_connection()
    
    self.connection.send_command("NLST")
    
    listing = b''
    while True:
        chunk = data_conn.sock.recv(4096)
        if not chunk:
            break
        listing += chunk
    
    data_conn.close()
    self.connection._read_response()
    
    # Parse simple list
    filenames = listing.decode('utf-8').strip().split('\n')
    return filenames
```

---

### MLSD - Machine-Readable Directory List

**Syntax:** `MLSD [path]`

**What it does:** Returns standardized, parseable directory listing

**Example:**
```
CLIENT: MLSD
SERVER: 150 Here comes the directory listing

[Data connection receives:]
type=dir;modify=20240115120000;perm=el; documents
type=file;size=50000;modify=20240120143000; report.pdf
type=file;size=1234567;modify=20240118100000; archive.zip

SERVER: 226 Directory send OK
```

**Format:**
```
type=<type>;size=<bytes>;modify=<timestamp>;perm=<perms>; <filename>

type=file    - Regular file
type=dir     - Directory
type=cdir    - Current directory (.)
type=pdir    - Parent directory (..)

modify=20240115120000 = 2024-01-15 12:00:00

perm=r  - Read
perm=w  - Write
perm=d  - Delete
perm=el - Enter directory / List files
```

**Advantages over LIST:**
- Standardized format (LIST varies by server)
- Machine-readable (easy to parse)
- Includes timestamp in consistent format

**When to use:**
- Modern FTP clients
- When you need reliable parsing
- If server supports it (not all do)

**Checking support:**
```
CLIENT: FEAT
SERVER: 211-Features:
 MLSD
 MLST
 ...
211 End
```

**Real-world example:**
```python
def mlsd(self, path='.'):
    # Check if supported
    feat_response = self.connection.send_command("FEAT")
    if 'MLSD' not in feat_response:
        raise Exception("Server doesn't support MLSD")
    
    data_conn = self._open_data_connection()
    self.connection.send_command(f"MLSD {path}")
    
    listing = b''
    while True:
        chunk = data_conn.sock.recv(4096)
        if not chunk:
            break
        listing += chunk
    
    data_conn.close()
    self.connection._read_response()
    
    # Parse
    files = []
    for line in listing.decode('utf-8').strip().split('\n'):
        facts, filename = line.rsplit(' ', 1)
        
        info = {}
        for fact in facts.split(';'):
            if '=' in fact:
                key, value = fact.split('=')
                info[key] = value
        
        files.append({
            'name': filename,
            'type': info.get('type'),
            'size': int(info.get('size', 0)),
            'modified': info.get('modify')
        })
    
    return files
```

---

## 5. Informational Commands

### STAT - Status

**Syntax:** `STAT [path]`

**What it does:** Returns server status or file info

**Without argument (server status):**
```
CLIENT: STAT
SERVER: 211-FTP server status:
     Connected to 192.168.1.100
     Logged in as alice
     TYPE: BINARY
     No data connection
211 End of status
```

**With path (file info):**
```
CLIENT: STAT report.pdf
SERVER: 213-Status of report.pdf:
     -rw-r--r--   1 alice  staff   50000 Jan 20 14:30 report.pdf
213 End
```

**When to use:**
- Check connection status
- Quick file info without opening data connection
- Debugging connection issues

---

### SYST - System Type

**Syntax:** `SYST`

**What it does:** Returns server operating system type

**Example:**
```
CLIENT: SYST
SERVER: 215 UNIX Type: L8
```

**Common responses:**
- `215 UNIX Type: L8` - Unix/Linux server
- `215 Windows_NT` - Windows server
- `215 VMS` - OpenVMS system

**When to use:**
- Determining file path format (/ vs \)
- Adjusting LIST parsing for server type
- Feature detection

---

### HELP - Get Help

**Syntax:** `HELP [command]`

**What it does:** Returns available commands or help for specific command

**Example:**
```
CLIENT: HELP
SERVER: 214-The following commands are recognized:
     USER PASS QUIT CWD PWD LIST RETR STOR
     DELE MKD RMD RNFR RNTO TYPE MODE STRU
     PASV PORT REST STAT SYST HELP NOOP
214 Help OK

CLIENT: HELP RETR
SERVER: 214 Syntax: RETR <filename>
```

**When to use:**
- Discovering server capabilities
- Learning command syntax
- Debugging

---

### FEAT - List Features

**Syntax:** `FEAT`

**What it does:** Returns list of extended features server supports

**Example:**
```
CLIENT: FEAT
SERVER: 211-Features:
 MLSD
 MLST type*;size*;modify*;
 REST STREAM
 SIZE
 TVFS
 UTF8
 MDTM
211 End
```

**When to use:**
- Before using modern commands (MLSD, SIZE, etc.)
- Feature detection
- Capability negotiation

**Real-world example:**
```python
def get_features(self):
    response = self.connection.send_command("FEAT")
    
    features = []
    for line in response.split('\n'):
        line = line.strip()
        if line and not line.startswith('211'):
            features.append(line)
    
    return features

# Usage:
features = client.get_features()
if 'MLSD' in features:
    # Use machine-readable listing
    client.mlsd()
else:
    # Fall back to LIST
    client.list_files()
```

---

### SIZE - Get File Size

**Syntax:** `SIZE <filename>`

**What it does:** Returns file size in bytes (without downloading)

**Example:**
```
CLIENT: SIZE report.pdf
SERVER: 213 50000
```

**Response codes:**
- `213 <size>` - File size in bytes
- `550` - File not found

**When to use:**
- Pre-allocating download buffer
- Showing download progress
- Checking if file changed

**Real-world example:**
```python
def get_file_size(self, filename):
    response = self.connection.send_command(f"SIZE {filename}")
    
    if response.startswith('213'):
        size = int(response.split()[1])
        return size
    elif response.startswith('550'):
        raise FileNotFoundError(f"File not found: {filename}")
    else:
        raise Exception(f"SIZE failed: {response}")

# Usage with progress bar:
size = client.get_file_size('large.zip')
print(f"File size: {size:,} bytes")

# Download with progress
downloaded = 0
for chunk in download_chunks('large.zip'):
    downloaded += len(chunk)
    progress = (downloaded / size) * 100
    print(f"Progress: {progress:.1f}%")
```

---

### MDTM - Get Modification Time

**Syntax:** `MDTM <filename>`

**What it does:** Returns file's last modification timestamp

**Example:**
```
CLIENT: MDTM report.pdf
SERVER: 213 20240120143000
```

**Format:** `YYYYMMDDhhmmss` (UTC)
- `20240120143000` = 2024-01-20 14:30:00 UTC

**When to use:**
- Checking if remote file changed
- Synchronization (only download if newer)
- Timestamps for downloaded files

**Real-world example:**
```python
from datetime import datetime

def get_modification_time(self, filename):
    response = self.connection.send_command(f"MDTM {filename}")
    
    if response.startswith('213'):
        timestamp_str = response.split()[1]  # "20240120143000"
        
        # Parse timestamp
        dt = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
        return dt
    else:
        raise Exception(f"MDTM failed: {response}")

# Usage:
remote_time = client.get_modification_time('report.pdf')
local_time = datetime.fromtimestamp(os.path.getmtime('local_report.pdf'))

if remote_time > local_time:
    print("Remote file is newer, downloading...")
    client.download_file('report.pdf')
else:
    print("Local file is up to date")
```

---

### NOOP - No Operation

**Syntax:** `NOOP`

**What it does:** Does nothing, server responds with success

**Example:**
```
CLIENT: NOOP
SERVER: 200 NOOP ok
```

**When to use:**
- Keep-alive (prevent timeout)
- Testing if connection still works
- Maintaining control connection during long data transfer

**Real-world example:**
```python
import threading
import time

def keep_alive(client, interval=60):
    """Send NOOP every 60 seconds to prevent timeout"""
    while client.logged_in:
        time.sleep(interval)
        try:
            client.connection.send_command("NOOP")
        except:
            break

# Start keep-alive thread during long transfer
keep_alive_thread = threading.Thread(target=keep_alive, args=(client,))
keep_alive_thread.daemon = True
keep_alive_thread.start()

# Now do long-running operations
client.download_large_file('huge.zip')
```

---

## 6. Advanced/Rarely Used Commands

### ALLO - Allocate Space

**Syntax:** `ALLO <bytes>`

**What it does:** Asks server to reserve disk space before upload

**Example:**
```
CLIENT: ALLO 1000000
SERVER: 200 ALLO command successful
```

**When to use:**
- Almost never (modern filesystems handle this automatically)
- Some ancient systems required this

---

### SITE - Site-Specific Command

**Syntax:** `SITE <command>`

**What it does:** Server-specific commands (not standardized)

**Examples:**
```
CLIENT: SITE CHMOD 755 script.sh
SERVER: 200 Permissions changed

CLIENT: SITE HELP
SERVER: 214 Available SITE commands:
     CHMOD UTIME
214 End
```

**When to use:**
- Server has custom features
- Changing Unix permissions
- Server-specific administration

---

### SMNT - Structure Mount

**Syntax:** `SMNT <pathname>`

**What it does:** Mount a different file structure (ancient mainframe stuff)

**When to use:**
- Never (obsolete)

---

### ABOR - Abort Transfer

**Syntax:** `ABOR`

**What it does:** Cancels ongoing data transfer

**Example:**
```
[During file transfer]

CLIENT: ABOR
SERVER: 426 Transfer aborted
SERVER: 226 Abort successful
```

**When to use:**
- User cancels download/upload
- Error detected during transfer
- Timeout occurred

**Tricky part:** Must send on control connection while data transfer is in progress

---

## Command Summary by Use Case

### Basic Session
```
1. USER alice
2. PASS secret123
3. SYST (optional - check server type)
4. PWD (where am I?)
5. ... do work ...
6. QUIT
```

### Download File
```
1. TYPE I (binary mode)
2. SIZE filename (get size - optional)
3. EPSV (or PASV)
4. [Open data connection]
5. RETR filename
6. [Read data]
7. [Data connection closes]
```

### Upload File
```
1. TYPE I
2. EPSV (or PASV)
3. [Open data connection]
4. STOR filename
5. [Write data]
6. [Close data connection]
```

### Browse Directories
```
1. PWD (where am I?)
2. LIST (what's here?)
3. CWD subfolder (go into folder)
4. LIST (what's in subfolder?)
5. CDUP (go back up)
```

### Resume Download
```
1. SIZE filename (get total size)
2. [Check local file size: 500000 bytes]
3. TYPE I
4. REST 500000 (resume from here)
5. EPSV
6. RETR filename (continues from byte 500000)
```

---

## Common Command Sequences

### Check if File Exists
```python
try:
    size = client.get_file_size('file.txt')
    print(f"File exists, size: {size}")
except:
    print("File doesn't exist")
```

### Download Only If Newer
```python
remote_time = client.get_modification_time('file.txt')
if os.path.exists('file.txt'):
    local_time = datetime.fromtimestamp(os.path.getmtime('file.txt'))
    if remote_time <= local_time:
        print("Already have latest version")
        return

client.download_file('file.txt')
```

### Safe Upload (Check Space First)
```python
file_size = os.path.getsize('upload.zip')
client.connection.send_command(f"ALLO {file_size}")
client.upload_file('upload.zip')
```

### Recursive Directory Download
```python
def download_recursive(client, remote_path, local_path):
    # List remote directory
    files = client.mlsd(remote_path)
    
    for file_info in files:
        if file_info['type'] == 'dir':
            # Create local directory
            os.makedirs(os.path.join(local_path, file_info['name']), exist_ok=True)
            
            # Recurse into subdirectory
            client.cwd(file_info['name'])
            download_recursive(client, file_info['name'], os.path.join(local_path, file_info['name']))
            client.cdup()
        else:
            # Download file
            client.download_file(
                file_info['name'],
                os.path.join(local_path, file_info['name'])
            )
```

---
