"""Etapa 4: evaluación del rendimiento del Recocido Simulado.

Realiza 30 pruebas con semillas diferentes y compara las rutas finales
con las rutas iniciales construidas por vecino más cercano.
No modifica los archivos de las etapas anteriores.
"""

import csv
import random
import statistics
import time
from pathlib import Path

from etapa1_validacion_datos import cargar_datos
from rutas_iniciales import (
    NUM_CENTROS,
    JORNADA_HORAS,
    asignar_tiendas,
    construir_ruta,
    calcular_recorrido,
    nombre_nodo,
)
from recocido_simulado import optimizar_ruta, validar_rutas, tiempo_estimado

SEMILLA_INICIAL = 42
NUM_PRUEBAS = 30


def guardar_csv(nombre, encabezados, filas):
    archivo = Path(__file__).resolve().parent / nombre
    with archivo.open("w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f)
        escritor.writerow(encabezados)
        escritor.writerows(filas)


def main():
    _, distancias, costos = cargar_datos()
    asignacion = asignar_tiendas(distancias)
    rutas_iniciales = {
        centro: construir_ruta(centro, tiendas, distancias)
        for centro, tiendas in asignacion.items()
    }
    validar_rutas(rutas_iniciales, len(distancias))

    distancia_inicial = sum(
        calcular_recorrido(ruta, distancias, costos)[0]
        for ruta in rutas_iniciales.values()
    )
    costo_inicial = sum(
        calcular_recorrido(ruta, distancias, costos)[1]
        for ruta in rutas_iniciales.values()
    )

    registros = []
    mejor_prueba = None
    print("EVALUACION DEL RECOCIDO SIMULADO - 30 PRUEBAS")
    print("Asignaciones de tiendas fijas; cambian las semillas aleatorias.")
    print("-" * 70)

    for numero in range(NUM_PRUEBAS):
        semilla = SEMILLA_INICIAL + numero
        generador = random.Random(semilla)
        rutas_finales = {}
        total_iteraciones = 0
        total_aceptados = 0
        total_peores = 0
        reloj = time.perf_counter()

        for centro in range(NUM_CENTROS):
            inicial = rutas_iniciales[centro]
            final, intentos, aceptados, peores, _ = optimizar_ruta(
                inicial, distancias, costos, generador, centro
            )
            if sorted(final[1:-1]) != sorted(inicial[1:-1]):
                raise ValueError(f"Prueba {numero + 1}: faltan tiendas del centro {centro + 1}.")
            if tiempo_estimado(final, distancias) > JORNADA_HORAS + 1e-9:
                raise ValueError(f"Prueba {numero + 1}: ruta fuera del horario del centro {centro + 1}.")
            rutas_finales[centro] = final
            total_iteraciones += intentos
            total_aceptados += aceptados
            total_peores += peores

        tiempo = time.perf_counter() - reloj
        validar_rutas(rutas_finales, len(distancias))

        distancia_final = sum(
            calcular_recorrido(ruta, distancias, costos)[0]
            for ruta in rutas_finales.values()
        )
        costo_final = sum(
            calcular_recorrido(ruta, distancias, costos)[1]
            for ruta in rutas_finales.values()
        )

        if distancia_final > distancia_inicial + 1e-8:
            raise ValueError("La mejor solucion no deberia superar la distancia inicial.")
        if costo_final > costo_inicial + 1e-8:
            raise ValueError("La mejor solucion no deberia superar el costo inicial.")

        mejora = 100 * (costo_inicial - costo_final) / costo_inicial
        registro = {
            "prueba": numero + 1,
            "semilla": semilla,
            "distancia": distancia_final,
            "costo": costo_final,
            "mejora": mejora,
            "tiempo": tiempo,
            "iteraciones": total_iteraciones,
            "aceptados": total_aceptados,
            "peores": total_peores,
        }
        registros.append(registro)

        if mejor_prueba is None or costo_final < mejor_prueba["costo"] - 1e-9:
            mejor_prueba = {**registro, "rutas": rutas_finales}

        print(f"Prueba {numero + 1:02d} | Semilla {semilla} | "
              f"Distancia: {distancia_final:.2f} km | "
              f"Costo: {costo_final:.2f} u.c. | "
              f"Mejora: {mejora:.2f}% | {tiempo:.3f} s")

    guardar_csv(
        "pruebas_rendimiento.csv",
        ["Prueba", "Semilla", "Distancia final (km)", "Costo final (u.c.)",
         "Mejora (%)", "Tiempo de calculo (s)", "Iteraciones totales",
         "Movimientos aceptados", "Aceptaciones de mayor costo"],
        [[r["prueba"], r["semilla"], round(r["distancia"], 6),
          round(r["costo"], 6), round(r["mejora"], 4),
          round(r["tiempo"], 6), r["iteraciones"], r["aceptados"], r["peores"]]
         for r in registros],
    )

    guardar_csv(
        "mejor_prueba_rutas.csv",
        ["Centro", "Tiendas", "Ruta inicial", "Mejor ruta encontrada",
         "Distancia inicial (km)", "Distancia final (km)",
         "Costo inicial (u.c.)", "Costo final (u.c.)", "Tiempo estimado (h)"],
        [[nombre_nodo(centro), len(mejor_prueba["rutas"][centro]) - 2,
          " -> ".join(nombre_nodo(x) for x in rutas_iniciales[centro]),
          " -> ".join(nombre_nodo(x) for x in mejor_prueba["rutas"][centro]),
          round(calcular_recorrido(rutas_iniciales[centro], distancias, costos)[0], 4),
          round(calcular_recorrido(mejor_prueba["rutas"][centro], distancias, costos)[0], 4),
          round(calcular_recorrido(rutas_iniciales[centro], distancias, costos)[1], 4),
          round(calcular_recorrido(mejor_prueba["rutas"][centro], distancias, costos)[1], 4),
          round(tiempo_estimado(mejor_prueba["rutas"][centro], distancias), 3)]
         for centro in range(NUM_CENTROS)],
    )

    mejoras = [r["mejora"] for r in registros]
    distancias_finales = [r["distancia"] for r in registros]
    tiempos = [r["tiempo"] for r in registros]

    resumen = (
        "RESUMEN DE RENDIMIENTO - RECOCIDO SIMULADO\n"
        f"Pruebas realizadas: {NUM_PRUEBAS}\n"
        f"Semillas utilizadas: {SEMILLA_INICIAL} a {SEMILLA_INICIAL + NUM_PRUEBAS - 1}\n"
        f"Distancia inicial: {distancia_inicial:.2f} km\n"
        f"Costo inicial: {costo_inicial:.2f} u.c.\n"
        f"Distancia final promedio: {statistics.mean(distancias_finales):.2f} km\n"
        f"Mejor distancia final: {min(distancias_finales):.2f} km\n"
        f"Peor distancia final: {max(distancias_finales):.2f} km\n"
        f"Mejora promedio: {statistics.mean(mejoras):.2f}%\n"
        f"Mejora minima: {min(mejoras):.2f}%\n"
        f"Mejora maxima: {max(mejoras):.2f}%\n"
        f"Desviacion estandar de la mejora: {statistics.stdev(mejoras):.2f} puntos porcentuales\n"
        f"Tiempo promedio de optimizacion: {statistics.mean(tiempos):.3f} s\n"
        f"Mejor ejecucion: prueba {mejor_prueba['prueba']}, semilla {mejor_prueba['semilla']}\n"
        "Validacion: en las 30 pruebas se atendieron 90 tiendas sin repeticiones y\n"
        "todas las rutas empezaron/terminaron en su centro y respetaron las 8 h estimadas.\n"
        "Nota: distancias de la matriz; el tiempo de entrega se estima con supuestos.\n"
    )
    (Path(__file__).resolve().parent / "resumen_rendimiento.txt").write_text(
        resumen, encoding="utf-8"
    )
    print("\n" + "=" * 70)
    print(resumen)
    print("Archivos creados: pruebas_rendimiento.csv, mejor_prueba_rutas.csv, resumen_rendimiento.txt")


if __name__ == "__main__":
    main()
