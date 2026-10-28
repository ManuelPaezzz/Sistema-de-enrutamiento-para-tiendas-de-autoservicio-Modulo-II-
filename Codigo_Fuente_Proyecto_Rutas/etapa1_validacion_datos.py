"""Etapa 1: lectura y validación de datos del proyecto de rutas."""

from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import math
import re

CARPETA = Path(__file__).resolve().parent
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def leer_excel(nombre):
    """Lee la primera hoja de un archivo .xlsx sin paquetes adicionales."""
    archivo = CARPETA / nombre
    if not archivo.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {archivo.name}")

    with ZipFile(archivo) as libro:
        textos = []
        if "xl/sharedStrings.xml" in libro.namelist():
            raiz_textos = ET.fromstring(libro.read("xl/sharedStrings.xml"))
            for elemento in raiz_textos.findall(NS + "si"):
                textos.append("".join(t.text or "" for t in elemento.iter(NS + "t")))

        hoja = ET.fromstring(libro.read("xl/worksheets/sheet1.xml"))
        filas = []
        for fila in hoja.findall(".//" + NS + "sheetData/" + NS + "row"):
            valores = []
            for celda in fila.findall(NS + "c"):
                letras = re.match(r"[A-Z]+", celda.attrib["r"]).group()
                indice = 0
                for letra in letras:
                    indice = indice * 26 + ord(letra) - ord("A") + 1
                indice -= 1

                while len(valores) <= indice:
                    valores.append(None)

                tipo = celda.attrib.get("t")
                dato = celda.find(NS + "v")
                if tipo == "inlineStr":
                    valor = "".join(t.text or "" for t in celda.iter(NS + "t"))
                elif dato is None or dato.text is None:
                    valor = None
                elif tipo == "s":
                    valor = textos[int(dato.text)]
                elif tipo in ("str", "e"):
                    valor = dato.text
                else:
                    valor = float(dato.text)
                valores[indice] = valor
            filas.append(valores)
    return filas


def validar_matriz(tabla, nombre):
    encabezado = [f"Nodo_{i}" for i in range(1, 101)]
    if len(tabla) != 101 or tabla[0] != encabezado:
        raise ValueError(f"Formato incorrecto en {nombre}: se esperan 100 nodos.")

    matriz = tabla[1:]
    for i in range(100):
        if len(matriz[i]) != 100:
            raise ValueError(f"La fila {i + 1} de {nombre} no tiene 100 valores.")
        for j in range(100):
            valor = matriz[i][j]
            if not isinstance(valor, (int, float)) or not math.isfinite(valor):
                raise ValueError(f"Valor inválido en {nombre}, fila {i + 1}, columna {j + 1}.")
            if valor < 0 or (i != j and valor == 0):
                raise ValueError(f"Distancia o costo inválido en {nombre} ({i + 1}, {j + 1}).")
            if not math.isclose(valor, matriz[j][i], abs_tol=1e-8):
                raise ValueError(f"{nombre} no es simétrica en ({i + 1}, {j + 1}).")
        if not math.isclose(matriz[i][i], 0, abs_tol=1e-8):
            raise ValueError(f"Diagonal incorrecta en {nombre}, nodo {i + 1}.")
    return matriz


def cargar_datos():
    tabla = leer_excel("datos_distribucion_tiendas.xlsx")
    distancias = validar_matriz(leer_excel("matriz_distancias.xlsx"), "distancias")
    costos = validar_matriz(leer_excel("matriz_costos_combustible.xlsx"), "costos")

    if len(tabla) != 101:
        raise ValueError("La tabla debe contener 100 ubicaciones y su encabezado.")
    ubicaciones = tabla[1:]
    if any(len(fila) != 7 for fila in ubicaciones):
        raise ValueError("La tabla de ubicaciones debe contener 7 columnas.")

    for i, fila in enumerate(ubicaciones):
        tipo_esperado = "Centro de Distribución" if i < 10 else "Tienda"
        nombre_esperado = (f"Centro de Distribución {i + 1}" if i < 10
                           else f"Tienda {i - 9}")
        if fila[0] != tipo_esperado or fila[1] != nombre_esperado:
            raise ValueError(f"Orden inesperado en la ubicación {i + 1}.")

    for i in range(100):
        for j in range(100):
            if not math.isclose(costos[i][j], 0.15 * distancias[i][j], abs_tol=1e-8):
                raise ValueError(f"El costo y la distancia no coinciden entre nodos {i+1} y {j+1}.")

    return ubicaciones, distancias, costos


def main():
    ubicaciones, distancias, costos = cargar_datos()
    print("VALIDACIÓN DE DATOS COMPLETADA")
    print("Centros de distribución:", 10)
    print("Tiendas:", 90)
    print("Tamaño de las matrices: 100 x 100")
    print("Costo por kilómetro en la matriz: 0.15 unidades de costo/km")
    print("Nodo 1:", ubicaciones[0][1])
    print("Nodo 10:", ubicaciones[9][1])
    print("Nodo 11:", ubicaciones[10][1])
    print("Nodo 100:", ubicaciones[99][1])
    print("Distancia entre nodos 1 y 2:", round(distancias[0][1], 3), "km")
    print("Costo entre nodos 1 y 2:", round(costos[0][1], 3))
    print("Los archivos están listos para construir las rutas iniciales.")


if __name__ == "__main__":
    main()
