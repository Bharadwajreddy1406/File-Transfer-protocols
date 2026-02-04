from django.core.management.base import BaseCommand
from ftp_client.services.ftp_core import FTPClient

class Command(BaseCommand):
    """
    Django management command to test FTP connection.
    
    Management commands are Django's way of creating CLI tools.
    They live in: app/management/commands/command_name.py
    Run with: python manage.py command_name
    
    BaseCommand gives us:
    - self.stdout.write() for output
    - self.style for colored output
    - Argument parsing
    - Error handling
    """
    
    # Help text shown when you run: python manage.py help ftp_test
    help = 'Test basic FTP connection and login'
    
    def add_arguments(self, parser):
        """
        Define command-line arguments.
        
        This lets you do:
        python manage.py ftp_test --host ftp.example.com --user bob
        
        For now, we'll use defaults, but this shows how to add options.
        """
        # Optional argument: which server to connect to
        parser.add_argument(
            '--host',
            type=str,
            default='ftp.gnu.org',
            help='FTP server hostname (default: ftp.gnu.org)'
        )
        
        # Optional argument: username
        parser.add_argument(
            '--user',
            type=str,
            default='anonymous',
            help='FTP username (default: anonymous)'
        )
        
        # Optional argument: password
        parser.add_argument(
            '--password',
            type=str,
            default='guest@example.com',
            help='FTP password (default: guest@example.com)'
        )
    
    def handle(self, *args, **options):
        """
        Main command logic. Django calls this when command runs.
        
        Args:
            options: Dictionary of command-line arguments
                     e.g., {'host': 'ftp.gnu.org', 'user': 'anonymous'}
        """
        # Extract arguments (with defaults from add_arguments)
        host = options['host']
        username = options['user']
        password = options['password']
        
        # Print header
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.HTTP_INFO("FTP CONNECTION TEST"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Host: {host}")
        self.stdout.write(f"User: {username}")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        
        # Create FTP client
        client = FTPClient(host)
        
        try:
            # STEP 1: Connect to server
            self.stdout.write(self.style.WARNING("STEP 1: Connecting to server..."))
            self.stdout.write("")
            
            client.connect()
            
            # Success message
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Connection established!"))
            self.stdout.write("")
            
            # STEP 2: Login
            self.stdout.write(self.style.WARNING("STEP 2: Logging in..."))
            self.stdout.write("")
            
            login_success = client.login(username, password)
            
            self.stdout.write("")
            
            if login_success:
                self.stdout.write(self.style.SUCCESS("✓ LOGIN SUCCESSFUL!"))
                self.stdout.write("")
                
                # NEW: List files
                try:
                    self.stdout.write(self.style.WARNING("STEP 2.5: Listing files..."))
                    self.stdout.write("")
                    
                    listing = client.list_files()
                    
                    self.stdout.write("")
                    self.stdout.write(self.style.SUCCESS("✓ FILE LISTING RECEIVED:"))
                    self.stdout.write("")
                    self.stdout.write("─" * 60)
                    
                    # Print first 20 lines only (listings can be huge)
                    lines = listing.split('\n')[:20]
                    for line in lines:
                        if line.strip():  # Skip empty lines
                            self.stdout.write(line)
                    
                    if len(listing.split('\n')) > 20:
                        self.stdout.write("...")
                        self.stdout.write(f"(+ {len(listing.split('\n')) - 20} more files)")
                    
                    self.stdout.write("─" * 60)
                    
                except Exception as e:
                    self.stdout.write("")
                    self.stdout.write(self.style.ERROR(f"✗ LIST FAILED: {e}"))
                    import traceback
                    self.stdout.write(traceback.format_exc())
                    
            client.quit()
            
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("DISCONNECTED CLEANLY"))
            
        except ConnectionRefusedError:
            # Server isn't running or wrong host/port
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("CONNECTION REFUSED"))
            self.stdout.write("")
            self.stdout.write(f"Cannot connect to {host}:21")
            self.stdout.write("Possible reasons:")
            self.stdout.write("  - Server is down")
            self.stdout.write("  - Firewall blocking connection")
            self.stdout.write("  - Wrong hostname")
            
        except TimeoutError:
            # Server didn't respond in time
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("CONNECTION TIMEOUT"))
            self.stdout.write("")
            self.stdout.write(f"Server {host} didn't respond within 30 seconds")
            self.stdout.write("Possible reasons:")
            self.stdout.write("  - Server is slow/overloaded")
            self.stdout.write("  - Network issues")
            
        except Exception as e:
            # Something else went wrong
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f"ERROR: {type(e).__name__}"))
            self.stdout.write("")
            self.stdout.write(str(e))
            
            # Print full traceback for debugging
            import traceback
            self.stdout.write("")
            self.stdout.write("Full traceback:")
            self.stdout.write(traceback.format_exc())
            
        finally:
            # Always print footer
            self.stdout.write("")
            self.stdout.write("=" * 60)
            self.stdout.write("Test complete")
            self.stdout.write("=" * 60)