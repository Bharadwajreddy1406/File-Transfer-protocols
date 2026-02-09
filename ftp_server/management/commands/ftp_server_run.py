from django.core.management.base import BaseCommand
from ftp_server.services.server_core import FTPServer


class Command(BaseCommand):
    help = "Run the FTP server (Phase 1: Control connection only)"

    def add_arguments(self, parser):
        parser.add_argument("--host", type=str, default="127.0.0.1")
        parser.add_argument("--port", type=int, default=2121)
        parser.add_argument("--root", type=str, default="server_storage")

    def handle(self, *args, **options):
        host = options["host"]
        port = options["port"]
        root_dir = options["root"]

        server = FTPServer(host=host, port=port, root_dir=root_dir)
        server.start()
