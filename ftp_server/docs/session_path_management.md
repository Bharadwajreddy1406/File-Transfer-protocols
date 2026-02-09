# This Document highlights the session path management in the FTP server.

FTP commands like:

* `CWD folder`
* `RETR file.txt`
* `STOR upload.zip`
* `LIST`

all work with **paths**.

But here’s the problem:

### FTP paths are *virtual*

Client thinks in terms of:

```
/pub/gnu/file.txt
```

But your server stores files in your local system like:

```
C:\Users\LENOVO\Desktop\FTPS\server_storage\pub\gnu\file.txt
```

So the server must convert:

✅ FTP path → real OS filesystem path

---

# ⚠️ The BIG Security Risk: Directory Traversal

If you don’t sanitize paths, an attacker can do:

```ftp
CWD ../../../../Windows/System32
RETR config/SAM
```

And suddenly your FTP server becomes a file-stealing machine.

So we must enforce:

> Client can never escape the FTP root directory.

That’s the whole reason behind the code.

---

# 📌 Explanation of the path code (line by line logic)

## 1️⃣ `root_dir = os.path.abspath(root_dir)`

```python
self.root_dir = os.path.abspath(root_dir)
```

### What it does:

It converts your FTP root directory into an absolute path.

Example:

```python
root_dir = "server_storage"
```

becomes:

```
C:\Users\LENOVO\Desktop\FTPS\server_storage
```

### Why it matters:

Absolute paths are consistent and safer for security checks.

---

## 2️⃣ `current_dir = "/"`

```python
self.current_dir = "/"
```

### Meaning:

This is the **FTP working directory**, not your Windows/Linux directory.

So if client does:

```
PWD
```

Server replies:

```
257 "/" is the current directory.
```

This is like Linux-style FTP paths.

---

# ⭐ The Main Function: `get_real_path()`

This is the most important part.

## Function goal:

Convert an FTP path into an OS-safe filesystem path.

Example:

### FTP path:

```
/pub/gnu/README
```

### OS path:

```
C:\...\server_storage\pub\gnu\README
```

---

## 3️⃣ Handling relative paths

```python
if not path.startswith("/"):
    if self.current_dir.endswith("/"):
        path = self.current_dir + path
    else:
        path = self.current_dir + "/" + path
```

### Why?

FTP supports both absolute and relative paths.

If current dir is:

```
/pub
```

And client sends:

```
CWD gnu
```

That means:

```
/pub/gnu
```

So we convert relative paths into absolute FTP-style paths.

---

## 4️⃣ Normalize the path (`os.path.normpath`)

```python
normalized = os.path.normpath(path).replace("\\", "/")
```

### What does `normpath()` do?

It simplifies paths:

| Input                  | Output              |
| ---------------------- | ------------------- |
| `/pub/gnu/../docs`     | `/pub/docs`         |
| `/pub//gnu///readme`   | `/pub/gnu/readme`   |
| `/../Windows/System32` | `/Windows/System32` |

### Why is this important?

Because traversal attacks use things like:

```
../../
```

`normpath()` resolves these.

---

## 5️⃣ Ensure it starts with `/`

```python
if not normalized.startswith("/"):
    normalized = "/" + normalized
```

Sometimes `normpath()` may remove leading `/` depending on OS behavior.

So we force consistency.

---

# 🔥 The Core Mapping Step: Joining root_dir with FTP path

```python
real_path = os.path.abspath(
    os.path.join(self.root_dir, normalized.lstrip("/"))
)
```

### What happens here?

Let’s say:

* `root_dir = C:\FTPS\server_storage`
* `normalized = /pub/gnu`

Then:

### Step A: `normalized.lstrip("/")`

```
pub/gnu
```

### Step B: join with root_dir

```
C:\FTPS\server_storage\pub\gnu
```

### Step C: `abspath()` again

This ensures it becomes fully resolved.

---

# 🛡️ The Most Important Security Check

```python
if not real_path.startswith(self.root_dir):
    raise PermissionError("Access denied: Path traversal attempt detected")
```

### Why is this critical?

Because even after normalization, attackers can try tricks.

Example attack:

If root_dir is:

```
C:\FTPS\server_storage
```

And user tries:

```
CWD ../../../../Windows/System32
```

After join + abspath, it becomes:

```
C:\Windows\System32
```

Now check:

Does it start with root_dir?

❌ No.

So we block it.

### This is the firewall gate of your FTP server.

---

# ⚠️ One subtle improvement (future-proofing)

On Windows, string checks can be tricky due to case-insensitivity:

* `C:\FTPS\server_storage`
* `c:\ftps\server_storage`

So later we can upgrade to:

```python
os.path.commonpath([real_path, self.root_dir]) == self.root_dir
```

That is the most correct security approach.

But your current check is totally fine for learning and local development.

---

# 🧩 `set_current_dir()` Explanation

```python
normalized = os.path.normpath(new_path).replace("\\", "/")
if not normalized.startswith("/"):
    normalized = "/" + normalized
self.current_dir = normalized
```

### What it does:

* cleans the FTP directory path
* stores it in a consistent format

So your server always stores working directory like:

```
/pub/gnu
```

not messy ones like:

```
pub//gnu/../gnu
```

---

# 🧹 `cleanup()` Explanation

```python
if self.passive_server_socket:
    self.passive_server_socket.close()
```

### Why?

In PASV mode, server opens a listening socket.

If the client disconnects and you don’t close it, you will get:

* port leaks
* stuck sockets
* "Address already in use" errors

So cleanup is mandatory.

---

# 🏁 Summary in One Clean Sentence

Your `get_real_path()` implementation ensures that **any FTP path the client sends is safely mapped into a real OS filesystem path, while preventing directory traversal attacks that could escape the FTP root directory.**

