## what we are building

### Phase 1: Build FTP CLIENT

- Connects to existing servers
- Downloads/uploads files
- We are the user

```
┌─────────────┐                    ┌──────────────────┐
│   Our Code  │ ──connects to──>   │  ftp.gnu.org     │
│ (FTP Client)│                    │  (FTP Server)    │
│             │ <──talks back───   │                  │
│  Downloads  │                    │  Has files       │
│  files      │                    │  stored on disk  │
└─────────────┘                    └──────────────────┘
```

### Phase 2 (later): Build FTP SERVER

- Other people connect to us
- They download/upload files
- We are the host

```

┌─────────────┐                    ┌──────────────────┐
│ Other people│ ──connects to──>   │  Your Code       │
│ (any client)│                    │  (FTP Server)    │
│             │ <──talks back───   │                  │
│  Downloads  │                    │  Hosts files     │
│  from YOU   │                    │  on your disk    │
└─────────────┘                    └──────────────────┘

```