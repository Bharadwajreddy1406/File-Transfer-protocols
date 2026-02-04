import socket

class FTPConnection:
    """
    Handles raw TCP socket connection to FTP server.
    This class is protocol-agnostic - it just manages the socket.
    """
    
    def __init__(self, host, port=21, timeout=30):
        """
        Initialize connection parameters (doesn't connect yet)
        
        Args:
            host: Server address
            port: FTP port
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        
    def connect(self):
        """
        Open TCP connection to the FTP server.
        
        Returns:
            str: Welcome message (for control connection) or empty string (for data connection)
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        
        try:
            print(f"  [DEBUG] Attempting TCP connect to {self.host}:{self.port}...")
            self.sock.connect((self.host, self.port))
            print(f"  [DEBUG] TCP socket connected!")
            
        except socket.timeout:
            raise TimeoutError(
                f"Connection to {self.host}:{self.port} timed out after {self.timeout} seconds.\n"
                f"Possible causes:\n"
                f"  - Server is not responding\n"
                f"  - Firewall blocking connection\n"
                f"  - Network issues"
            )
        except ConnectionRefusedError:
            raise ConnectionRefusedError(
                f"Connection to {self.host}:{self.port} refused.\n"
                f"Possible causes:\n"
                f"  - Nothing listening on that port\n"
                f"  - Firewall blocking\n"
                f"  - Wrong host/port"
            )
        except Exception as e:
            raise Exception(f"Failed to connect to {self.host}:{self.port}: {e}")
        
        # Control connection (port 21) gets welcome message
        # Data connection (other ports) doesn't
        if self.port == 21:
            response = self._read_response()
            return response
        else:
            # Data connection - no welcome message expected
            print(f"  [DEBUG] Data connection ready (no welcome message)")
            return ""
    
    def _read_response(self):
        """
        Read response from server with timeout-based completion detection.
        
        Returns:
            str: Complete server response
        """
        original_timeout = self.sock.gettimeout()
        self.sock.settimeout(0.5)  # Short timeout for detecting end of response
        
        response = b''
        
        try:
            while True:
                try:
                    chunk = self.sock.recv(4096)
                    
                    if not chunk:
                        break
                    
                    response += chunk
                    
                    # Check if we have a complete response
                    if b'\n' in chunk:
                        text = response.decode('utf-8', errors='ignore')
                        lines = text.strip().split('\n')
                        
                        if lines:
                            last_line = lines[-1]
                            
                            # FTP responses end with "XXX Message" (3 digits + space)
                            if len(last_line) >= 4 and last_line[:3].isdigit() and last_line[3] == ' ':
                                break
                
                except socket.timeout:
                    # No more data - assume response is complete
                    if response:
                        break
                    
        finally:
            self.sock.settimeout(original_timeout)
        
        return response.decode('utf-8', errors='ignore')
    
    def send_command(self, command):
        """
        Send command to FTP server and get response.
        
        Args:
            command: FTP command
            
        Returns:
            str: Server's response
        """
        full_command = f"{command}\r\n".encode('utf-8')
        self.sock.sendall(full_command)
        return self._read_response()
    
    def close(self):
        """Close the TCP connection."""
        if self.sock:
            self.sock.close()
            self.sock = None