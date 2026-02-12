import socket
import threading
import random


class PassiveModeManager:
    """
    Manages passive mode (PASV/EPSV) data connections for FTP server.
    
    In passive mode:
    1. Server opens a socket and listens on a random port
    2. Server tells client the IP:port
    3. Client connects to that port
    4. Data transfer happens
    5. Connection closes
    """
    
    def __init__(self, session):
        """
        Initialize passive mode manager for a session.
        
        Args:
            session: FTPSession object
        """
        self.session = session
        self.data_socket = None
        self.listen_socket = None
    
    def setup_passive_mode(self, server_host):
        """
        Setup a passive mode listener socket.
        
        Args:
            server_host: Server's IP address
            
        Returns:
            tuple: (host, port) where client should connect
        """
        # Create a listener socket
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to a random available port (0 = let OS choose)
        # Use same host as control connection
        self.listen_socket.bind((server_host, 0))
        
        # Get the actual port assigned
        host, port = self.listen_socket.getsockname()
        
        # Listen for ONE connection
        self.listen_socket.listen(1)
        
        print(f"  [PASV] Listening on {host}:{port}")
        
        return host, port
    
    def accept_data_connection(self, timeout=30):
        """
        Wait for client to connect to our passive mode socket.
        
        Args:
            timeout: How long to wait for connection
            
        Returns:
            socket: Connected data socket
        """
        if not self.listen_socket:
            raise Exception("Passive mode not setup - call setup_passive_mode() first")
        
        # Set timeout so we don't wait forever
        self.listen_socket.settimeout(timeout)
        
        print(f"  [PASV] Waiting for client to connect...")
        
        try:
            # Accept the connection
            self.data_socket, client_addr = self.listen_socket.accept()
            print(f"  [PASV] Client connected from {client_addr}")
            
            return self.data_socket
            
        except socket.timeout:
            raise TimeoutError(f"Client did not connect within {timeout} seconds")
    
    def send_data(self, data):
        """
        Send data through the data connection.
        
        Args:
            data: bytes to send
            
        Returns:
            int: Number of bytes sent
        """
        if not self.data_socket:
            raise Exception("No data connection established")
        
        total_sent = 0
        
        # Send in chunks
        chunk_size = 8192
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i+chunk_size]
            sent = self.data_socket.send(chunk)
            total_sent += sent
        
        return total_sent
    
    def receive_data(self):
        """
        Receive all data from the data connection.
        
        Returns:
            bytes: Received data
        """
        if not self.data_socket:
            raise Exception("No data connection established")
        
        data = b''
        
        while True:
            chunk = self.data_socket.recv(8192)
            
            if not chunk:
                # Client closed connection = transfer complete
                break
            
            data += chunk
        
        return data
    
    def close(self):
        """
        Close data connection and listener socket.
        """
        if self.data_socket:
            try:
                self.data_socket.close()
            except:
                pass
            self.data_socket = None
        
        if self.listen_socket:
            try:
                self.listen_socket.close()
            except:
                pass
            self.listen_socket = None
        
        print(f"  [PASV] Data connection closed")
