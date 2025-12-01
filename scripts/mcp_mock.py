import http.server
import socketserver
import json
import time
from urllib.parse import urlparse, parse_qs

PORT = 9000

class MCPMockHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path.endswith("/messages"):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "messages": [
                    {"seq": 1, "ts": time.time(), "payload": {"agent": "mock_agent", "text": "Hello form mock!"}}
                ]
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        if self.path.endswith("/messages"):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "accepted", "id": "mock-msg-123"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), MCPMockHandler) as httpd:
        print(f"Serving MCP Mock on port {PORT}")
        httpd.serve_forever()
