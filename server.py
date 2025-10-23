import socket
import os
import sys
import mimetypes
import urllib.parse
from datetime import datetime

mimetypes.init()
mimetypes.add_type('application/pdf', '.pdf')
SUPPORTED_MIMES = {
    '.html': 'text/html',
    '.png': 'image/png',
    '.pdf': 'application/pdf'
}

def generate_dir_listing(path, requested_path):
    """Generates an HTML directory listing for a given path."""
    items = sorted(os.listdir(path))
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Directory Listing for {requested_path}</title>
    <style>
        body {{ font-family: monospace; }}
        a {{ text-decoration: none; }}
        pre {{ margin: 0; }}
    </style>
</head>
<body>
    <h1>Directory listing for {requested_path}</h1>
    <hr>
    <pre>
"""
    if requested_path != '/':
        parent_dir = os.path.normpath(os.path.join(requested_path, '..'))
        html += f'<a href="{parent_dir}">../</a>\n'

    for item in items:
        encoded_item = urllib.parse.quote(item)
        full_path = os.path.join(path, item)
        link = os.path.join(requested_path, encoded_item).replace('\\', '/')
        if os.path.isdir(full_path):
            link += '/'
            item += '/'
        html += f'<a href="{link}">{item}</a>\n'

    html += """
    </pre>
    <hr>
</body>
</html>
"""
    return html.encode('utf-8')

def handle_request(client_socket, doc_root):
    """Parses request, finds file, and sends response."""
    request = client_socket.recv(4096).decode('utf-8', 'ignore')
    if not request:
        return

    try:
        first_line = request.split('\n')[0].strip()
        method, url_path, _ = first_line.split()
        url_path = urllib.parse.unquote(url_path) 
    except Exception:
        return 

    if method != 'GET':
        send_response(client_socket, 501, 'Not Implemented', 'text/plain', b'501 Not Implemented')
        return

    if '..' in url_path:
        send_response(client_socket, 403, 'Forbidden', 'text/plain', b'403 Forbidden: Directory traversal attempt.')
        return

    if url_path.endswith('/'):
        local_path = os.path.join(doc_root, url_path.lstrip('/'), 'index.html')
        is_directory_request = True
    else:
        local_path = os.path.join(doc_root, url_path.lstrip('/'))
        is_directory_request = False

    if not os.path.exists(local_path):
        if is_directory_request and os.path.isdir(os.path.join(doc_root, url_path.lstrip('/'))):
            local_path = os.path.join(doc_root, url_path.lstrip('/')) # Use the directory path
        else:
            send_404(client_socket)
            return

    if os.path.isdir(local_path):
        if not url_path.endswith('/'):
            redirect_url = url_path + '/'
            response_headers = [
                'HTTP/1.1 301 Moved Permanently',
                f'Location: {redirect_url}',
                f'Date: {datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")}',
                'Content-Length: 0',
                'Connection: close'
            ]
            client_socket.sendall('\r\n'.join(response_headers).encode('utf-8') + b'\r\n\r\n')
            return

        body = generate_dir_listing(local_path, url_path)
        send_response(client_socket, 200, 'OK', 'text/html; charset=utf-8', body)
        return

    ext = os.path.splitext(local_path)[1].lower()
    mime_type = SUPPORTED_MIMES.get(ext) or mimetypes.guess_type(local_path)[0]

    if mime_type is None or mime_type not in SUPPORTED_MIMES.values():
        send_404(client_socket, msg='Unsupported file type or extension.')
        return

    try:
        with open(local_path, 'rb') as f:
            body = f.read()
        send_response(client_socket, 200, 'OK', mime_type, body)
    except IOError:
        send_404(client_socket, msg='File could not be opened/read.')

def send_response(client_socket, status_code, status_text, content_type, body):
    """Constructs and sends the HTTP response."""
    response_headers = [
        f'HTTP/1.1 {status_code} {status_text}',
        f'Date: {datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")}',
        f'Content-Type: {content_type}',
        f'Content-Length: {len(body)}',
        'Connection: close'
    ]
    response = '\r\n'.join(response_headers).encode('utf-8') + b'\r\n\r\n' + body
    client_socket.sendall(response)

def send_404(client_socket, msg="The requested file or resource was not found."):
    """Sends a 404 Not Found response."""
    html_body = f'<html><body><h1>404 Not Found</h1><p>{msg}</p></body></html>'.encode('utf-8')
    send_response(client_socket, 404, 'Not Found', 'text/html; charset=utf-8', html_body)

def main():
    if len(sys.argv) != 2:
        print("Usage: python server.py <directory_to_serve>")
        sys.exit(1)

    doc_root = sys.argv[1]
    if not os.path.isdir(doc_root):
        print(f"Error: Directory '{doc_root}' does not exist.")
        sys.exit(1)

    HOST = '0.0.0.0'
    PORT = 8080

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1) 
        print(f"Server serving directory '{doc_root}' on http://{HOST}:{PORT}...")

        while True:
            try:
                client_socket, client_address = s.accept()
                print(f"Connection from {client_address[0]}:{client_address[1]}")
                handle_request(client_socket, doc_root)
                client_socket.close()
            except KeyboardInterrupt:
                print("\nServer shutting down.")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                if 'client_socket' in locals():
                    client_socket.close()

if __name__ == '__main__':
    main()