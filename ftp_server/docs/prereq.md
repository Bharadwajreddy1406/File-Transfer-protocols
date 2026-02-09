## know about the docs in FTP client first

# Now
Most Important: We will run server on port 2121

Because port 21 requires admin privileges.

So clients can connect like:

```
client = FTPClient("127.0.0.1", port=2121)

```