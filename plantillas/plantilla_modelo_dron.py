"""Plantilla de modelo de dron para DroneScript.

Cópiala, cambia MODELO y la clase, e impórtala con «+ Importar modelo de dron» en la
ventana de elegir dron. Tal como está funciona: es un dron virtual que sólo escribe en
la consola lo que haría, para que pruebes el importador y tus misiones.

Cómo funciona un modelo:
- MODELO dice cómo se llama y qué clase usar. DroneScript lo lee SIN ejecutar el archivo.
- La clase hereda de BaseDriver (control/drivers/base.py) e implementa sus métodos.
  DroneScript aplica antes los límites del panel (altura, velocidad, hover) y las
  teclas de seguridad; el modelo sólo tiene que hablar con el dron.
- El código se ejecuta al pulsar «Conectar». Sólo puede usar las librerías que trae
  DroneScript: las de Python (socket, struct, threading, json…) y numpy, cv2 (OpenCV),
  av (vídeo H.264) y serial (puerto serie).

Ejemplos reales para copiar ideas: control/drivers/tello.py (UDP con texto),
anafi.py (UDP binario con acuses) y codrone.py (puerto serie con una librería).
"""

import time

from control.drivers.base import BaseDriver, DroneError, DroneRejected

MODELO = {
    "id": "dron_plantilla",           # minúsculas, números y _ ; es lo que va en Drone("…")
    "nombre": "Dron de plantilla",    # lo que se ve en la lista de drones
    "clase": "DronPlantilla",         # la clase de abajo
    "descripcion": "Dron virtual de ejemplo: escribe en la consola lo que haría.",
    "autor": "DroneScript",
    "version": "1.0",
}


class DronPlantilla(BaseDriver):
    name = "Dron de plantilla"
    min_move = 20        # cm mínimos y máximos por orden de desplazamiento
    max_move = 500
    max_rotate = 360
    min_speed = 10       # cm/s
    max_speed = 100
    # Qué tiene el dron. Los bloques de lo que no tenga se marcan «se omitirá».
    supports_flip = False
    has_tof = False
    has_camera = False
    has_gimbal = False
    has_front = False
    has_color = False
    has_led = False
    has_buzzer = False

    def __init__(self):
        super().__init__()
        self.speed = 30
        self._h = 0          # cm
        self._yaw = 0        # °
        self._bat = 100      # %

    # ── conexión ──────────────────────────────────────────────────
    def connect(self):
        # Un dron real: abrir el socket o el puerto serie y comprobar que responde.
        # Si no responde, lanzar DroneError con un mensaje que diga qué revisar.
        self.connected = True
        self.log("success", f"Conectado a {self.name} (virtual)")

    def close(self):
        self.connected = False

    # ── telemetría ────────────────────────────────────────────────
    def telemetry(self):
        # «fresh» = los datos son recientes. Si no hay telemetría, DroneScript avisa
        # y no puede aplicar los límites de altura.
        return {"bat": self._bat, "h": self._h, "tof": self._h, "pitch": 0, "roll": 0,
                "yaw": self._yaw, "fresh": self.connected}

    # ── vuelo ─────────────────────────────────────────────────────
    # Usa self.sleep() para esperar: se corta al pulsar Detener / Land / Emergency.
    def takeoff(self):
        self.flying = True   # pesimista: si se pierde la respuesta, quizá sí despegó
        self.log("info", "(plantilla) despegando…")
        self.sleep(1.0)
        self._h = 80

    def land(self):
        self.log("info", "(plantilla) aterrizando…")
        self.sleep(1.0)
        self._h = 0
        self.flying = False

    def move(self, direction, cm):
        # direction: forward, back, left, right, up, down
        if not self.flying:
            raise DroneRejected(f"'{direction} {cm}': el dron está en tierra")
        self.sleep(cm / max(self.speed, 1))
        if direction == "up":
            self._h += cm
        elif direction == "down":
            self._h = max(0, self._h - cm)

    def rotate(self, degrees):
        # grados positivos = sentido horario
        self.sleep(abs(degrees) / 90)
        self._yaw = int((self._yaw + degrees + 180) % 360 - 180)

    def set_speed(self, cm_s):
        self.speed = int(min(self.max_speed, max(self.min_speed, cm_s)))
        return self.speed

    # ── seguridad (se llaman desde otro hilo: que sean rápidos) ───
    def emergency(self):
        self.abort_event.set()   # corta la espera en curso de la misión
        self.flying = False      # un dron real: apagar motores YA
        self._h = 0
        self.log("error", "(plantilla) motores apagados")

    def safe_land(self):
        self.abort_event.set()
        if not self.flying:
            return True
        time.sleep(1.0)          # aquí no se usa self.sleep: la misión ya se abortó
        self._h = 0
        self.flying = False
        return True              # True si se confirmó el aterrizaje

    # Opcionales (BaseDriver ya responde «no disponible»): camera_on, take_photo,
    # start_video, stop_video, set_gimbal, set_led, beep, flip, query.


if __name__ == "__main__":
    raise DroneError("Esto es un modelo para importar en DroneScript, no un programa")
