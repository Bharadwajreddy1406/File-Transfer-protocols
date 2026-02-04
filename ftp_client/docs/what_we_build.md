# Plan to be followed

```
What We're Building (Full Project):

1. FTP CLIENT ← (We're here, authentication done)
   ├── Connect ✓
   ├── Login ✓
   ├── List files (next)
   ├── Download files (after that)
   ├── Upload files (after that)
   └── Handle errors (ongoing)

2. FTP SERVER (much later)
   ├── Listen for connections
   ├── Authenticate users
   ├── Serve files
   └── Accept uploads

3. SFTP CLIENT (after FTP)
4. HTTP Transfer (after SFTP)
5. rsync (after HTTP)
... etc

```