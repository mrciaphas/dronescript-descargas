# ════════════════════════════════════════════════════════════════════════════
#  rutinas.py — extensión propia de DroneScript: rutinas de vuelo
# ════════════════════════════════════════════════════════════════════════════
#
#  Bloques nuevos:
#    · polígono      (acción)  vuela un polígono regular de N lados
#    · buscar ArUco  (acción)  gira poco a poco hasta ver un marcador
#    · anotar        (acción)  guarda la telemetría en una tabla (CSV, se abre con Excel)
#    · segundos de misión (sensor) cuánto tiempo lleva la misión
#
#  No necesita instalar nada: sólo usa lo que ya trae Python y la API de DroneScript
#  (el objeto `drone`, el mismo de las misiones).


# ── 1. Datos de la extensión (valores fijos: DroneScript los lee sin ejecutar) ──
EXTENSION = {
    "id": "rutinas",                 # = nombre del archivo (rutinas.py), en minúsculas
    "nombre": "Rutinas de vuelo",    # título de la categoría en la paleta
    "descripcion": "Polígonos, búsqueda de ArUco y registro de vuelo en CSV.",
    "autor": "Tu nombre",
    "version": "1.0",
    "color": "#2d7d46",
    "librerias": [],                 # nada que instalar con pip
    "archivos": [],                  # nada que descargar
}


# ── 2. Bloques nuevos ───────────────────────────────────────────────────────
#  «args»: los campos que se rellenan en el bloque (máximo 3).
#    tipo "numero": casilla de número (admite cuentas con variables, como vueltas * 10)
#    tipo "texto":  casilla de texto
#    «unidad» se muestra detrás de la casilla.
BLOQUES = [
    {"funcion": "poligono", "tipo": "accion", "texto": "polígono",
     "args": [{"nombre": "lados", "tipo": "numero", "defecto": 4},
              {"nombre": "de", "tipo": "numero", "defecto": 50, "unidad": "cm"}]},
    {"funcion": "buscar_aruco", "tipo": "accion", "texto": "buscar ArUco",
     "args": [{"nombre": "id", "tipo": "numero", "defecto": 100}]},
    {"funcion": "anotar", "tipo": "accion", "texto": "anotar",
     "args": [{"nombre": "nota", "tipo": "texto", "defecto": "punto 1"}]},
    {"funcion": "segundos", "tipo": "sensor", "texto": "segundos de misión", "valor": "numero", "unidad": "s"},
]


# ── 3. El código ────────────────────────────────────────────────────────────
import csv
import time
from datetime import datetime

from control.extensiones import carpeta   # carpeta propia de la extensión: extensiones\rutinas\

# Este archivo se ejecuta al empezar la misión (cuando el código generado hace
# cargar("rutinas")), así que la hora de ahora es «el inicio de la misión».
INICIO = time.monotonic()
ARCHIVO = None   # la tabla de esta misión; se crea con la primera nota


def poligono(drone, lados, lado):
    """Vuela un polígono regular: «lados» tramos de «lado» cm, girando 360/lados grados.

    Usa los mismos movimientos que los bloques, así que se respetan los límites del panel
    (velocidad, altura) y Detener funciona en cualquier momento.
    """
    lados = int(lados)
    if lados < 3:
        drone.log("polígono: hacen falta al menos 3 lados", "warn")
        return
    giro = 360 / lados                     # triángulo 120°, cuadrado 90°, hexágono 60°…
    drone.log(f"polígono de {lados} lados de {lado} cm (giros de {giro:.0f}°)")
    for _ in range(lados):
        drone.move_forward(lado)
        drone.rotate_clockwise(giro)


def buscar_aruco(drone, marcador):
    """Gira de 30 en 30 grados hasta ver el ArUco (como mucho una vuelta completa).

    Después de cada giro espera medio segundo: la imagen del dron llega con algo de retraso
    y sin esa pausa miraría una foto de antes del giro.
    """
    marcador = int(marcador)
    for paso in range(12):                 # 12 × 30° = 360°
        if drone.sees_aruco(marcador):
            drone.log(f"buscar ArUco: encontré el {marcador} tras girar {paso * 30}°", "success")
            return
        drone.rotate_clockwise(30)
        drone.wait(0.5)                    # wait, no time.sleep: así Detener la corta
    drone.log(f"buscar ArUco: di una vuelta y no vi el {marcador}", "warn")


def anotar(drone, nota):
    """Añade una fila a la tabla de la misión: hora, segundos, batería, altura, yaw y la nota.

    La tabla queda en Documentos\\DroneScript\\extensiones\\rutinas\\vuelo_<fecha>.csv.
    El CSV usa «;», que es lo que Excel en español espera para separar columnas.
    """
    global ARCHIVO
    nueva = ARCHIVO is None
    if nueva:
        carpeta("rutinas").mkdir(parents=True, exist_ok=True)
        ARCHIVO = carpeta("rutinas") / f"vuelo_{datetime.now():%Y%m%d_%H%M%S}.csv"
    fila = [datetime.now().strftime("%H:%M:%S"), segundos(drone), drone.get_battery(),
            drone.get_height(), drone.get_yaw(), nota]
    # «utf-8-sig» para que Excel muestre bien los acentos; newline="" lo pide el módulo csv
    with open(ARCHIVO, "a", newline="", encoding="utf-8-sig") as f:
        tabla = csv.writer(f, delimiter=";")
        if nueva:
            tabla.writerow(["hora", "segundos", "bateria_%", "altura_cm", "yaw_grados", "nota"])
        tabla.writerow(fila)
    drone.log(f"anotado: {nota} → {ARCHIVO.name}")


def segundos(drone):
    """Sensor: segundos (enteros) desde que empezó la misión."""
    return int(time.monotonic() - INICIO)
