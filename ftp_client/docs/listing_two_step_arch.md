## The Two-Connection Architecture (Visualized)

This is what just happened:
```
CONTROL CONNECTION (stays open entire session):
You:21 ←─────────────────→ Server:21
  "USER anonymous"     →
                       ← "230 Login successful"
  "EPSV"               →
                       ← "229 Use port 27546"
  "LIST ."             →
                       ← "150 Sending data..."
  [waiting...]
                       ← "226 Transfer complete"
  "QUIT"               →
                       ← "221 Goodbye"

DATA CONNECTION (opens/closes for each transfer):
You:random ←─────────→ Server:27546
  [opens connection]
                       ← [file listing data bytes]
  [server closes when done]
```

---

## Key Insights You Just Learned

### 1. **FTP Uses TWO Connections**
- **Control (port 21):** Commands and responses
- **Data (random port):** Actual file/listing data

### 2. **PASV/EPSV Mode**
- Server tells you which port to connect to
- You open the data connection TO the server
- Firewall-friendly (you initiate both connections)

### 3. **Multi-line Responses**
- Format: `"XXX-Message"` (more coming)
- Final: `"XXX Message"` (done)
- Must read until final line

### 4. **FTP Response Codes**
- `1xx`: Info, wait for another response
- `2xx`: Success
- `3xx`: Need more info
- `4xx`: Temporary error
- `5xx`: Permanent error

### 5. **Data Connection Lifecycle**
```
1. Send PASV/EPSV on control
2. Parse port from response
3. Open new socket to that port
4. Send command (LIST, RETR, etc.) on control
5. Read data from data socket
6. Data socket closes automatically
7. Control socket confirms completion
```

---

## What You Saw in the File Listing
```
drwxrwxr-x  326 0  3003  12288 Jan 21 19:58 gnu
-rw-rw-r--    1 0  3003 257944 Feb 04 14:50 find.txt.gz
```