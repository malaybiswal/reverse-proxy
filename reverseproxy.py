import http.server
import socketserver
import urllib.request
from urllib.parse import urlparse
import sys
import ssl
import time  # Import the time module
from constant import BACKEND_SERVERS
import logging

current_backend = 0
# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ReverseProxyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.forward_request()

    def do_POST(self):
        self.forward_request()

    def forward_request(self):
        # Redirect to HTTPS if the request is on HTTP (port 80)
        if self.server.socket.getsockname()[1] == 80:
            https_url = f"https://{self.headers['Host']}{self.path}"
            self.send_response(301)
            self.send_header('Location', https_url)
            self.end_headers()
            return

        # Block requests on ports other than 80 or 443
        server_port = self.server.socket.getsockname()[1]
        if server_port not in [80, 443, 8082]:
            self.send_error(403, "Access to this port is blocked")
            return

        # Perform round-robin load balancing
        global current_backend
        backend_server = self.get_next_backend()
        if not backend_server:
            self.send_error(502, "No healthy backend servers available")
            return

        parsed_backend_url = urlparse(backend_server['url'])
        target_url = f"{parsed_backend_url.scheme}://{parsed_backend_url.netloc}{self.path}"

        # Prepare the request to the backend
        backend_request = urllib.request.Request(target_url, headers=self.headers)
        backend_request.add_header('Connection', 'close')
        logger.info(f"sending traffic to backend:{target_url}")

        if self.command == 'POST':
            content_length = int(self.headers['Content-Length'])
            post_body = self.rfile.read(content_length)
            backend_request.data = post_body

        try:
            # Forward the request to the backend server and get the response
            with urllib.request.urlopen(backend_request) as response:
                self.send_response(response.status)
                for header_key, header_value in response.getheaders():
                    self.send_header(header_key, header_value)
                self.end_headers()
                self.wfile.write(response.read())
                # Only update current_backend if the request was successful
                global current_backend
                current_backend = (current_backend + 1) % len(BACKEND_SERVERS)
        except urllib.error.HTTPError as e:
            self.send_error(e.code, e.reason)
        except urllib.error.URLError as e:
            self.send_error(502, "Bad Gateway: Could not reach the backend server")

    def get_next_backend(self):
        """Get the next healthy backend server using round-robin."""
        global current_backend
        for _ in range(len(BACKEND_SERVERS)):
            backend = BACKEND_SERVERS[current_backend]
            logger.debug(f"getNextBackEnd backend:{backend}")
            if backend['healthy']:
                return backend
            # Move to the next backend server if the current one is not healthy
            current_backend = (current_backend + 1) % len(BACKEND_SERVERS)
            logger.debug(f"current_backend:{current_backend}")
        return None

# Health checking mechanism to mark unhealthy servers
def check_backend_health():
    for backend in BACKEND_SERVERS:
        try:
            urllib.request.urlopen(backend["url"])
            backend["healthy"] = True
            logger.debug(f"TRY BACKEND:{backend}")
        except Exception:
            backend["healthy"] = False
            logger.debug(f"EXCEPT BACKEND:{backend}")

def run_server(port):
    with socketserver.TCPServer(("", port), ReverseProxyHTTPRequestHandler) as httpd:
        # Enable HTTPS (self-signed certificate for testing purposes)
        if port == 443:
            httpd.socket = ssl.wrap_socket(httpd.socket,
                                           server_side=True,
                                           certfile="path/to/localhost.pem",  # Update with your certificate path
                                           keyfile="path/to/localhost-key.pem",
                                           ssl_version=ssl.PROTOCOL_TLS)
        logger.info(f"Serving reverse proxy on port {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("Usage: python reverse_proxy.py <port>")
        sys.exit(1)

    port = int(sys.argv[1])

    # Check backend health periodically
    import threading
    health_check_interval = 10  # seconds
    def health_check_loop():
        while True:
            check_backend_health()
            time.sleep(health_check_interval)

    threading.Thread(target=health_check_loop, daemon=True).start()

    run_server(port)