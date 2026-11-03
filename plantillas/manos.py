# ════════════════════════════════════════════════════════════════════════════
#  manos.py — extensión de DroneScript: detectar manos y contar dedos
# ════════════════════════════════════════════════════════════════════════════
#
#  Una extensión tiene SIEMPRE tres partes:
#    1. EXTENSION: quién es, qué librerías usa y qué archivos necesita.
#    2. BLOQUES:   los bloques nuevos que aparecerán en la paleta.
#    3. Funciones: lo que hace cada bloque (una función de Python por bloque).
#
#  DroneScript LEE las partes 1 y 2 sin ejecutar nada, para mostrarte qué hace el
#  archivo antes de que lo apruebes. Por eso EXTENSION y BLOQUES tienen que ser
#  valores fijos: textos, números, listas y diccionarios, sin cálculos ni variables.


# ── 1. Datos de la extensión ────────────────────────────────────────────────
EXTENSION = {
    # id: identificador único, en minúsculas y sin espacios. Debe coincidir con el
    # nombre del archivo (manos.py → "manos").
    "id": "manos",

    # nombre: lo que se ve en la paleta como título de la categoría nueva.
    "nombre": "Manos (MediaPipe)",

    "descripcion": "Ve una mano con la cámara y cuenta los dedos levantados.",
    "autor": "Tu nombre",
    "version": "1.0",

    # color de la categoría en la paleta (formato #rrggbb).
    "color": "#b4508a",

    # librerias: los nombres EXACTOS como en pip (pip install mediapipe).
    # DroneScript las instala cuando pulses «Instalar lo que falta».
    "librerias": ["mediapipe"],

    # archivos: cosas que hay que descargar aparte. MediaPipe necesita un «modelo»:
    # un archivo con lo que la red neuronal aprendió sobre cómo es una mano (~7 MB).
    # DroneScript lo descarga a Documentos\DroneScript\extensiones\manos\
    # y, como damos su sha256 (su «huella digital»), comprueba que llegó completo y
    # que es exactamente ese archivo y no otro.
    "archivos": [{
        "nombre": "mano.task",
        "url": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
        "sha256": "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1",
    }],
}


# ── 2. Los bloques nuevos ───────────────────────────────────────────────────
#  tipo "sensor": se usa dentro de las condiciones de «si», «while» y «esperar hasta».
#                 «valor» dice qué devuelve: "numero", "si_no" o "texto".
#  tipo "accion": es un bloque que se pone en el programa, como «fly forward».
#                 «args» son los campos que el alumno rellena (hasta 3).
#  «funcion» es el nombre de la función de Python que se ejecuta (más abajo).
BLOQUES = [
    {"funcion": "dedos", "tipo": "sensor", "texto": "dedos levantados", "valor": "numero"},
    {"funcion": "ve_mano", "tipo": "sensor", "texto": "ve una mano", "valor": "si_no"},
    {"funcion": "esperar_dedos", "tipo": "accion", "texto": "esperar dedos",
     "args": [{"nombre": "cuántos", "tipo": "numero", "defecto": 2}]},
]


# ── 3. El código ────────────────────────────────────────────────────────────
#  Todo lo de aquí abajo SÍ se ejecuta, pero sólo cuando una misión usa uno de
#  estos bloques, y sólo si el archivo es exactamente el que aprobaste.

import time

import cv2                    # OpenCV: ya viene con DroneScript (convierte colores)
import mediapipe as mp        # la librería que agregamos
from mediapipe.tasks.python import BaseOptions, vision

from control.extensiones import carpeta   # dónde quedaron los archivos descargados

# El detector de MediaPipe tarda ~1 s en prepararse: lo creamos UNA vez y lo guardamos
# aquí para reutilizarlo en cada fotograma (si no, cada bloque tardaría 1 s).
detector = None

# Los 21 puntos que MediaPipe encuentra en una mano (los que usamos):
#
#        8   12  16  20      ← puntas de los dedos (índice, medio, anular, meñique)
#        |   |   |   |
#        6   10  14  18      ← nudillo del medio de cada dedo
#         \  |   |  /
#      4   \ |   | /
#       \___\|___|/          ← 4 = punta del pulgar
#            0               ← 0 = muñeca
#
# Cada punto tiene .x y .y entre 0 y 1 (fracción del ancho y del alto de la imagen).
PUNTAS_Y_NUDILLOS = [(8, 6), (12, 10), (16, 14), (20, 18)]


def _mano(drone):
    """Busca una mano en lo que ve la cámara ahora. Devuelve sus 21 puntos, o None."""
    global detector

    # 1) Pedir el fotograma actual. Si la cámara está apagada, DroneScript la enciende.
    #    Si el dron no tiene cámara (p. ej. el CoDrone EDU), llega None.
    img = drone.get_frame()
    if img is None:
        return None

    # 2) Crear el detector la primera vez, con el modelo que se descargó.
    if detector is None:
        opciones = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(carpeta("manos") / "mano.task")),
            num_hands=1)                     # con una mano basta, y es más rápido
        detector = vision.HandLandmarker.create_from_options(opciones)

    # 3) OpenCV guarda los colores como BGR (azul, verde, rojo) y MediaPipe los quiere
    #    en RGB: si no se convierten, la piel se ve azulada y detecta peor.
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    resultado = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))

    # 4) hand_landmarks es una lista con los puntos de cada mano encontrada.
    if not resultado.hand_landmarks:
        return None
    return resultado.hand_landmarks[0]


def _lejos_de_la_muneca(p, a, b):
    """¿El punto a está más lejos de la muñeca que el punto b?

    Un dedo levantado tiene la punta MÁS LEJOS de la muñeca que su nudillo; uno doblado,
    más cerca. Comparamos distancias (y no sólo «más arriba») para que funcione aunque la
    mano esté girada o de lado. Usamos la distancia al cuadrado: para comparar da lo mismo
    y nos ahorramos la raíz.
    """
    def dist2(i):
        return (p[i].x - p[0].x) ** 2 + (p[i].y - p[0].y) ** 2
    return dist2(a) > dist2(b)


def dedos(drone):
    """Sensor «dedos levantados»: 0 a 4 (el pulgar no se cuenta: de lado engaña mucho)."""
    p = _mano(drone)
    if p is None:
        return 0
    n = sum(_lejos_de_la_muneca(p, punta, nudillo) for punta, nudillo in PUNTAS_Y_NUDILLOS)
    # drone.log escribe en la consola de DroneScript: muy útil para ver qué está
    # detectando mientras pruebas. Bórralo cuando ya funcione (llena la consola).
    drone.log(f"manos: {n} dedos")
    return n


def ve_mano(drone):
    """Sensor «ve una mano»: True o False."""
    return _mano(drone) is not None


def esperar_dedos(drone, cuantos):
    """Acción «esperar dedos»: espera hasta ver ese número de dedos (como mucho 20 s).

    drone.wait() es importante: además de esperar, revisa si alguien pulsó Detener,
    Land o Emergency. Un time.sleep() normal NO lo haría y la misión no se podría parar.
    """
    limite = time.monotonic() + 20
    while time.monotonic() < limite:
        if dedos(drone) == int(cuantos):
            drone.log(f"manos: vi {int(cuantos)} dedos")
            return
        drone.wait(0.1)
    drone.log(f"manos: no vi {int(cuantos)} dedos en 20 s; sigo", "warn")
