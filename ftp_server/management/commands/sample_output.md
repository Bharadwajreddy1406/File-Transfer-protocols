### This is the sample output for the server management command

```shell
(venv) PS C:\Users\LENOVO\Desktop\FTPS> python .\manage.py ftp_server_run
============================================================
🚀 FTP Server running on 127.0.0.1:2121
📂 Root directory: server_storage
============================================================

[+] Client connected: ('127.0.0.1', 59605)
[SERVER] 220 Welcome to Django FTP Server
[CLIENT] USER anonymous
[SERVER] 331 Username OK, need password
[CLIENT] PASS guest@example.com
[SERVER] 230 Login successful
[CLIENT] EPSV
  [PASV] Listening on 127.0.0.1:59606
[SERVER] 229 Entering Extended Passive Mode (|||59606|)
[CLIENT] LIST .
[SERVER] 150 Opening data connection for directory listing
  [PASV] Waiting for client to connect...
  [PASV] Client connected from ('127.0.0.1', 59607)
  [PASV] Data connection closed
[SERVER] 226 Directory listing sent
[CLIENT] PWD
[SERVER] 257 "/" is the current directory
[CLIENT] QUIT
[SERVER] 221 Goodbye
[-] Client disconnected: ('127.0.0.1', 59605)

```