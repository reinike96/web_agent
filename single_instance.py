import socket
import threading

class SingleInstance:
    def __init__(self, port=50000, restore_callback=None):
        self.port = port
        self.restore_callback = restore_callback
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bound = False
        try:
            # Intenta enlazar en localhost
            self.sock.bind(('127.0.0.1', self.port))
            self.sock.listen(1)
            self.bound = True
            threading.Thread(target=self.listen, daemon=True).start()
        except OSError:
            # Ya hay una instancia, no se pudo enlazar
            self.bound = False

    def listen(self):
        while True:
            try:
                conn, _ = self.sock.accept()
                data = conn.recv(1024)
                if data.decode('utf-8') == "RESTORE" and self.restore_callback:
                    self.restore_callback()
                conn.close()
            except Exception:
                break

    @staticmethod
    def send_restore(port=50000):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', port))
            s.sendall(b"RESTORE")
            s.close()
        except Exception:
            pass
