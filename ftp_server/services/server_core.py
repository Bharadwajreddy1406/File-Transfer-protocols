import socket
from .session import FTPSession
from .data_connection import PassiveModeManager
from .file_system import FileSystemHelper


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

            elif command == "PASV":
                self.handle_pasv(session)

            elif command == "EPSV":
                self.handle_epsv(session)

            elif command == "LIST":
                self.handle_list(session, argument or ".")

            elif command == "RETR":
                if not argument:
                    self.send_response(session, "501 Missing filename")
                else:
                    self.handle_retr(session, argument)

            elif command == "STOR":
                if not argument:
                    self.send_response(session, "501 Missing filename")
                else:
                    self.handle_stor(session, argument)

            elif command == "DELE":
                if not argument:
                    self.send_response(session, "501 Missing filename")
                else:
                    self.handle_dele(session, argument)

            elif command == "MKD":
                if not argument:
                    self.send_response(session, "501 Missing directory name")
                else:
                    self.handle_mkd(session, argument)

            elif command == "RMD":
                if not argument:
                    self.send_response(session, "501 Missing directory name")
                else:
                    self.handle_rmd(session, argument)

            elif command == "RNFR":
                if not argument:
                    self.send_response(session, "501 Missing filename")
                else:
                    # Store the source filename for RNTO
                    session.rename_from = argument
                    self.send_response(session, "350 Ready for RNTO")

            elif command == "RNTO":
                if not argument:
                    self.send_response(session, "501 Missing filename")
                elif not hasattr(session, 'rename_from') or not session.rename_from:
                    self.send_response(session, "503 RNFR required first")
                else:
                    self.handle_rnto(session, session.rename_from, argument)
                    session.rename_from = None

            elif command == "SIZE":
                if not argument:
                    self.send_response(session, "501 Missing filename")
                else:
                    self.handle_size(session, argument)

            elif command == "MDTM":
                if not argument:
                    self.send_response(session, "501 Missing filename")
                else:
                    self.handle_mdtm(session, argument)

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

    def handle_pasv(self, session: FTPSession):
        """
        Handle PASV (Passive Mode) command.
        """
        try:
            # Create passive mode manager
            pasv_mgr = PassiveModeManager(session)
            
            # Setup passive listener
            host, port = pasv_mgr.setup_passive_mode(self.host)
            
            # Store in session for later use
            session.passive_manager = pasv_mgr
            
            # Calculate PASV response format: h1,h2,h3,h4,p1,p2
            # IP address parts
            h1, h2, h3, h4 = host.split('.')
            
            # Port parts (port = p1*256 + p2)
            p1 = port // 256
            p2 = port % 256
            
            # Send response
            self.send_response(session, f"227 Entering Passive Mode ({h1},{h2},{h3},{h4},{p1},{p2})")
            
        except Exception as e:
            print(f"[ERROR] PASV failed: {e}")
            self.send_response(session, "425 Cannot open passive connection")

    def handle_epsv(self, session: FTPSession):
        """
        Handle EPSV (Extended Passive Mode) command.
        """
        try:
            # Create passive mode manager
            pasv_mgr = PassiveModeManager(session)
            
            # Setup passive listener
            host, port = pasv_mgr.setup_passive_mode(self.host)
            
            # Store in session for later use
            session.passive_manager = pasv_mgr
            
            # EPSV response format: (|||port|)
            self.send_response(session, f"229 Entering Extended Passive Mode (|||{port}|)")
            
        except Exception as e:
            print(f"[ERROR] EPSV failed: {e}")
            self.send_response(session, "425 Cannot open passive connection")

    def handle_list(self, session: FTPSession, path):
        """
        Handle LIST command - send directory listing.
        """
        if not session.is_authenticated:
            self.send_response(session, "530 Not logged in")
            return
        
        if not hasattr(session, 'passive_manager') or not session.passive_manager:
            self.send_response(session, "425 Use PASV or EPSV first")
            return
        
        try:
            # Get real path
            real_path = session.get_real_path(path)
            
            # Get directory listing
            listing = FileSystemHelper.list_directory(real_path)
            
            # Tell client we're about to send data
            self.send_response(session, "150 Opening data connection for directory listing")
            
            # Accept data connection
            session.passive_manager.accept_data_connection()
            
            # Send listing
            session.passive_manager.send_data(listing.encode('utf-8'))
            
            # Close data connection
            session.passive_manager.close()
            
            # Tell client transfer is complete
            self.send_response(session, "226 Directory listing sent")
            
        except FileNotFoundError:
            session.passive_manager.close()
            self.send_response(session, "550 Directory not found")
        except PermissionError:
            session.passive_manager.close()
            self.send_response(session, "550 Permission denied")
        except Exception as e:
            print(f"[ERROR] LIST failed: {e}")
            session.passive_manager.close()
            self.send_response(session, "550 Failed to list directory")

    def handle_retr(self, session: FTPSession, filename):
        """
        Handle RETR command - send file to client.
        """
        if not session.is_authenticated:
            self.send_response(session, "530 Not logged in")
            return
        
        if not hasattr(session, 'passive_manager') or not session.passive_manager:
            self.send_response(session, "425 Use PASV or EPSV first")
            return
        
        try:
            # Get real path
            real_path = session.get_real_path(filename)
            
            # Read file
            file_data = FileSystemHelper.read_file(real_path)
            
            # Tell client we're about to send data
            self.send_response(session, f"150 Opening data connection for {filename} ({len(file_data)} bytes)")
            
            # Accept data connection
            session.passive_manager.accept_data_connection()
            
            # Send file
            session.passive_manager.send_data(file_data)
            
            # Close data connection
            session.passive_manager.close()
            
            # Tell client transfer is complete
            self.send_response(session, "226 Transfer complete")
            
        except FileNotFoundError:
            session.passive_manager.close()
            self.send_response(session, "550 File not found")
        except IsADirectoryError:
            session.passive_manager.close()
            self.send_response(session, "550 Is a directory")
        except PermissionError:
            session.passive_manager.close()
            self.send_response(session, "550 Permission denied")
        except Exception as e:
            print(f"[ERROR] RETR failed: {e}")
            session.passive_manager.close()
            self.send_response(session, "550 Failed to retrieve file")

    def handle_stor(self, session: FTPSession, filename):
        """
        Handle STOR command - receive file from client.
        """
        if not session.is_authenticated:
            self.send_response(session, "530 Not logged in")
            return
        
        if not hasattr(session, 'passive_manager') or not session.passive_manager:
            self.send_response(session, "425 Use PASV or EPSV first")
            return
        
        try:
            # Get real path
            real_path = session.get_real_path(filename)
            
            # Tell client we're ready to receive
            self.send_response(session, f"150 Ready to receive {filename}")
            
            # Accept data connection
            session.passive_manager.accept_data_connection()
            
            # Receive file data
            file_data = session.passive_manager.receive_data()
            
            # Write file
            bytes_written = FileSystemHelper.write_file(real_path, file_data)
            
            # Close data connection
            session.passive_manager.close()
            
            # Tell client transfer is complete
            self.send_response(session, f"226 Transfer complete ({bytes_written} bytes received)")
            
        except PermissionError:
            session.passive_manager.close()
            self.send_response(session, "550 Permission denied")
        except Exception as e:
            print(f"[ERROR] STOR failed: {e}")
            session.passive_manager.close()
            self.send_response(session, "550 Failed to store file")

    def handle_dele(self, session: FTPSession, filename):
        """
        Handle DELE command - delete file.
        """
        if not session.is_authenticated:
            self.send_response(session, "530 Not logged in")
            return
        
        try:
            real_path = session.get_real_path(filename)
            FileSystemHelper.delete_file(real_path)
            self.send_response(session, f"250 File {filename} deleted")
            
        except FileNotFoundError:
            self.send_response(session, "550 File not found")
        except IsADirectoryError:
            self.send_response(session, "550 Is a directory, use RMD")
        except PermissionError:
            self.send_response(session, "550 Permission denied")
        except Exception as e:
            print(f"[ERROR] DELE failed: {e}")
            self.send_response(session, "550 Failed to delete file")

    def handle_mkd(self, session: FTPSession, dirname):
        """
        Handle MKD command - make directory.
        """
        if not session.is_authenticated:
            self.send_response(session, "530 Not logged in")
            return
        
        try:
            real_path = session.get_real_path(dirname)
            FileSystemHelper.make_directory(real_path)
            self.send_response(session, f'257 "{dirname}" directory created')
            
        except FileExistsError:
            self.send_response(session, "550 Directory already exists")
        except PermissionError:
            self.send_response(session, "550 Permission denied")
        except Exception as e:
            print(f"[ERROR] MKD failed: {e}")
            self.send_response(session, "550 Failed to create directory")

    def handle_rmd(self, session: FTPSession, dirname):
        """
        Handle RMD command - remove directory.
        """
        if not session.is_authenticated:
            self.send_response(session, "530 Not logged in")
            return
        
        try:
            real_path = session.get_real_path(dirname)
            FileSystemHelper.remove_directory(real_path)
            self.send_response(session, f"250 Directory {dirname} removed")
            
        except FileNotFoundError:
            self.send_response(session, "550 Directory not found")
        except NotADirectoryError:
            self.send_response(session, "550 Not a directory")
        except OSError:
            self.send_response(session, "550 Directory not empty")
        except PermissionError:
            self.send_response(session, "550 Permission denied")
        except Exception as e:
            print(f"[ERROR] RMD failed: {e}")
            self.send_response(session, "550 Failed to remove directory")

    def handle_rnto(self, session: FTPSession, old_name, new_name):
        """
        Handle RNTO command - rename file (second part of rename).
        """
        if not session.is_authenticated:
            self.send_response(session, "530 Not logged in")
            return
        
        try:
            old_path = session.get_real_path(old_name)
            new_path = session.get_real_path(new_name)
            FileSystemHelper.rename(old_path, new_path)
            self.send_response(session, "250 Rename successful")
            
        except FileNotFoundError:
            self.send_response(session, "550 Source file not found")
        except FileExistsError:
            self.send_response(session, "550 Destination already exists")
        except PermissionError:
            self.send_response(session, "550 Permission denied")
        except Exception as e:
            print(f"[ERROR] RNTO failed: {e}")
            self.send_response(session, "550 Failed to rename")

    def handle_size(self, session: FTPSession, filename):
        """
        Handle SIZE command - get file size.
        """
        if not session.is_authenticated:
            self.send_response(session, "530 Not logged in")
            return
        
        try:
            real_path = session.get_real_path(filename)
            size = FileSystemHelper.get_file_size(real_path)
            self.send_response(session, f"213 {size}")
            
        except FileNotFoundError:
            self.send_response(session, "550 File not found")
        except IsADirectoryError:
            self.send_response(session, "550 Is a directory")
        except Exception as e:
            print(f"[ERROR] SIZE failed: {e}")
            self.send_response(session, "550 Failed to get file size")

    def handle_mdtm(self, session: FTPSession, filename):
        """
        Handle MDTM command - get modification time.
        """
        if not session.is_authenticated:
            self.send_response(session, "530 Not logged in")
            return
        
        try:
            real_path = session.get_real_path(filename)
            mtime = FileSystemHelper.get_modification_time(real_path)
            self.send_response(session, f"213 {mtime}")
            
        except FileNotFoundError:
            self.send_response(session, "550 File not found")
        except Exception as e:
            print(f"[ERROR] MDTM failed: {e}")
            self.send_response(session, "550 Failed to get modification time")
