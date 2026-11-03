"""Modelo de dron para DroneScript: un dron por Wi-Fi que recibe órdenes de texto por UDP.

Muchos drones educativos funcionan así (el DJI Tello y sus clones): el PC manda una orden de
texto, como "takeoff" o "forward 50", a la IP y el puerto del dron, y el dron responde "ok" o
"error". Cambia IP, PUERTO y las órdenes por las que use tu dron (vienen en su manual o SDK).
"""

import socket
import threading
import time

from control.drivers.base import BaseDriver, DroneError, DroneRejected

MODELO = {
    "id": "dron_udp",                 # minúsculas, números y _ ; único
    "nombre": "Mi dron por Wi-Fi",    # lo que se ve en la lista de drones
    "clase": "DronUDP",               # la clase de abajo
    "descripcion": "Dron que recibe órdenes de texto por UDP.",
    "autor": "Tu nombre",
    "version": "1.0",
}

IP = "192.168.10.1"     # la IP del dron cuando el PC está conectado a su Wi-Fi
PUERTO = 8889           # el puerto UDP donde escucha las órdenes


class DronUDP(BaseDriver):
    name = "Mi dron por Wi-Fi"
    min_move = 20        # cm mínimos y máximos que acepta en una orden de movimiento
    max_move = 500
    max_rotate = 360
    min_speed = 10       # cm/s
    max_speed = 100
    supports_flip = False   # lo que no tenga: sus bloques se marcan «no soportado»
    has_tof = False
    has_camera = False

    def __init__(self):
        super().__init__()
        self.speed = 30
        self.sock = None
        self.lock = threading.Lock()   # una orden a la vez: la telemetría usa el mismo socket
        self.bat = None
        self.bat_time = 0.0

    # ── conexión ──────────────────────────────────────────────────
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.2)   # recvfrom espera como mucho 0,2 s y vuelve a mirar si hay que abortar
        try:
            reply = self.send("command", timeout=3, abortable=False)   # pone el dron en modo SDK
        except DroneError:
            reply = None
        if reply != "ok":
            self.close()
            raise DroneError(f"El dron no responde en {IP}: enciéndelo y conecta el PC a su Wi-Fi")
        self.connected = True
        self.log("success", f"Conectado a {self.name}")

    def close(self):
        self.connected = False
        if self.sock:
            self.sock.close()
            self.sock = None

    # ── enviar órdenes ────────────────────────────────────────────
    def send(self, cmd, timeout=7.0, abortable=True):
        """Manda una orden y devuelve la respuesta del dron (texto)."""
        with self.lock:
            return self._send(cmd, timeout, abortable)

    def _send(self, cmd, timeout, abortable):
        self.sock.setblocking(False)   # tirar respuestas atrasadas de órdenes anteriores
        try:
            while self.sock.recv(1024):
                pass
        except OSError:
            pass
        self.sock.settimeout(0.2)
        self.sock.sendto(cmd.encode(), (IP, PUERTO))
        limit = time.monotonic() + timeout
        while time.monotonic() < limit:
            if abortable:
                self.check_abort()   # Detener / Land / Emergency cortan la espera aquí
            try:
                data, _ = self.sock.recvfrom(1024)
                return data.decode(errors="replace").strip()
            except socket.timeout:
                pass
        raise DroneError(f"'{cmd}': el dron no respondió en {timeout:.0f} s")

    def order(self, cmd, timeout=7.0):
        """Una orden que tiene que responder "ok"; si no, es un error."""
        reply = self.send(cmd, timeout)
        if reply.lower() != "ok":
            raise DroneRejected(f"'{cmd}' → {reply}")

    # ── telemetría ────────────────────────────────────────────────
    def telemetry(self):
        # DroneScript la pide 4 veces por segundo. La batería se pregunta como mucho cada 2 s,
        # y sólo si no hay una orden en curso (si no, las respuestas se mezclarían).
        if self.connected and time.monotonic() - self.bat_time > 2 and self.lock.acquire(blocking=False):
            try:
                self.bat = int(float(self._send("battery?", 2, abortable=False)))
                self.bat_time = time.monotonic()
            except (DroneError, ValueError):
                pass
            finally:
                self.lock.release()
        # Sin altura (None), DroneScript avisa de que no puede aplicar los límites de altura.
        # Si tu dron la da, pregúntala igual que la batería (en el Tello: "height?").
        return {"bat": self.bat, "h": None, "tof": None, "pitch": None, "roll": None, "yaw": None,
                "fresh": time.monotonic() - self.bat_time < 5}

    # ── vuelo ─────────────────────────────────────────────────────
    def takeoff(self):
        self.flying = True   # pesimista: si se pierde la respuesta, quizá sí despegó
        try:
            self.order("takeoff", timeout=20)
        except DroneRejected:
            self.flying = False
            raise

    def land(self):
        self.order("land", timeout=20)
        self.flying = False

    def move(self, direction, cm):
        # direction: forward, back, left, right, up, down (como las órdenes del Tello)
        self.order(f"{direction} {int(cm)}", timeout=cm / max(self.speed, 1) + 7)

    def rotate(self, degrees):
        # grados positivos = sentido horario
        sentido = "cw" if degrees >= 0 else "ccw"
        self.order(f"{sentido} {int(round(abs(degrees)))}", timeout=abs(degrees) / 30 + 7)

    def set_speed(self, cm_s):
        v = int(min(self.max_speed, max(self.min_speed, cm_s)))
        self.order(f"speed {v}")
        self.speed = v
        return v

    # ── seguridad (se llaman desde otro hilo: tienen que ser rápidos) ──
    def emergency(self):
        self.abort_event.set()
        for _ in range(3):   # UDP no garantiza la entrega: se repite
            try:
                self.sock.sendto(b"emergency", (IP, PUERTO))
            except (OSError, AttributeError):
                pass
        self.flying = False

    def safe_land(self):
        self.abort_event.set()   # la misión suelta el socket en menos de 0,2 s
        try:
            ok = self.send("land", timeout=15, abortable=False).lower() == "ok"
        except DroneError:
            return False
        if ok:
            self.flying = False
        return ok
