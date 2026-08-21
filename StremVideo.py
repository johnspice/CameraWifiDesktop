
"""
APP for MACOS
1.- debe compilar el codigo
2.-pip install pyinstaller

3.-

mkdir myicon.iconset
sips -z 16 16     logo.png --out myicon.iconset/icon_16x16.png
sips -z 32 32     logo.png --out myicon.iconset/icon_16x16@2x.png
sips -z 32 32     logo.png --out myicon.iconset/icon_32x32.png
sips -z 64 64     logo.png --out myicon.iconset/icon_32x32@2x.png
sips -z 128 128   logo.png --out myicon.iconset/icon_128x128.png
sips -z 256 256   logo.png --out myicon.iconset/icon_128x128@2x.png
sips -z 256 256   logo.png --out myicon.iconset/icon_256x256.png
sips -z 512 512   logo.png --out myicon.iconset/icon_256x256@2x.png
sips -z 512 512   logo.png --out myicon.iconset/icon_512x512.png
iconutil -c icns myicon.iconset -o app_icon.icns
rm -rf myicon.iconset


4.-pyinstaller --noconsole --onedir --windowed --icon=app_icon.icns --name="CameraWiFi" StremVideo.py


5.-brew install create-dmg

6.-

  create-dmg \
    --volname "Camera WiFi Installer" \
    --volicon "app_icon.icns" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "CameraWiFi.app" 175 190 \
    --hide-extension "CameraWiFi.app" \
    --app-drop-link 425 190 \
    "CameraWiFi.dmg" \
    "dist/CameraWiFi.app"

"""







"""
aPP for windows

1.- pip install PyQt6 pillow opencv-python numpy pyinstaller

2.- pyinstaller --noconsole --onedir --name="CameraWiFi" StremVideo.py

"""






import sys
import socket
import struct
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

PORT = 8888
MAX_FRAME_BYTES = 10_000_000

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

class NetworkWorker(QThread):
    frame_received = pyqtSignal(np.ndarray)
    disconnected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_running = True

    def recv_all(self, sock, length):
        data = bytearray()
        while len(data) < length:
            packet = sock.recv(length - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data

    def run(self):
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('0.0.0.0', PORT))
            server_socket.listen(1)

            while self.is_running:
                client_socket, _ = server_socket.accept()
                while self.is_running:
                    length_bytes = self.recv_all(client_socket, 4)
                    if not length_bytes:
                        break

                    frame_length = struct.unpack('>i', length_bytes)[0]
                    if frame_length <= 0 or frame_length > MAX_FRAME_BYTES:
                        break

                    jpeg_bytes = self.recv_all(client_socket, frame_length)
                    if not jpeg_bytes:
                        break

                    np_arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                    if frame is not None:
                        self.frame_received.emit(frame)

                client_socket.close()
                self.disconnected.emit()

        except Exception as e:
            print(f"Error en servidor: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AndroidCAMERA Wi-Fi")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #1E1E1E;")

        self.my_ip = get_local_ip()
        self.current_pixmap = None  # Guardar la última imagen recibida

        # Layout Principal
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Banner de IP
        self.ip_label = QLabel(f"IP : {self.my_ip}")
        self.ip_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #00FF88; padding: 12px; background-color: #2D2D2D;")
        self.ip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.ip_label)

        # Label de Video / Estado
        self.video_label = QLabel("⏳ Waiting for video transmission...")
        self.video_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #888888;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 💡 ESTO PERMITE REDIMENSIONAR LA VENTANA LIBREMENTE CON EL RATÓN:
        self.video_label.setScaledContents(False)
        self.video_label.setMinimumSize(320, 240)

        main_layout.addWidget(self.video_label, stretch=1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Iniciar Hilo de Red
        self.worker = NetworkWorker()
        self.worker.frame_received.connect(self.update_image)
        self.worker.disconnected.connect(self.reset_label)
        self.worker.start()

    def update_image(self, frame):
        # Convertir BGR (OpenCV) a RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w

        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.current_pixmap = QPixmap.fromImage(q_img)

        # Redimensionar y mostrar la imagen en el widget
        self.render_current_frame()

    def render_current_frame(self):
        """Ajusta proporcionalmente el pixmap al tamaño actual del contenedor."""
        if self.current_pixmap and not self.current_pixmap.isNull():
            scaled_pixmap = self.current_pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """Evento de PyQt que se dispara dinámicamente cuando estiras la ventana con el ratón."""
        super().resizeEvent(event)
        self.render_current_frame()

    def reset_label(self):
        self.current_pixmap = None
        self.video_label.clear()
        self.video_label.setText("⏳ Waiting for video transmission.....")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())