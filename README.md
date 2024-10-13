README Section

1. How Could Someone Get Started with Your Codebase?
Clone the repository.
Install Python if not already installed (python3 --version).
Set up a backend server on port 8082, or modify the BACKEND_URL variable to point to another backend.
Run the reverse proxy by executing python reverse_proxy.py 8082 in the terminal.
The reverse proxy will forward requests sent to localhost:8082 to the backend at localhost:80 and localhost:8080.
Modify BACKEND_SERVERS in constants.py accordingly

2. What Resources Did You Use to Build Your Implementation?
Python’s standard http.server documentation.
urllib library documentation for handling HTTP requests.
python mock library for unit test.

3. Explain Any Design Decisions You Made, Including Limitations of the System
Design Decisions:
The urllib.request module is used to forward the requests and responses without relying on third-party libraries.
I used http.server.SimpleHTTPRequestHandler as the base for the proxy handler to support both GET and POST requests.
Limitations:
The proxy forwards requests and responses as-is with no transformation, caching. 
I've implemented basic round robin load balancing.
No support for WebSocket connections.
No optimizations for large-scale performance or fault tolerance in this simple implementation.

4. How Would You Scale This?
Load Balancing: Add a mechanism to distribute traffic to multiple backend servers by latency and by host resource usage.
Concurrency: Use Python’s asyncio or run multiple instances of the proxy using a process manager like gunicorn for handling higher traffic.
Caching: Implement a caching layer to speed up response times for repeated requests.

5. How Would You Make It More Secure?
TLS/HTTPS: I've added code to switch from http to https and also checking certificates

Authentication: Introduce client authentication to control access to the proxy.
Request Validation: Sanitize and validate requests to prevent attacks like SQL injection or command injection.
Rate Limiting: Implement rate limiting to prevent denial of service attacks.
Logging: Added basic logging to this code. More logging can be added in future to analyze or audit in future.
