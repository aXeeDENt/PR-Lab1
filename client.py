import socket
import sys
import os
import urllib.parse

def http_get(host, port, path):
    """Performs an HTTP GET request and returns (headers, body)."""
    request = f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, port))
            s.sendall(request.encode('utf-8'))

            response_data = b''
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response_data += chunk

            if not response_data:
                print("Error: Empty response received.")
                return None, None

    except socket.error as e:
        print(f"Socket error: {e}")
        return None, None
    except socket.timeout:
        print("Error: Connection timed out.")
        return None, None

    try:
        header_end_index = response_data.find(b'\r\n\r\n')
        if header_end_index == -1:
            header_part = response_data.decode('latin-1').split('\r\n\r\n')[0]
            body_part = b''
        else:
            header_part = response_data[:header_end_index].decode('latin-1')
            body_part = response_data[header_end_index + 4:]

        headers = header_part.split('\r\n')
        return headers, body_part
    except Exception as e:
        print(f"Error parsing response: {e}")
        return None, None

def save_file(directory, path, content):
    """Saves file content to the specified directory."""
    file_name = os.path.basename(urllib.parse.urlparse(path).path)
    if not file_name: 
        file_name = 'index.html' if path == '/' else 'downloaded_file'

    save_path = os.path.join(directory, file_name)

    os.makedirs(directory, exist_ok=True)

    try:
        with open(save_path, 'wb') as f:
            f.write(content)
        print(f"Successfully saved file to: {save_path}")
    except IOError as e:
        print(f"Error saving file: {e}")

def get_header_value(headers, key):
    """Extracts a header value (case-insensitive) from a list of headers."""
    key = key.lower()
    for header in headers:
        if ':' in header:
            h_name, h_value = header.split(':', 1)
            if h_name.strip().lower() == key:
                return h_value.strip()
    return None

def main():
    if len(sys.argv) != 5:
        print("Usage: python client.py server_host server_port url_path directory")
        sys.exit(1)

    server_host = sys.argv[1]
    server_port = int(sys.argv[2])
    url_path = sys.argv[3]
    save_directory = sys.argv[4]

    if not url_path.startswith('/'):
        url_path = '/' + url_path

    print(f"Requesting: http://{server_host}:{server_port}{url_path}")

    headers, body = http_get(server_host, server_port, url_path)

    if not headers:
        print("Failed to get response.")
        return

    status_line = headers[0]
    try:
        status_code = int(status_line.split()[1])
    except IndexError:
        print(f"Error: Malformed status line: {status_line}")
        return

    if status_code != 200:
        print(f"Server responded with status code: {status_code} {status_line.split()[2]}")
        if body:
            print("\n--- Response Body ---")
            print(body.decode('latin-1', 'ignore'))
        return

    content_type = get_header_value(headers, 'Content-Type')

    if content_type is None:
        print("Warning: Content-Type header missing or malformed. Treating as HTML.")
        content_type = 'text/html' 

    if 'text/html' in content_type:
        try:
            content = body.decode('utf-8')
        except UnicodeDecodeError:
            content = body.decode('latin-1', 'ignore')

        print("\n--- HTML Response Body ---")
        print(content)
    elif 'image/png' in content_type or 'application/pdf' in content_type:
        print(f"File type: {content_type}. Saving to directory: {save_directory}")
        save_file(save_directory, url_path, body)
    else:
        print(f"Unknown Content-Type: {content_type}. Printing body as text.")
        try:
            content = body.decode('utf-8')
        except UnicodeDecodeError:
            content = body.decode('latin-1', 'ignore')
        print("\n--- Unknown Response Body ---")
        print(content)

if __name__ == '__main__':
    main()