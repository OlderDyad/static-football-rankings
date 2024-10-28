from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from datetime import datetime
import os

# Store comments in memory for development
comments = []

class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Handle static files
        if self.path.startswith('/api/'):
            if self.path == '/api/comments':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(comments).encode())
                return
        else:
            # Serve static files from the current directory
            file_path = os.path.join(os.getcwd(), self.path.lstrip('/'))
            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.path = '/' + os.path.relpath(file_path, os.getcwd())
                return SimpleHTTPRequestHandler.do_GET(self)

        # If no file found, try index.html
        if self.path == '/':
            self.path = '/index.html'
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/api/comments':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                comment_data = json.loads(post_data.decode('utf-8'))
                
                # Add timestamp and ID
                comment_data['id'] = len(comments) + 1
                comment_data['timestamp'] = datetime.now().isoformat()
                
                comments.append(comment_data)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(comment_data).encode())
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, CustomHandler)
    print('Server running at http://localhost:8000')
    print('Current directory:', os.getcwd())
    httpd.serve_forever()