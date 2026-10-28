"""Etapa 5: graficas para analizar las rutas y el Recocido Simulado.

Lee los CSV generados en las etapas 3 y 4. No modifica los resultados.
Instalacion (solo una vez): python -m pip install matplotlib
Ejecucion: python visualizacion_resultados.py
"""

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

CARPETA = Path(__file__).resolve().parent


def leer_csv(nombre):
    with (CARPETA / nombre).open("r", encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo))


def guardar_grafica(nombre):
    plt.tight_layout()
    plt.savefig(CARPETA / nombre, dpi=170, bbox_inches="tight")
    plt.close()
    print("Grafica guardada:", nombre)


def graficar_comparacion(pruebas, rutas):
    """Compara la distancia inicial con la mejor de las 30 pruebas."""
    inicial = sum(float(fila["Distancia inicial (km)"]) for fila in rutas)
    mejor = min(float(fila["Distancia final (km)"]) for fila in pruebas)
    promedio = sum(float(fila["Distancia final (km)"]) for fila in pruebas) / len(pruebas)
    etiquetas = ["Ruta inicial", "Promedio (30 pruebas)", "Mejor prueba"]
    valores = [inicial, promedio, mejor]

    plt.figure(figsize=(9, 5))
    barras = plt.bar(etiquetas, valores)
    plt.bar_label(barras, fmt="%.2f km", padding=3)
    plt.ylabel("Distancia total (km)")
    plt.title("Distancia total antes y despues de optimizar")
    plt.ylim(0, max(valores) * 1.15)
    plt.grid(axis="y", alpha=0.25)
    guardar_grafica("grafica_comparacion_distancias.png")


def graficar_pruebas(pruebas):
    """Muestra la mejora conseguida en cada una de las 30 ejecuciones."""
    numeros = [int(fila["Prueba"]) for fila in pruebas]
    mejoras = [float(fila["Mejora (%)"]) for fila in pruebas]
    promedio = sum(mejoras) / len(mejoras)

    plt.figure(figsize=(11, 5))
    plt.plot(numeros, mejoras, marker="o", markersize=4, label="Mejora por prueba")
    plt.axhline(promedio, linestyle="--", label=f"Promedio: {promedio:.2f}%")
    plt.xlabel("Numero de prueba")
    plt.ylabel("Reduccion de costo (%)")
    plt.title("Rendimiento del algoritmo en 30 ejecuciones")
    plt.xticks(range(1, len(numeros) + 1, 2))
    plt.grid(alpha=0.25)
    plt.legend()
    guardar_grafica("grafica_rendimiento_30_pruebas.png")


def graficar_convergencia(historial):
    """Suma los mejores costos de los 10 centros en cada iteracion.

    Este historial corresponde a la semilla 42, NO a la mejor semilla 46.
    """
    costo_por_iteracion = defaultdict(float)
    centros_por_iteracion = defaultdict(set)
    for fila in historial:
        iteracion = int(fila["Iteracion"])
        centro = int(fila["Centro"])
        costo_por_iteracion[iteracion] += float(fila["Mejor costo (u.c.)"])
        centros_por_iteracion[iteracion].add(centro)

    puntos = sorted(i for i in costo_por_iteracion if len(centros_por_iteracion[i]) == 10)
    if not puntos:
        raise ValueError("El historial no contiene iteraciones de los diez centros.")
    costos = [costo_por_iteracion[i] for i in puntos]

    plt.figure(figsize=(10, 5))
    plt.plot(puntos, costos, linewidth=2, label="Mejor costo acumulado")
    plt.xlabel("Iteracion (por centro)")
    plt.ylabel("Costo total (u.c.)")
    plt.title("Convergencia del Recocido Simulado - semilla 42")
    plt.grid(alpha=0.25)
    plt.legend()
    guardar_grafica("grafica_convergencia_semilla_42.png")
    print(f"Convergencia (semilla 42): {costos[0]:.2f} -> {costos[-1]:.2f} u.c.")


def graficar_centros(rutas):
    """Compara distancias por centro de la mejor prueba (semilla 46)."""
    centros = [fila["Centro"] for fila in rutas]
    iniciales = [float(fila["Distancia inicial (km)"]) for fila in rutas]
    finales = [float(fila["Distancia final (km)"]) for fila in rutas]
    posiciones = range(len(centros))
    ancho = 0.4

    plt.figure(figsize=(12, 5.5))
    plt.bar([x - ancho / 2 for x in posiciones], iniciales, width=ancho, label="Inicial")
    plt.bar([x + ancho / 2 for x in posiciones], finales, width=ancho, label="Optimizada")
    plt.xticks(list(posiciones), [c.replace("Centro ", "C") for c in centros])
    plt.xlabel("Centro de distribucion")
    plt.ylabel("Distancia (km)")
    plt.title("Distancia por centro - mejor prueba (semilla 46)")
    plt.grid(axis="y", alpha=0.25)
    plt.legend()
    guardar_grafica("grafica_distancia_por_centro.png")


def main():
    pruebas = leer_csv("pruebas_rendimiento.csv")
    rutas = leer_csv("mejor_prueba_rutas.csv")
    historial = leer_csv("historial_recocido.csv")

    if len(pruebas) != 30 or len(rutas) != 10:
        raise ValueError("Se esperaban 30 pruebas y rutas de 10 centros.")

    print("ETAPA 5 - GRAFICAS DE RESULTADOS")
    print("-" * 45)
    graficar_comparacion(pruebas, rutas)
    graficar_pruebas(pruebas)
    graficar_convergencia(historial)
    graficar_centros(rutas)
    print("Listo: se crearon 4 imagenes PNG en la carpeta del proyecto.")
    print("Nota: la convergencia usa la semilla 42; la mejor prueba usa la 46.")


if __name__ == "__main__":
    main()
