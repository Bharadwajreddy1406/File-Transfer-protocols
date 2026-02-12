import os
import time
import stat


class FileSystemHelper:
    """
    Helper class for FTP file system operations.
    Handles file listing, reading, writing with proper security.
    """
    
    @staticmethod
    def list_directory(real_path):
        """
        List directory contents in Unix ls -l format.
        
        Args:
            real_path: Absolute filesystem path
            
        Returns:
            str: Directory listing in ls -l format
        """
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"Directory not found: {real_path}")
        
        if not os.path.isdir(real_path):
            raise NotADirectoryError(f"Not a directory: {real_path}")
        
        lines = []
        
        try:
            # List all files and directories
            entries = os.listdir(real_path)
            
            for entry in sorted(entries):
                entry_path = os.path.join(real_path, entry)
                
                try:
                    # Get file stats
                    stats = os.stat(entry_path)
                    
                    # Format: drwxr-xr-x  1 owner group size month day time name
                    
                    # File type and permissions
                    if os.path.isdir(entry_path):
                        perms = 'drwxr-xr-x'
                        size = 0
                    else:
                        perms = '-rw-r--r--'
                        size = stats.st_size
                    
                    # Number of links (always 1 for simplicity)
                    links = 1
                    
                    # Owner and group (just use "ftp" for both)
                    owner = "ftp"
                    group = "ftp"
                    
                    # File size
                    size_str = str(size)
                    
                    # Modification time
                    mtime = time.localtime(stats.st_mtime)
                    time_str = time.strftime("%b %d %H:%M", mtime)
                    
                    # Full line
                    line = f"{perms} {links:3} {owner:8} {group:8} {size_str:>12} {time_str} {entry}"
                    lines.append(line)
                    
                except Exception as e:
                    # If we can't stat a file, skip it
                    print(f"  [WARNING] Cannot stat {entry}: {e}")
                    continue
            
        except PermissionError:
            raise PermissionError(f"Permission denied: {real_path}")
        
        return "\r\n".join(lines) + "\r\n" if lines else ""
    
    @staticmethod
    def read_file(real_path):
        """
        Read a file from disk.
        
        Args:
            real_path: Absolute filesystem path
            
        Returns:
            bytes: File contents
        """
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"File not found: {real_path}")
        
        if not os.path.isfile(real_path):
            raise IsADirectoryError(f"Is a directory: {real_path}")
        
        with open(real_path, 'rb') as f:
            return f.read()
    
    @staticmethod
    def write_file(real_path, data):
        """
        Write a file to disk.
        
        Args:
            real_path: Absolute filesystem path
            data: bytes to write
            
        Returns:
            int: Number of bytes written
        """
        # Create parent directory if it doesn't exist
        parent_dir = os.path.dirname(real_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        
        with open(real_path, 'wb') as f:
            f.write(data)
        
        return len(data)
    
    @staticmethod
    def delete_file(real_path):
        """
        Delete a file.
        
        Args:
            real_path: Absolute filesystem path
        """
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"File not found: {real_path}")
        
        if not os.path.isfile(real_path):
            raise IsADirectoryError(f"Is a directory, not a file: {real_path}")
        
        os.remove(real_path)
    
    @staticmethod
    def make_directory(real_path):
        """
        Create a directory.
        
        Args:
            real_path: Absolute filesystem path
        """
        if os.path.exists(real_path):
            raise FileExistsError(f"Directory already exists: {real_path}")
        
        os.makedirs(real_path, exist_ok=False)
    
    @staticmethod
    def remove_directory(real_path):
        """
        Remove a directory (must be empty).
        
        Args:
            real_path: Absolute filesystem path
        """
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"Directory not found: {real_path}")
        
        if not os.path.isdir(real_path):
            raise NotADirectoryError(f"Not a directory: {real_path}")
        
        if os.listdir(real_path):
            raise OSError(f"Directory not empty: {real_path}")
        
        os.rmdir(real_path)
    
    @staticmethod
    def rename(old_path, new_path):
        """
        Rename a file or directory.
        
        Args:
            old_path: Current path
            new_path: New path
        """
        if not os.path.exists(old_path):
            raise FileNotFoundError(f"Source not found: {old_path}")
        
        if os.path.exists(new_path):
            raise FileExistsError(f"Destination already exists: {new_path}")
        
        os.rename(old_path, new_path)
    
    @staticmethod
    def get_file_size(real_path):
        """
        Get file size in bytes.
        
        Args:
            real_path: Absolute filesystem path
            
        Returns:
            int: File size in bytes
        """
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"File not found: {real_path}")
        
        if not os.path.isfile(real_path):
            raise IsADirectoryError(f"Is a directory: {real_path}")
        
        return os.path.getsize(real_path)
    
    @staticmethod
    def get_modification_time(real_path):
        """
        Get file modification time.
        
        Args:
            real_path: Absolute filesystem path
            
        Returns:
            str: Modification time in YYYYMMDDHHMMSS format
        """
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"File not found: {real_path}")
        
        mtime = os.path.getmtime(real_path)
        time_struct = time.gmtime(mtime)
        
        # Format: YYYYMMDDHHMMSS
        return time.strftime("%Y%m%d%H%M%S", time_struct)
