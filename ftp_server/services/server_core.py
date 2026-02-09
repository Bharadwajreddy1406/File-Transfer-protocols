import socket
from .session import FTPSession


class FTPServer:


    def __init__(self, host="127.0.0.1", port=2121, root_dir="server_storage"):
        self.host = host
        self.port = port
        self.root_dir = root_dir
        self.server_socket = None

    def start(self):
        """
        Start listening for FTP clients.
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        print("=" * 60)
        print(f"🚀 FTP Server running on {self.host}:{self.port}")
        print(f"📂 Root directory: {self.root_dir}")
        print("=" * 60)

        while True:
            client_sock, client_addr = self.server_socket.accept()
            print(f"\n[+] Client connected: {client_addr}")

            session = FTPSession(client_sock, client_addr, self.root_dir)

            try:
                self.handle_client(session)
            except Exception as e:
                print(f"[!] Client error: {e}")
            finally:
                session.cleanup()
                print(f"[-] Client disconnected: {client_addr}")

    def handle_client(self, session: FTPSession):
        """
        Handles a single FTP client connection.
        """
        self.send_response(session, "220 Welcome to Django FTP Server")

        while True:
            command_line = self.recv_command(session)

            if not command_line:
                break

            print(f"[CLIENT] {command_line}")

            parts = command_line.split(" ", 1)
            command = parts[0].upper()
            argument = parts[1] if len(parts) > 1 else None

            if command == "USER":
                session.username = argument
                self.send_response(session, "331 Username OK, need password")

            elif command == "PASS":
                # For now accept any password
                session.is_authenticated = True
                self.send_response(session, "230 Login successful")

            elif command == "SYST":
                self.send_response(session, "215 UNIX Type: L8")

            elif command == "PWD":
                self.send_response(session, f'257 "{session.current_dir}" is the current directory')

            elif command == "CWD":
                if not argument:
                    self.send_response(session, "501 Missing directory name")
                    continue

                try:
                    real_path = session.get_real_path(argument)

                    # Check if directory exists
                    import os
                    if os.path.isdir(real_path):
                        session.set_current_dir(argument if argument.startswith("/") else session.current_dir + "/" + argument)
                        self.send_response(session, "250 Directory changed successfully")
                    else:
                        self.send_response(session, "550 Directory not found")

                except PermissionError:
                    self.send_response(session, "550 Access denied")

            elif command == "CDUP":
                # Move one level up
                import os
                new_dir = os.path.normpath(session.current_dir + "/..").replace("\\", "/")
                if not new_dir.startswith("/"):
                    new_dir = "/" + new_dir

                try:
                    real_path = session.get_real_path(new_dir)
                    if os.path.isdir(real_path):
                        session.set_current_dir(new_dir)
                        self.send_response(session, "200 Directory changed to parent")
                    else:
                        self.send_response(session, "550 Cannot go up")
                except PermissionError:
                    self.send_response(session, "550 Access denied")

            elif command == "TYPE":
                if argument not in ["A", "I"]:
                    self.send_response(session, "504 Unsupported TYPE")
                else:
                    session.transfer_type = argument
                    self.send_response(session, f"200 Type set to {argument}")

            elif command == "NOOP":
                self.send_response(session, "200 OK")

            elif command == "QUIT":
                self.send_response(session, "221 Goodbye")
                break

            else:
                self.send_response(session, "500 Unknown command")

    def send_response(self, session: FTPSession, message: str):
        """
        Sends a response with CRLF ending (required by FTP standard).
        """
        full_message = message + "\r\n"
        session.client_socket.sendall(full_message.encode("utf-8"))

        print(f"[SERVER] {message}")

    def recv_command(self, session: FTPSession):
        """
        Receives one FTP command line.
        """
        data = b""

        while True:
            chunk = session.client_socket.recv(1024)
            if not chunk:
                return None

            data += chunk

            if b"\n" in data:
                break

        return data.decode("utf-8", errors="ignore").strip()
