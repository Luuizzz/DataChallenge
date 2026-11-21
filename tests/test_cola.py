"""Propiedades de la cola FIFO de camas (nucleo de la simulacion)."""
import numpy as np

from hun.cola import asignar_camas


def test_sin_restriccion_de_camas_no_hay_espera():
    pedido = np.array([0.0, 1.0, 2.0, 5.0])
    inicio = asignar_camas(pedido, np.full(4, 30.0), np.full(4, 15.0), camas=100)
    assert np.allclose(inicio, pedido)


def test_una_cama_atiende_en_orden_de_llegada():
    pedido = np.array([3.0, 0.0, 1.0])
    inicio = asignar_camas(pedido, np.full(3, 10.0), np.full(3, 15.0), camas=1)
    # el primero en pedir (indice 1) entra al pedir; los demas esperan y entran en orden FIFO
    assert inicio[1] == 0.0
    assert inicio[1] < inicio[2] < inicio[0]
    assert np.all(inicio >= pedido)


def test_mas_camas_nunca_aumentan_la_espera():
    rng = np.random.default_rng(0)
    pedido = np.sort(rng.uniform(0, 24 * 60, 400))
    estancia = rng.lognormal(3.5, 0.8, 400)
    alta = rng.uniform(10, 18, 400)
    esperas = [np.mean(asignar_camas(pedido, estancia, alta, c) - pedido) for c in (5, 10, 20, 40)]
    assert all(a >= b - 1e-9 for a, b in zip(esperas, esperas[1:]))


def test_el_alta_ocurre_a_la_hora_indicada_y_tras_al_menos_2_h():
    pedido = np.array([0.0, 0.5])
    inicio = asignar_camas(pedido, np.array([0.1, 1.0]), np.array([0.5, 9.0]), camas=1)
    # el primer paciente ocupa la cama 0.1 h; su alta caeria antes de 2 h, asi que pasa al dia siguiente a las 0.5 h
    assert inicio[1] == 24.5
