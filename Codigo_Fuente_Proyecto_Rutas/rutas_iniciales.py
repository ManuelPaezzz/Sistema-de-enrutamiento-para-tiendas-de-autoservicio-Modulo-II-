"""Etapa 2: asignación de tiendas y construcción de rutas iniciales."""

import csv
from pathlib import Path
from etapa1_validacion_datos import cargar_datos

NUM_CENTROS = 10
VELOCIDAD_KMH = 25          # Supuesto para estimar el tiempo
MINUTOS_DESCARGA = 15       # Supuesto por tienda
JORNADA_HORAS = 8           # Supuesto: de 7:00 a 15:00


def nombre_nodo(indice):
    if indice < NUM_CENTROS:
        return f"Centro {indice + 1}"
    return f"Tienda {indice - NUM_CENTROS + 1}"


def asignar_tiendas(distancias):
    """Asigna cada tienda al centro con menor distancia."""
    asignacion = {centro: [] for centro in range(NUM_CENTROS)}
    for tienda in range(NUM_CENTROS, len(distancias)):
        centro = min(range(NUM_CENTROS), key=lambda c: (distancias[c][tienda], c))
        asignacion[centro].append(tienda)
    return asignacion


def construir_ruta(centro, tiendas, distancias):
    """Visita la tienda pendiente más cercana desde la ubicación actual."""
    pendientes = set(tiendas)
    ruta = [centro]

    while pendientes:
        actual = ruta[-1]
        siguiente = min(pendientes, key=lambda t: (distancias[actual][t], t))
        ruta.append(siguiente)
        pendientes.remove(siguiente)

    ruta.append(centro)  # Regresar al centro de distribución
    return ruta


def calcular_recorrido(ruta, distancias, costos):
    distancia = 0
    costo = 0
    for origen, destino in zip(ruta, ruta[1:]):
        distancia += distancias[origen][destino]
        costo += costos[origen][destino]
    return distancia, costo


def main():
    _, distancias, costos = cargar_datos()
    asignacion = asignar_tiendas(distancias)

    rutas = {}
    tiendas_visitadas = []
    resultados = []
    distancia_total = 0
    costo_total = 0

    print("RUTAS INICIALES - VECINO MAS CERCANO")
    print("Asignacion de tiendas al centro mas cercano")
    print("-" * 56)

    for centro, tiendas in asignacion.items():
        ruta = construir_ruta(centro, tiendas, distancias)
        rutas[centro] = ruta
        tiendas_visitadas.extend(ruta[1:-1])

        distancia, costo = calcular_recorrido(ruta, distancias, costos)
        tiempo_horas = distancia / VELOCIDAD_KMH + len(tiendas) * MINUTOS_DESCARGA / 60
        cumple_tiempo = tiempo_horas <= JORNADA_HORAS

        distancia_total += distancia
        costo_total += costo
        texto_ruta = " -> ".join(nombre_nodo(nodo) for nodo in ruta)
        resultados.append([
            nombre_nodo(centro), len(tiendas), texto_ruta,
            round(distancia, 3), round(costo, 3),
            round(tiempo_horas, 2), "Si" if cumple_tiempo else "No"
        ])

        print(f"\nCentro {centro + 1}: {len(tiendas)} tiendas")
        print("Ruta:", texto_ruta)
        print(f"Distancia: {distancia:.2f} km | Costo: {costo:.2f} u.c.")
        print(f"Tiempo estimado: {tiempo_horas:.2f} h | Dentro de 8 h: {'Si' if cumple_tiempo else 'No'}")

    # Verificar que cada tienda aparezca una sola vez.
    tiendas_esperadas = set(range(NUM_CENTROS, len(distancias)))
    if len(tiendas_visitadas) != len(tiendas_esperadas) or set(tiendas_visitadas) != tiendas_esperadas:
        raise ValueError("Hay tiendas repetidas o sin asignar.")
    if any(ruta[0] != centro or ruta[-1] != centro for centro, ruta in rutas.items()):
        raise ValueError("Una ruta no comienza o termina en su propio centro.")

    print("\n" + "=" * 56)
    print("RESUMEN DE LA SOLUCION INICIAL")
    print("Centros:", len(rutas))
    print("Tiendas atendidas:", len(tiendas_visitadas))
    print(f"Distancia total: {distancia_total:.2f} km")
    print(f"Costo total: {costo_total:.2f} unidades de costo")
    print("Rutas dentro de 8 horas:", sum(r[-1] == "Si" for r in resultados), "de", len(rutas))

    archivo_salida = Path(__file__).resolve().parent / "rutas_iniciales.csv"
    with archivo_salida.open("w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow([
            "Centro", "Numero de tiendas", "Recorrido", "Distancia (km)",
            "Costo (u.c.)", "Tiempo estimado (h)", "Dentro de 8 horas"
        ])
        escritor.writerows(resultados)
    print("Archivo de resultados guardado:", archivo_salida.name)
    print("Nota: el tiempo es estimado y no verifica capacidad de carga ni trafico real.")


if __name__ == "__main__":
    main()
