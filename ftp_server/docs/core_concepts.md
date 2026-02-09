

## We need FTP Session State
### here's why 

Because FTP is stateful.

For each connected client, server must store:

FTP Session State:

is_authenticated

username

current_directory

passive_socket

data_socket

So we’ll build a FTPSession object.



---

We must implement in a sequence that matches how FTP clients behave.

Phase 1 (Control connection only)
Mandatory responses:
```
220 Welcome

USER

PASS

SYST

PWD

CWD

QUIT
```