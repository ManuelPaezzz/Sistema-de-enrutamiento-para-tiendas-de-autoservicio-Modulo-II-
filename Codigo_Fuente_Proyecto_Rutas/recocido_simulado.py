"""Etapa 3: mejorar las rutas iniciales utilizando Recocido Simulado.

Las tiendas permanecen asignadas a su centro más cercano. Solo se optimiza
el orden de visita; cada recorrido inicia y termina en su centro.
"""

import csv
import math
import random
import time
from pathlib import Path

from etapa1_validacion_datos import cargar_datos
from rutas_iniciales import (
    NUM_CENTROS,
    VELOCIDAD_KMH,
    MINUTOS_DESCARGA,
    JORNADA_HORAS,
    asignar_tiendas,
    construir_ruta,
    calcular_recorrido,
    nombre_nodo,
)

# Parámetros de la simulación
SEMILLA = 42
TEMPERATURA_INICIAL = 1.5        # Unidades de costo
FACTOR_ENFRIAMIENTO = 0.997     # Se multiplica después de cada intento
TEMPERATURA_MINIMA = 0.005
MAX_ITERACIONES = 2500          # Por centro de distribución


def tiempo_estimado(ruta, distancias):
    """Estimación: recorrido a 25 km/h más 15 min por tienda."""
    distancia = sum(distancias[a][b] for a, b in zip(ruta, ruta[1:]))
    cantidad_tiendas = max(0, len(ruta) - 2)
    return distancia / VELOCIDAD_KMH + cantidad_tiendas * MINUTOS_DESCARGA / 60


def crear_vecino(ruta, generador):
    """Cambia el orden de las tiendas por inversión de tramo o intercambio."""
    vecino = ruta[:]
    cantidad_tiendas = len(ruta) - 2
    if cantidad_tiendas < 3:
        return vecino

    i, j = sorted(generador.sample(range(1, len(ruta) - 1), 2))
    if generador.random() < 0.7:
        vecino[i:j + 1] = reversed(vecino[i:j + 1])
    else:
        vecino[i], vecino[j] = vecino[j], vecino[i]
    return vecino


def validar_rutas(rutas, cantidad_nodos):
    """Cada centro conserva sus extremos y todas las tiendas aparecen una vez."""
    tiendas_visitadas = []
    for centro in range(NUM_CENTROS):
        ruta = rutas[centro]
        if len(ruta) < 2 or ruta[0] != centro or ruta[-1] != centro:
            raise ValueError(f"La ruta del centro {centro + 1} no regresa al depósito.")
        tiendas_visitadas.extend(ruta[1:-1])

    tiendas_esperadas = set(range(NUM_CENTROS, cantidad_nodos))
    if (len(tiendas_visitadas) != len(tiendas_esperadas)
            or set(tiendas_visitadas) != tiendas_esperadas):
        raise ValueError("Hay tiendas repetidas o faltantes en las rutas.")


def optimizar_ruta(ruta_inicial, distancias, costos, generador, centro):
    """Ejecuta Recocido Simulado para una ruta, con límite de 8 horas."""
    actual = ruta_inicial[:]
    mejor = actual[:]
    _, costo_actual = calcular_recorrido(actual, distancias, costos)
    mejor_costo = costo_actual
    temperatura = TEMPERATURA_INICIAL

    aceptados = 0
    aceptados_peores = 0
    intentos = 0
    historial = [(centro + 1, 0, temperatura, costo_actual, mejor_costo)]

    while intentos < MAX_ITERACIONES and temperatura > TEMPERATURA_MINIMA:
        intentos += 1
        vecino = crear_vecino(actual, generador)
        _, costo_vecino = calcular_recorrido(vecino, distancias, costos)

        # Evitar recorridos inviables y movimientos que no cambian la ruta.
        if vecino != actual and tiempo_estimado(vecino, distancias) <= JORNADA_HORAS:
            diferencia = costo_vecino - costo_actual
            if diferencia <= 0 or generador.random() < math.exp(-diferencia / temperatura):
                if diferencia > 1e-10:
                    aceptados_peores += 1
                actual = vecino
                costo_actual = costo_vecino
                aceptados += 1

                if costo_actual < mejor_costo - 1e-10:
                    mejor = actual[:]
                    mejor_costo = costo_actual

        temperatura *= FACTOR_ENFRIAMIENTO
        if intentos % 10 == 0:
            historial.append((centro + 1, intentos, temperatura, costo_actual, mejor_costo))

    historial.append((centro + 1, intentos, temperatura, costo_actual, mejor_costo))
    return mejor, intentos, aceptados, aceptados_peores, historial


