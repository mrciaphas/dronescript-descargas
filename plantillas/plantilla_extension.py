"""Plantilla de extensión para DroneScript.

Una extensión añade bloques propios a la paleta. Copia este archivo, cambia el «id» y el
«nombre», escribe tus funciones e impórtalo en DroneScript: Extensiones y librerías → «+ Importar extensión».

Reglas:
- EXTENSION y BLOQUES sólo pueden tener valores fijos (textos, números, listas, diccionarios):
  DroneScript los lee SIN ejecutar el archivo para mostrarte qué hace antes de importarlo.
- Cada bloque llama a una función de este archivo. La función recibe primero `drone` (el mismo
  objeto que usan los bloques: drone.takeoff(), drone.move_forward(50), drone.get_battery(),
  drone.get_frame(), drone.log("texto")…) y después los valores escritos en el bloque.
- tipo "accion": un bloque que hace algo (con hasta 3 valores, número o texto).
- tipo "sensor": aparece en los bloques «si», «while» y «esperar hasta». Su función devuelve
  un número ("numero"), True / False ("si_no") o un texto ("texto").
- Si usas una librería que no viene con DroneScript, ponla en "librerias" (el nombre de pip):
  la app la instala con «Instalar lo que falta». Ejemplo completo con MediaPipe: manos.py.
- Al cambiar el archivo hay que volver a importarlo (la app sólo ejecuta lo que aprobaste).
"""

import random
import time

EXTENSION = {
    "id": "mi_extension",              # minúsculas, números y _ ; único
    "nombre": "Mi extensión",
    "descripcion": "Bloques de ejemplo: azar, hora, mensajes y un cuadrado.",
    "autor": "Tu nombre",
    "version": "1.0",
    "color": "#0f6b6b",                # color de los bloques (#rrggbb)
    "librerias": [],                   # p. ej. ["mediapipe"] — nombres de pip
    "archivos": [],                    # p. ej. [{"nombre": "modelo.task", "url": "https://…", "sha256": "…"}]
}

BLOQUES = [
    # sensores
    {"funcion": "azar", "tipo": "sensor", "texto": "número al azar (1–6)", "valor": "numero"},
    {"funcion": "hora", "tipo": "sensor", "texto": "hora del día (0–23)", "valor": "numero", "unidad": "h"},
    {"funcion": "bateria_ok", "tipo": "sensor", "texto": "batería suficiente", "valor": "si_no"},
    # acciones
    {"funcion": "decir", "tipo": "accion", "texto": "decir",
     "args": [{"nombre": "mensaje", "tipo": "texto", "defecto": "¡Hola!"}]},
    {"funcion": "cuadrado", "tipo": "accion", "texto": "volar un cuadrado de",
     "args": [{"nombre": "lado", "tipo": "numero", "defecto": 50, "unidad": "cm"}]},
]


def azar(drone):
    return random.randint(1, 6)


def hora(drone):
    return time.localtime().tm_hour


def bateria_ok(drone):
    return drone.get_battery() > 30


def decir(drone, mensaje):
    drone.log(mensaje)                 # sale en la consola de DroneScript


def cuadrado(drone, lado):
    # usa los mismos movimientos que los bloques: respetan los límites y Detener / Land
    for _ in range(4):
        drone.move_forward(lado)
        drone.rotate_clockwise(90)
