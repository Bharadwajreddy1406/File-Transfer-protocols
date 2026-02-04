## FTP Response Codes Cheat Sheet

```
COMMON CODES YOU'LL SEE:

2xx - Success
├── 200: Command okay
├── 220: Service ready (welcome message)
├── 221: Service closing (goodbye)
├── 230: User logged in
└── 250: Requested action okay

3xx - Need More Info
├── 331: Need password
└── 350: Pending further information

4xx - Temporary Failure
├── 421: Service not available
└── 450: File unavailable

5xx - Permanent Failure
├── 500: Command not understood
├── 530: Not logged in
└── 550: File not found
```


---
## Example Usage

When handling FTP responses in your code, you can check the response codes like this:

```python
response_code = user_response[:3]
if response_code == '230':
```

FTP responses look like:
```shell
"331 Please specify the password.\r\n"
 ^^^
 This is the code

```



## Why try/except/finally in quit()?

```python
try:
    # Try to send QUIT
except Exception as e:
    # Might fail if server already closed
finally:
    # ALWAYS close socket, no matter what


Some FTP servers close the connection when they see QUIT, before sending response. So `send_command()` might fail. That's okay - we're quitting anyway. The `finally` ensures we close our socket even if there's an error.

### 4. **What's with all the print statements?**

For learning! You can SEE the FTP conversation:
→ Sending: USER anonymous
← Server says: 331 Password required
→ Sending: PASS guest@example.com
← Server says: 230 Login successful

```