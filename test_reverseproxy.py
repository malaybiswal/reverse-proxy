import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
import reverseproxy
from reverseproxy import ReverseProxyHTTPRequestHandler
import urllib.error

class MockSocket:
    def __init__(self, request_text):
        self.request_text = request_text.encode('ascii')
        self.sent_data = BytesIO()

    def makefile(self, mode, bufsize):
        if mode == 'rb':
            return BytesIO(self.request_text)
        elif mode == 'wb':
            return self.sent_data
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    def sendall(self, data):
        self.sent_data.write(data)

    def getsockname(self):
        return ('localhost', 443)

class TestProxyHTTPRequestHandler(unittest.TestCase):
    def setUp(self):
        request_text = 'GET /some/path HTTP/1.1\r\nHost: localhost\r\n\r\n'
        self.mock_socket = MockSocket(request_text)
        self.client_address = ('127.0.0.1', 12345)
        self.server = MagicMock()
        self.server.socket = self.mock_socket

        # Create an instance of the ReverseProxyHTTPRequestHandler
        self.handler = ReverseProxyHTTPRequestHandler(
            self.mock_socket,
            self.client_address,
            self.server
        )
        
        # Set up the backend servers
        reverseproxy.BACKEND_SERVERS = [
            {"url": "http://localhost:8080", "healthy": True},
            {"url": "http://192.168.0.207", "healthy": True}
        ]
        reverseproxy.current_backend = 0

    def test_current_backend_initialization(self):
        self.assertEqual(reverseproxy.current_backend, 0)
        self.assertEqual(len(reverseproxy.BACKEND_SERVERS), 2)

    @patch('urllib.request.urlopen')
    def test_round_robin_load_balancing(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"Mock response"
        mock_response.status = 200
        mock_response.getheaders.return_value = []
        mock_urlopen.return_value.__enter__.return_value = mock_response
        initial_backend = reverseproxy.current_backend

        # Call do_GET() to simulate a request
        self.handler.do_GET()

        # Check if it switched to the next backend
        self.assertEqual(reverseproxy.current_backend, (initial_backend + 1) % len(reverseproxy.BACKEND_SERVERS))

        # Call do_GET() again
        self.handler.do_GET()

        # Check if it switched to the next backend again
        self.assertEqual(reverseproxy.current_backend, (initial_backend + 2) % len(reverseproxy.BACKEND_SERVERS))

        # Verify that urlopen was called twice with different backends
        self.assertEqual(mock_urlopen.call_count, 2)
        first_call_backend = mock_urlopen.call_args_list[0][0][0].full_url.split('/')[2]
        second_call_backend = mock_urlopen.call_args_list[1][0][0].full_url.split('/')[2]
        self.assertNotEqual(first_call_backend, second_call_backend)

    @patch('urllib.request.urlopen')
    def test_forward_request_403(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='http://localhost:8081',
            code=403,
            msg='Forbidden',
            hdrs=None,
            fp=BytesIO(b'Forbidden: Authentication required')
        )

        self.handler.do_GET()

        sent_data = self.mock_socket.sent_data.getvalue()
        self.assertIn(b'403 Forbidden', sent_data)
