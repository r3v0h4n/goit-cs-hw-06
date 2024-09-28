import json
import multiprocessing
import pathlib
import socket
from http.server import BaseHTTPRequestHandler
import socketserver
from datetime import datetime
from pymongo import MongoClient
import urllib.parse
import mimetypes

# MongoDB connection
client = MongoClient('mongodb://mongo:27017/')
db = client['message_db']
messages_collection = db['messages']

# HTTP Server
class MyHttpRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message':
            self.send_html_file('message.html')
        else:
            if pathlib.Path().joinpath('static', pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)
    def do_POST(self):
        if self.path == "/message":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            parsed_data = urllib.parse.parse_qs(post_data.decode('utf-8'))
            
            message_dict = {
                "username": parsed_data["username"][0],
                "message": parsed_data["message"][0]
            }
            self.send_to_socket_server(message_dict)
            
            self.send_html_file('messageSent.html')
        else:
            self.send_html_file('error.html', 404)

    def send_to_socket_server(self, message_dict):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', 5000))
            s.sendall(json.dumps(message_dict).encode())
    
    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(f'templates/{filename}', 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'static/{self.path}', 'rb') as file:
            self.wfile.write(file.read())

# Socket server
def socket_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 5000))
    server_socket.listen(5)
    
    while True:
        client_socket, address = server_socket.accept()
        data = client_socket.recv(1024)
        
        if data:
            message_dict = json.loads(data.decode())
            message_dict["date"] = str(datetime.now())
            
            messages_collection.insert_one(message_dict)
            print(f"Збережено повідомлення від {message_dict['username']}")

        client_socket.close()


def run_http_server():
    PORT = 3000
    handler = MyHttpRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print("Serving at port", PORT)
        httpd.serve_forever()


if __name__ == "__main__":
    http_process = multiprocessing.Process(target=run_http_server)
    socket_process = multiprocessing.Process(target=socket_server)

    http_process.start()
    socket_process.start()

    http_process.join()
    socket_process.join()
