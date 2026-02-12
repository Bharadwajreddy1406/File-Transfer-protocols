### This is the sample output for the 
management command 

``` shell
(venv) PS C:\Users\LENOVO\Desktop\FTPS> python .\manage.py ftp_test --host '127.0.0.1' --port '2121'
============================================================
FTP CONNECTION TEST
============================================================
Host: 127.0.0.1
User: anonymous
============================================================

STEP 1: Connecting to server...

  [DEBUG] Attempting TCP connect to 127.0.0.1:2121...
  [DEBUG] TCP socket connected!
  [DEBUG] Reading welcome message from control connection...
  [DEBUG] Welcome received: 220 Welcome to Django FTP Server...
Server says: 220 Welcome to Django FTP Server

Connection established!

STEP 2: Logging in...


-> Sending: USER anonymous
<- Server says: 331 Username OK, need password
-> Password required, sending PASS command...
<- Server says: 230 Login successful
Login successful!

✓ LOGIN SUCCESSFUL!

STEP 2.5: Listing files...


-> Listing files in: .

-> Sending: EPSV (requesting extended passive mode)
<- Server says: 229 Entering Extended Passive Mode (|||59606|)
Using EPSV (Extended Passive Mode)
Data connection: 127.0.0.1:59606
  [DEBUG] Attempting TCP connect to 127.0.0.1:59606...
  [DEBUG] TCP socket connected!
  [DEBUG] Data connection ready (no welcome message)
Data connection established
-> Sending: LIST .
<- Server says: 150 Opening data connection for directory listing
Reading file listing from data connection...
<- Server says: 226 Directory listing sent
File listing received
Data connection closed

✓ FILE LISTING RECEIVED:

────────────────────────────────────────────────────────────
-rw-r--r--   1 ftp      ftp                 7 Feb 09 23:46 sample.txt
-rw-r--r--   1 ftp      ftp                89 Feb 09 23:46 test.c
────────────────────────────────────────────────────────────
STEP 2.6: Getting current directory...


→ Sending: PWD (print working directory)
← Server says: 257 "/" is the current directory
  Current directory: /

✓ CURRENT DIRECTORY: /

→ Sending: QUIT
<- Server says: 221 Goodbye
Disconnected cleanly
Socket closed

DISCONNECTED CLEANLY

============================================================
Test complete
============================================================
(venv) PS C:\Users\LENOVO\Desktop\FTPS> 

```
