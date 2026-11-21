"""Nucleo de la simulacion de eventos discretos: asignacion FIFO de camas.

Cada paciente pide cama en `pedido[i]` (horas). Recibe la primera cama libre en orden de pedido (FIFO). Ocupa la cama su
estancia `estancia_h[i]` y el alta ocurre ese dia a la hora `hora_alta[i]` (nunca antes de 2 h de ocupar la cama).
Devuelve la hora de asignacion de cama de cada paciente.
"""
import heapq

import numpy as np


def asignar_camas(pedido: np.ndarray, estancia_h: np.ndarray, hora_alta: np.ndarray, camas: int) -> np.ndarray:
    pedido = np.asarray(pedido, dtype=float)
    inicio = np.empty(len(pedido))
    ocupadas: list[float] = []  # horas de liberacion de las camas ocupadas (min-heap)
    for i in np.argsort(pedido, kind="stable"):
        r = pedido[i]
        if len(ocupadas) < camas:
            s = r
        else:
            s = max(r, heapq.heappop(ocupadas))
        fin = np.floor((s + estancia_h[i]) / 24) * 24 + hora_alta[i]
        if fin < s + 2:
            fin += 24
        heapq.heappush(ocupadas, fin)
        inicio[i] = s
    return inicio