def main():
    inicio = time.perf_counter()
    _, distancias, costos = cargar_datos()
    generador = random.Random(SEMILLA)
    asignacion = asignar_tiendas(distancias)

    rutas_iniciales = {
        centro: construir_ruta(centro, tiendas, distancias)
        for centro, tiendas in asignacion.items()
    }
    validar_rutas(rutas_iniciales, len(distancias))

    rutas_optimas = {}
    filas_resultados = []
    filas_historial = []
    distancia_inicial_total = costo_inicial_total = 0.0
    distancia_final_total = costo_final_total = 0.0

    print("RECOCIDO SIMULADO - OPTIMIZACION DE RUTAS")
    print("Se mantienen las asignaciones al centro mas cercano.")
    print("-" * 66)

    for centro in range(NUM_CENTROS):
        ruta_inicial = rutas_iniciales[centro]
        ruta_mejor, intentos, aceptados, peores, historial = optimizar_ruta(
            ruta_inicial, distancias, costos, generador, centro
        )
        rutas_optimas[centro] = ruta_mejor
        filas_historial.extend(historial)

        d_inicial, c_inicial = calcular_recorrido(ruta_inicial, distancias, costos)
        d_final, c_final = calcular_recorrido(ruta_mejor, distancias, costos)
        horas_final = tiempo_estimado(ruta_mejor, distancias)
        if horas_final > JORNADA_HORAS + 1e-9:
            raise ValueError(f"La ruta del centro {centro + 1} excede la jornada.")
        if sorted(ruta_inicial[1:-1]) != sorted(ruta_mejor[1:-1]):
            raise ValueError(f"La ruta del centro {centro + 1} perdió tiendas.")

        distancia_inicial_total += d_inicial
        costo_inicial_total += c_inicial
        distancia_final_total += d_final
        costo_final_total += c_final
        mejora = 100 * (c_inicial - c_final) / c_inicial if c_inicial > 0 else 0.0

        filas_resultados.append([
            nombre_nodo(centro), len(ruta_mejor) - 2,
            " -> ".join(nombre_nodo(n) for n in ruta_mejor),
            round(d_inicial, 3), round(d_final, 3),
            round(c_inicial, 3), round(c_final, 3),
            round(mejora, 2), round(horas_final, 2),
            intentos, aceptados, peores,
        ])
        print(f"Centro {centro + 1}: {len(ruta_mejor) - 2} tiendas | "
              f"{d_inicial:.2f} -> {d_final:.2f} km | "
              f"{c_inicial:.2f} -> {c_final:.2f} u.c. | "
              f"Mejora: {mejora:.2f}%")

    validar_rutas(rutas_optimas, len(distancias))
    tiempo = time.perf_counter() - inicio
    mejora_total = (100 * (costo_inicial_total - costo_final_total) / costo_inicial_total
                    if costo_inicial_total > 0 else 0.0)

    carpeta = Path(__file__).resolve().parent
    with (carpeta / "rutas_optimizadas.csv").open("w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f)
        escritor.writerow([
            "Centro", "Tiendas", "Ruta optimizada", "Distancia inicial (km)",
            "Distancia optimizada (km)", "Costo inicial (u.c.)",
            "Costo optimizado (u.c.)", "Mejora (%)", "Tiempo estimado (h)",
            "Iteraciones", "Movimientos aceptados", "Aceptaciones de mayor costo",
        ])
        escritor.writerows(filas_resultados)

    with (carpeta / "historial_recocido.csv").open("w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f)
        escritor.writerow([
            "Centro", "Iteracion", "Temperatura", "Costo actual (u.c.)",
            "Mejor costo (u.c.)",
        ])
        escritor.writerows(filas_historial)

    print("\n" + "=" * 66)
    print("RESUMEN GENERAL")
    print("Tiendas visitadas: 90 de 90")
    print(f"Distancia inicial total: {distancia_inicial_total:.2f} km")
    print(f"Distancia optimizada total: {distancia_final_total:.2f} km")
    print(f"Costo inicial total: {costo_inicial_total:.2f} u.c.")
    print(f"Costo optimizado total: {costo_final_total:.2f} u.c.")
    print(f"Mejora total: {mejora_total:.2f}%")
    print(f"Tiempo de ejecución: {tiempo:.3f} segundos")
    print("Se generaron: rutas_optimizadas.csv e historial_recocido.csv")
    print("Nota: distancias basadas en la matriz; tiempo de reparto estimado.")


if __name__ == "__main__":
    main()
