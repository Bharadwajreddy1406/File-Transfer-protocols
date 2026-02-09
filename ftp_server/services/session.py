import os
import datetime


class FTPSession:
    """
    Represents ONE connected FTP client session.

    FTP is stateful:
    - Server must remember authentication status
    - Current working directory
    - Passive mode sockets
    - Transfer mode (ASCII/Binary)

    This object will be created per client connection.
    """

    def __init__(self, client_socket, client_address, root_dir):
        self.client_socket = client_socket
        self.client_address = client_address

        # Root directory for FTP server (sandbox)
        self.root_dir = os.path.abspath(root_dir)

        # Current working directory (relative to root)
        self.current_dir = "/"

        # Authentication info
        self.is_authenticated = False
        self.username = None

        # Transfer type: "A" (ASCII) or "I" (Binary)
        self.transfer_type = "A"

        # Passive mode state
        self.passive_server_socket = None
        self.passive_port = None

        # Session metadata
        self.connected_at = datetime.datetime.now()

    def get_real_path(self, path=None):
        """
        Convert an FTP path (like /pub/file.txt) into a safe real filesystem path.

        This prevents directory traversal attacks like:
        CWD ../../Windows/System32
        """
        if path is None:
            path = self.current_dir

        # If client gives relative path, make it relative to current_dir
        if not path.startswith("/"):
            if self.current_dir.endswith("/"):
                path = self.current_dir + path
            else:
                path = self.current_dir + "/" + path

        # Normalize path
        normalized = os.path.normpath(path).replace("\\", "/")

        # Ensure starts with /
        if not normalized.startswith("/"):
            normalized = "/" + normalized

        # Convert to real system path
        real_path = os.path.abspath(os.path.join(self.root_dir, normalized.lstrip("/")))

        # Security check: real_path must remain inside root_dir
        if not real_path.startswith(self.root_dir):
            raise PermissionError("Access denied: Path traversal attempt detected")

        return real_path

    def set_current_dir(self, new_path):
        """
        Update current directory safely.
        """
        # Normalize
        normalized = os.path.normpath(new_path).replace("\\", "/")

        if not normalized.startswith("/"):
            normalized = "/" + normalized

        self.current_dir = normalized

    def cleanup(self):
        """
        Cleanup session resources.
        """
        try:
            if self.passive_server_socket:
                self.passive_server_socket.close()
                self.passive_server_socket = None
        except ConnectionAbortedError:
            pass

        try:
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
        except ConnectionAbortedError:
            pass
