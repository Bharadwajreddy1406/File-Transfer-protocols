## The Two-Connection Problem

### What We've Used So Far: CONTROL Connection

```
Your Client ←──────────────→ FTP Server
            Port 21
            (commands only)
```

Commands like USER, PASS, QUIT go through this connection.

### What We Need Now: DATA Connection

```
Your Client ←──────────────→ FTP Server
            Port 21 (control - commands)
            
Your Client ←──────────────→ FTP Server  
            Port ??? (data - actual files/listings)
```

**Why two connections?**
- Control connection: Stays open, sends commands
- Data connection: Opens temporarily for each file transfer, then closes

This is FTP's biggest design flaw (causes firewall/NAT nightmares).

---

## PASV Mode (Passive Mode)

There are two ways to open the data connection:

1. **PORT mode (active)**: Server connects to you - doesn't work behind firewalls
2. **PASV mode (passive)**: You connect to server - works everywhere ✓

We'll use PASV mode.

### How PASV Works:

```
1. Client → Server: "PASV" (I want to enter passive mode)
2. Server → Client: "227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)"
3. Client: Calculates port = (p1 * 256) + p2
4. Client → Server: Opens NEW connection to server:port
5. Client → Server (control): "LIST" (send me file listing)
6. Server → Client (data): Sends file listing over data connection
7. Data connection closes
```

---
