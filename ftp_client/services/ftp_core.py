from .connection import FTPConnection

class FTPClient:
    """
    FTP Client that implements the FTP protocol.
    This class KNOWS about FTP - commands, response codes, login flow.
    
    FTP Protocol Basics:
    - Client sends commands (USER, PASS, QUIT, etc.)
    - Server responds with 3-digit codes + message
    - Codes tell you what happened (like HTTP status codes)
    """
    
    def __init__(self, host, port=21):
        """
        Create FTP client (doesn't connect yet).
        
        Args:
            host: FTP server address
            port: FTP port (default 21)
        """
        # Create connection object (but not connected yet)
        self.connection = FTPConnection(host, port)
        
        # Track login state
        self.logged_in = False
        self.host = host
        
    def connect(self):
        """
        Connect to FTP server.
        Server sends welcome message immediately.
        
        FTP Response Codes (first digit):
        - 1xx: Positive preliminary (waiting for more)
        - 2xx: Positive completion (success!)
        - 3xx: Positive intermediate (need more info)
        - 4xx: Transient negative (try again)
        - 5xx: Permanent negative (failed)
        
        Welcome is usually: "220 Server ready"
        
        Returns:
            str: Welcome message
        """
        # Open TCP connection and get welcome message
        welcome = self.connection.connect()
        
        # Print it so we can see what's happening
        print(f"Server says: {welcome.strip()}")
        
        # Check if server is ready (should start with "220")
        # 220 = Service ready for new user
        if not welcome.startswith('220'):
            raise Exception(f"Unexpected welcome: {welcome}")
            
        return welcome
    
    def login(self, username='anonymous', password='guest@example.com'):
        """
        Authenticate with FTP server.
        
        FTP Login Flow:
        1. Send USER <username>
        2. Server responds:
           - 230 = Login successful (no password needed)
           - 331 = Need password
           - 530 = Login failed
        3. If 331, send PASS <password>
        4. Server responds:
           - 230 = Login successful
           - 530 = Login failed
        
        Args:
            username: Login username (default 'anonymous' for public servers)
            password: Login password (default email for anonymous FTP)
            
        Returns:
            bool: True if login successful, False otherwise
        """
        # Step 1: Send username
        print(f"\n-> Sending: USER {username}")
        user_response = self.connection.send_command(f"USER {username}")
        print(f"<- Server says: {user_response.strip()}")
        
        # Parse response code (first 3 characters)
        # "331 Password required" → code is "331"
        response_code = user_response[:3]
            
        # Step 2: Check what server wants
        if response_code == '230':
            # 230 = User logged in, no password needed
            # (rare, but some servers allow this)
            print("Logged in without password!")
            self.logged_in = True
            return True
            
        elif response_code == '331':
            # 331 = Need password
            # Server is waiting for PASS command
            print("-> Password required, sending PASS command...")
            pass_response = self.connection.send_command(f"PASS {password}")
            print(f"<- Server says: {pass_response.strip()}")
            
            # Check password response
            pass_code = pass_response[:3]
            
            if pass_code == '230':
                # 230 = Login successful
                print("Login successful!")
                self.logged_in = True
                return True
            else:
                # 530 or other = Login failed
                print(f"✗ Login failed: {pass_response.strip()}")
                self.logged_in = False
                return False
                
        else:
            # Unexpected response (not 230 or 331)
            print(f"✗ Unexpected response to USER: {user_response.strip()}")
            self.logged_in = False
            return False
    
    def quit(self):
        """
        Properly disconnect from FTP server.
        
        FTP servers expect QUIT command before disconnecting.
        Just closing socket is rude and might leave server confused.
        
        Server should respond with:
        - 221 = Goodbye message
        """
        print("\n→ Sending: QUIT")
        
        try:
            # Send QUIT command
            quit_response = self.connection.send_command("QUIT")
            print(f"<- Server says: {quit_response.strip()}")
            
            # 221 = Service closing control connection
            if quit_response.startswith('221'):
                print("Disconnected cleanly")
            else:
                print(f"Unexpected QUIT response: {quit_response.strip()}")
                
        except Exception as e:
            # Sometimes server closes connection before we read response
            # That's okay, we're quitting anyway
            print(f"Error during quit (probably harmless): {e}")
            
        finally:
            # Always close socket, even if QUIT command failed
            self.connection.close()
            print("Socket closed")

    #########################
    # region DATA CONNECTION 
    #########################
    def _parse_pasv_response(self, response):
        """
        Parse PASV or EPSV response to get host and port for data connection.
        
        Two formats supported:
        
        1. PASV (RFC 959):
        "227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)"
        → IP: h1.h2.h3.h4, Port: p1*256 + p2
        
        2. EPSV (RFC 2428) - Extended Passive Mode:
        "229 Extended Passive Mode Entered (|||port|)"
        → Use same IP as control connection, Port: direct number
        
        Args:
            response: Server's PASV/EPSV response string
            
        Returns:
            tuple: (host, port) for data connection
            
        Raises:
            ValueError: If response format is invalid
        """
        import re
        
        # Check if this is EPSV response (229 code)
        if response.startswith('229'):
            # EPSV format: "229 Extended Passive Mode Entered (|||port|)"
            # Sometimes also: "229 Entering Extended Passive Mode (|||port|)"
            
            # Extract port from (|||port|) format
            match = re.search(r'\(\|\|\|(\d+)\|\)', response)
            
            if not match:
                raise ValueError(f"Invalid EPSV response: {response}")
            
            port = int(match.group(1))
            
            # EPSV doesn't provide host - use same host as control connection
            # (that's the whole point of EPSV - simpler!)
            host = self.host
            
            print("Using EPSV (Extended Passive Mode)")
            
            return host, port
        
        # Check if this is PASV response (227 code)
        elif response.startswith('227'):
            # PASV format: "227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)"
            
            match = re.search(r'\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)', response)
            
            if not match:
                raise ValueError(f"Invalid PASV response: {response}")
            
            # Extract the 6 numbers
            h1, h2, h3, h4, p1, p2 = match.groups()
            
            # Construct IP address
            host = f"{h1}.{h2}.{h3}.{h4}"
            
            # Calculate port number
            port = int(p1) * 256 + int(p2)
            
            print("Using PASV (Passive Mode)")
            
            return host, port
        
        else:
            raise ValueError(f"Unknown passive mode response: {response}")


    def _open_data_connection(self):
        """
        Open a data connection using EPSV or PASV mode.
        
        Note: Some servers return 229 (EPSV format) even when you send PASV.
        We handle both response formats for both commands.
        
        Returns:
            FTPConnection: New connection object for data transfer
        """
        data_conn = None
        
        # Try EPSV first (modern method)
        print("\n-> Sending: EPSV (requesting extended passive mode)")
        
        try:
            epsv_response = self.connection.send_command("EPSV")
            
            # Get only the last line (in case of multi-line response)
            last_line = epsv_response.strip().split('\n')[-1]
            print(f"<- Server says: {last_line}")
            
            # Check response code
            if last_line.startswith('229') or last_line.startswith('227'):
                # Success! Parse response (handles both 229 and 227)
                data_host, data_port = self._parse_pasv_response(last_line)
                print(f"Data connection: {data_host}:{data_port}")
                
                # Open data connection (is_control=False means no welcome message)
                data_conn = FTPConnection(data_host, data_port, is_control=False)
                data_conn.connect()
                print("Data connection established")
                
                return data_conn
                
            elif last_line.startswith('500') or last_line.startswith('502'):
                # Server doesn't support EPSV
                print("Server doesn't support EPSV, trying PASV...")
                
            else:
                print(f"Unexpected EPSV response: {last_line}")
        
        except Exception as e:
            print(f"EPSV failed: {e}")
        
        # Try PASV (older method)
        print("-> Sending: PASV (requesting passive mode)")
        
        try:
            pasv_response = self.connection.send_command("PASV")
            
            # Get only the last line
            last_line = pasv_response.strip().split('\n')[-1]
            print(f"<- Server says: {last_line}")
            
            # Some servers return 229 (EPSV format) even for PASV command!
            if last_line.startswith('227') or last_line.startswith('229'):
                # Parse response (handles both formats)
                data_host, data_port = self._parse_pasv_response(last_line)
                print(f"Data connection: {data_host}:{data_port}")
                
                # Open data connection (is_control=False means no welcome message)
                data_conn = FTPConnection(data_host, data_port, is_control=False)
                data_conn.connect()
                print("Data connection established")
                
                return data_conn
            else:
                raise Exception(f"PASV failed: {last_line}")
                
        except Exception as e:
            raise Exception(f"Both EPSV and PASV failed. Error: {e}")
        
    def list_files(self, path='.'):
        """
        List files in a directory on the FTP server.
        
        This is the first command that uses the DATA connection!
        
        How it works:
        1. Open data connection (via PASV)
        2. Send LIST command on control connection
        3. Receive file listing on data connection
        4. Close data connection
        
        Args:
            path: Directory to list (default: current directory)
            
        Returns:
            str: Directory listing (raw text from server)
        """
        # Make sure we're logged in
        if not self.logged_in:
            raise Exception("Must login before listing files")
        
        # Step 1: Open data connection
        print(f"\n-> Listing files in: {path}")
        data_conn = self._open_data_connection()
        
        try:
            # Step 2: Send LIST command on CONTROL connection
            print(f"-> Sending: LIST {path}")
            list_response = self.connection.send_command(f"LIST {path}")
            print(f"<- Server says: {list_response.strip()}")
            
            # Response should be "150 Opening data connection" or similar
            # This means server is about to send data
            if not (list_response.startswith('150') or list_response.startswith('125')):
                raise Exception(f"LIST failed: {list_response}")
            
            # Step 3: Read the file listing from DATA connection
            # Server sends listing, then closes data connection
            print("Reading file listing from data connection...")
            
            listing = b''  # Accumulate bytes
            
            while True:
                # Read chunks from data connection
                chunk = data_conn.sock.recv(4096)
                
                if not chunk:
                    # Empty chunk = connection closed by server
                    break
                    
                listing += chunk
            
            # Convert bytes to string
            listing_text = listing.decode('utf-8')
            
            # Step 4: Control connection should send completion message
            # "226 Transfer complete" or similar
            completion = self.connection._read_response()
            print(f"<- Server says: {completion.strip()}")
            
            if not completion.startswith('226'):
                print(f"Unexpected completion: {completion.strip()}")
            
            print("File listing received")
            
            return listing_text
            
        finally:
            # ALWAYS close data connection when done
            data_conn.close()
            print("Data connection closed")

    def pwd(self):
        """
        Print Working Directory - get current directory path.
        
        Returns:
            str: Current directory path
        """
        if not self.logged_in:
            raise Exception("Must login before using PWD")
        
        print("\n→ Sending: PWD (print working directory)")
        response = self.connection.send_command("PWD")
        print(f"← Server says: {response.strip()}")
        
        # Response format: 257 "/path/to/dir" is current directory
        if response.startswith('257'):
            # Extract path from quotes
            import re
            match = re.search(r'"([^"]+)"', response)
            if match:
                current_dir = match.group(1)
                print(f"  Current directory: {current_dir}")
                return current_dir
            else:
                # Some servers don't use quotes
                parts = response.split()
                if len(parts) >= 2:
                    return parts[1]
        
        raise Exception(f"PWD failed: {response}")


    def cwd(self, path):
        """
        Change Working Directory.
        
        Args:
            path: Directory path to change to
            
        Returns:
            bool: True if successful
        """
        if not self.logged_in:
            raise Exception("Must login before using CWD")
        
        print(f"\n→ Sending: CWD {path}")
        response = self.connection.send_command(f"CWD {path}")
        print(f"← Server says: {response.strip()}")
        
        # 250 = Directory changed successfully
        if response.startswith('250'):
            print(f"  ✓ Changed to: {path}")
            return True
        else:
            print("Failed to change directory")
            return False


    def cdup(self):
        """
        Change to parent directory (go up one level).
        
        Returns:
            bool: True if successful
        """
        if not self.logged_in:
            raise Exception("Must login before using CDUP")
        
        print("\n→ Sending: CDUP (change to parent directory)")
        response = self.connection.send_command("CDUP")
        print(f"← Server says: {response.strip()}")
        
        # 250 = Directory changed successfully
        if response.startswith('250'):
            print("  ✓ Moved to parent directory")
            return True
        else:
            print("  ✗ Failed to move to parent directory")
            return False

    def download_file(self, remote_filename, local_filename=None):
        """
        Download a file from the FTP server.
        
        This is similar to LIST but receives file data instead of directory listing.
        
        Args:
            remote_filename: Name of file on server
            local_filename: Where to save locally (defaults to same name)
            
        Returns:
            int: Number of bytes downloaded
        """
        if not self.logged_in:
            raise Exception("Must login before downloading")
        
        # Default to same filename
        if local_filename is None:
            local_filename = remote_filename
        
        print(f"\n→ Downloading: {remote_filename} → {local_filename}")
        
        # Step 1: Set binary mode (important for non-text files!)
        print("→ Sending: TYPE I (binary mode)")
        type_response = self.connection.send_command("TYPE I")
        print(f"← Server says: {type_response.strip()}")
        
        if not type_response.startswith('200'):
            raise Exception(f"Failed to set binary mode: {type_response}")
        
        # Step 2: Open data connection
        data_conn = self._open_data_connection()
        
        try:
            # Step 3: Send RETR command on control connection
            print(f"→ Sending: RETR {remote_filename}")
            retr_response = self.connection.send_command(f"RETR {remote_filename}")
            print(f"← Server says: {retr_response.strip()}")
            
            # Check if server is sending file
            # 150 = About to open data connection
            # 125 = Data connection already open, transfer starting
            if not (retr_response.startswith('150') or retr_response.startswith('125')):
                # Check for common errors
                if retr_response.startswith('550'):
                    raise Exception(f"File not found: {remote_filename}")
                else:
                    raise Exception(f"RETR failed: {retr_response}")
            
            # Step 4: Read file data from data connection
            print("  Reading file data...")
            
            file_data = b''
            bytes_received = 0
            
            while True:
                chunk = data_conn.sock.recv(8192)  # 8KB chunks
                
                if not chunk:
                    # Server closed connection = transfer complete
                    break
                
                file_data += chunk
                bytes_received += len(chunk)
                
                # Show progress every 100KB
                if bytes_received % 102400 == 0:
                    print(f"  Received: {bytes_received:,} bytes...")
            
            print(f"  ✓ Received {bytes_received:,} bytes")
            
            # Step 5: Save to local file
            print(f"  Writing to: {local_filename}")
            with open(local_filename, 'wb') as f:
                f.write(file_data)
            
            print("File saved!")
            
            # Step 6: Read completion message from control connection
            completion = self.connection._read_response()
            print(f"← Server says: {completion.strip()}")
            
            if not completion.startswith('226'):
                print(f"Unexpected completion: {completion.strip()}")
            
            return bytes_received
            
        finally:
            # Always close data connection
            data_conn.close()
            print("  Data connection closed")

    def upload_file(self, local_filename, remote_filename=None):
        """
        Upload a file to the FTP server.
        
        Args:
            local_filename: Local file to upload
            remote_filename: Name on server (defaults to same name)
            
        Returns:
            int: Number of bytes uploaded
        """
        if not self.logged_in:
            raise Exception("Must login before uploading")
        
        # Default to same filename
        if remote_filename is None:
            import os
            remote_filename = os.path.basename(local_filename)
        
        print(f"\n→ Uploading: {local_filename} → {remote_filename}")
        
        # Step 1: Read local file
        try:
            with open(local_filename, 'rb') as f:
                file_data = f.read()
            print(f"  Read {len(file_data):,} bytes from local file")
        except FileNotFoundError:
            raise Exception(f"Local file not found: {local_filename}")
        
        # Step 2: Set binary mode
        print("→ Sending: TYPE I (binary mode)")
        type_response = self.connection.send_command("TYPE I")
        print(f"← Server says: {type_response.strip()}")
        
        if not type_response.startswith('200'):
            raise Exception(f"Failed to set binary mode: {type_response}")
        
        # Step 3: Open data connection
        data_conn = self._open_data_connection()
        
        try:
            # Step 4: Send STOR command on control connection
            print(f"→ Sending: STOR {remote_filename}")
            stor_response = self.connection.send_command(f"STOR {remote_filename}")
            print(f"← Server says: {stor_response.strip()}")
            
            # Check if server is ready to receive
            if not (stor_response.startswith('150') or stor_response.startswith('125')):
                # Check for permission errors
                if stor_response.startswith('550'):
                    raise Exception(f"Permission denied or cannot create file: {remote_filename}")
                elif stor_response.startswith('553'):
                    raise Exception(f"Filename not allowed: {remote_filename}")
                else:
                    raise Exception(f"STOR failed: {stor_response}")
            
            # Step 5: Write file data to data connection
            print("  Sending file data...")
            
            bytes_sent = 0
            chunk_size = 8192  # 8KB chunks
            
            # Send in chunks to show progress
            for i in range(0, len(file_data), chunk_size):
                chunk = file_data[i:i+chunk_size]
                data_conn.sock.sendall(chunk)
                bytes_sent += len(chunk)
                
                # Show progress every 100KB
                if bytes_sent % 102400 == 0:
                    print(f"  Sent: {bytes_sent:,} / {len(file_data):,} bytes...")
            
            print(f"  ✓ Sent {bytes_sent:,} bytes")
            
            # Step 6: Close data connection (signals upload complete)
            data_conn.close()
            print("  Data connection closed (upload complete)")
            
            # Step 7: Read completion message from control connection
            completion = self.connection._read_response()
            print(f"← Server says: {completion.strip()}")
            
            if completion.startswith('226'):
                print("  ✓ Upload successful!")
            else:
                print(f"  ⚠ Unexpected completion: {completion.strip()}")
            
            return bytes_sent
            
        except Exception:
            # If upload fails, still try to close data connection
            try:
                data_conn.close()
            except ConnectionAbortedError:
                pass
            raise

    def delete_file(self, filename):
        """
        Delete a file on the FTP server.
        
        Args:
            filename: Name of file to delete
            
        Returns:
            bool: True if successful
        """
        if not self.logged_in:
            raise Exception("Must login before deleting files")
        
        print(f"\n→ Deleting file: {filename}")
        response = self.connection.send_command(f"DELE {filename}")
        print(f"← Server says: {response.strip()}")
        
        # 250 = File deleted successfully
        if response.startswith('250'):
            print(f"  ✓ File deleted: {filename}")
            return True
        elif response.startswith('550'):
            print(f"  ✗ File not found or permission denied")
            return False
        else:
            print(f"  ✗ Delete failed: {response.strip()}")
            return False

    def make_directory(self, dirname):
        """
        Create a new directory on the FTP server.
        
        Args:
            dirname: Name of directory to create
            
        Returns:
            str: Path of created directory (if successful)
        """
        if not self.logged_in:
            raise Exception("Must login before creating directories")
        
        print(f"\n→ Creating directory: {dirname}")
        response = self.connection.send_command(f"MKD {dirname}")
        print(f"← Server says: {response.strip()}")
        
        # 257 = Directory created
        if response.startswith('257'):
            # Extract directory path from quotes
            import re
            match = re.search(r'"([^"]+)"', response)
            if match:
                created_path = match.group(1)
                print(f"  ✓ Directory created: {created_path}")
                return created_path
            else:
                print("  ✓ Directory created")
                return dirname
        elif response.startswith('550'):
            print(f"  ✗ Cannot create directory (may already exist or permission denied)")
            return None
        else:
            print(f"  ✗ Failed: {response.strip()}")
            return None

    def remove_directory(self, dirname):
        """
        Remove a directory on the FTP server.
        
        Args:
            dirname: Name of directory to remove
            
        Returns:
            bool: True if successful
        """
        if not self.logged_in:
            raise Exception("Must login before removing directories")
        
        print(f"\n→ Removing directory: {dirname}")
        response = self.connection.send_command(f"RMD {dirname}")
        print(f"← Server says: {response.strip()}")
        
        # 250 = Directory removed
        if response.startswith('250'):
            print(f"  ✓ Directory removed: {dirname}")
            return True
        elif response.startswith('550'):
            print(f"  ✗ Directory not found or not empty")
            return False
        else:
            print(f"  ✗ Failed: {response.strip()}")
            return False

    def rename(self, old_name, new_name):
        """
        Rename a file or directory on the FTP server.
        
        This uses two commands:
        1. RNFR (Rename From) - specify source
        2. RNTO (Rename To) - specify destination
        
        Args:
            old_name: Current name
            new_name: New name
            
        Returns:
            bool: True if successful
        """
        if not self.logged_in:
            raise Exception("Must login before renaming files")
        
        print(f"\n→ Renaming: {old_name} → {new_name}")
        
        # Step 1: Send RNFR command
        print(f"→ Sending: RNFR {old_name}")
        rnfr_response = self.connection.send_command(f"RNFR {old_name}")
        print(f"← Server says: {rnfr_response.strip()}")
        
        # 350 = Ready for RNTO
        if not rnfr_response.startswith('350'):
            print(f"  ✗ RNFR failed (file not found?)")
            return False
        
        # Step 2: Send RNTO command
        print(f"→ Sending: RNTO {new_name}")
        rnto_response = self.connection.send_command(f"RNTO {new_name}")
        print(f"← Server says: {rnto_response.strip()}")
        
        # 250 = Rename successful
        if rnto_response.startswith('250'):
            print(f"  ✓ Renamed successfully")
            return True
        else:
            print(f"  ✗ RNTO failed: {rnto_response.strip()}")
            return False

    def get_file_size(self, filename):
        """
        Get the size of a file on the FTP server.
        
        Args:
            filename: Name of file
            
        Returns:
            int: File size in bytes, or None if failed
        """
        if not self.logged_in:
            raise Exception("Must login before getting file size")
        
        print(f"\n→ Getting size of: {filename}")
        response = self.connection.send_command(f"SIZE {filename}")
        print(f"← Server says: {response.strip()}")
        
        # 213 = File size response
        if response.startswith('213'):
            # Extract size from response
            parts = response.split()
            if len(parts) >= 2:
                try:
                    size = int(parts[1])
                    print(f"  File size: {size:,} bytes")
                    return size
                except ValueError:
                    pass
        
        print(f"  ✗ Failed to get file size")
        return None

    def get_modification_time(self, filename):
        """
        Get the last modification time of a file on the FTP server.
        
        Args:
            filename: Name of file
            
        Returns:
            str: Modification time (YYYYMMDDHHMMSS format), or None if failed
        """
        if not self.logged_in:
            raise Exception("Must login before getting modification time")
        
        print(f"\n→ Getting modification time of: {filename}")
        response = self.connection.send_command(f"MDTM {filename}")
        print(f"← Server says: {response.strip()}")
        
        # 213 = Modification time response
        if response.startswith('213'):
            # Extract timestamp from response
            parts = response.split()
            if len(parts) >= 2:
                timestamp = parts[1]
                print(f"  Modification time: {timestamp}")
                return timestamp
        
        print(f"  ✗ Failed to get modification time")
        return None

    def noop(self):
        """
        Send NOOP (No Operation) command to keep connection alive.
        
        Returns:
            bool: True if server responded positively
        """
        if not self.logged_in:
            raise Exception("Must login before using NOOP")
        
        print("\n→ Sending: NOOP (keep alive)")
        response = self.connection.send_command("NOOP")
        print(f"← Server says: {response.strip()}")
        
        # 200 = Command okay
        return response.startswith('200')

    def system_type(self):
        """
        Get the server's system type.
        
        Returns:
            str: System type string
        """
        if not self.logged_in:
            raise Exception("Must login before getting system type")
        
        print("\n→ Sending: SYST (get system type)")
        response = self.connection.send_command("SYST")
        print(f"← Server says: {response.strip()}")
        
        # 215 = System type response
        if response.startswith('215'):
            # Extract system type
            system_type = response[4:].strip()
            print(f"  System type: {system_type}")
            return system_type
        
        return None

    def set_transfer_type(self, type_code):
        """
        Set the transfer type (ASCII or Binary).
        
        Args:
            type_code: 'A' for ASCII, 'I' for Binary
            
        Returns:
            bool: True if successful
        """
        if not self.logged_in:
            raise Exception("Must login before setting transfer type")
        
        if type_code not in ['A', 'I']:
            raise ValueError("Type must be 'A' (ASCII) or 'I' (Binary)")
        
        type_name = "ASCII" if type_code == 'A' else "Binary"
        print(f"\n→ Setting transfer type to: {type_name}")
        response = self.connection.send_command(f"TYPE {type_code}")
        print(f"← Server says: {response.strip()}")
        
        # 200 = Type set successfully
        return response.startswith('200')