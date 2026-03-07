"""Simple TCP proxy - forwards Windows port 9000 to WSL2 port 8888."""
import socket
import threading
import sys

LOCAL_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
TARGET_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8888
TARGET_HOST = "127.0.0.1"

def forward(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except:
        pass
    finally:
        src.close()
        dst.close()

def handle(client):
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.connect((TARGET_HOST, TARGET_PORT))
        t1 = threading.Thread(target=forward, args=(client, server), daemon=True)
        t2 = threading.Thread(target=forward, args=(server, client), daemon=True)
        t1.start()
        t2.start()
        t1.join()
    except Exception as e:
        print(f"Connection error: {e}")
        client.close()

listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(("127.0.0.1", LOCAL_PORT))
listener.listen(5)
print(f"TCP Proxy: 127.0.0.1:{LOCAL_PORT} -> {TARGET_HOST}:{TARGET_PORT}")
print(f"Open http://127.0.0.1:{LOCAL_PORT}/marathi_tts/tts/ in Chrome")

while True:
    client, addr = listener.accept()
    threading.Thread(target=handle, args=(client,), daemon=True).start()
