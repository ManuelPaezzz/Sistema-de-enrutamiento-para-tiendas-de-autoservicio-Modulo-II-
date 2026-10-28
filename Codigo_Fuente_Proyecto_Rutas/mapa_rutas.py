"""Etapa 6: mapa interactivo de rutas iniciales y optimizadas.

Requiere estos archivos junto al programa:
- mapa_geoespacial_actualizado.html (ubicaciones originales del mapa)
- mejor_prueba_rutas.csv (resultado de la etapa 4, semilla 46)
- etapa1_validacion_datos.py y los tres Excel originales

Solo utiliza bibliotecas incluidas en Python.
"""

import csv
import json
import re
from pathlib import Path

from etapa1_validacion_datos import cargar_datos

CARPETA = Path(__file__).resolve().parent
MAPA_ORIGINAL = CARPETA / "mapa_geoespacial_actualizado.html"
RUTAS_CSV = CARPETA / "mejor_prueba_rutas.csv"
MAPA_SALIDA = CARPETA / "mapa_rutas_comparacion.html"


# El mapa original contiene los 10 centros (rojos) seguidos de 90 tiendas (azules).
def obtener_coordenadas():
    if not MAPA_ORIGINAL.exists():
        raise FileNotFoundError(
            "Falta mapa_geoespacial_actualizado.html. Colócalo junto a este programa."
        )

    texto = MAPA_ORIGINAL.read_text(encoding="utf-8")
    patron = re.compile(
        r'L\.circleMarker\(\s*\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\],\s*(\{.*?\})\s*\)',
        re.DOTALL,
    )
    encontrados = patron.findall(texto)
    if len(encontrados) != 100:
        raise ValueError(
            f"Se esperaban 100 ubicaciones en el mapa y se encontraron {len(encontrados)}."
        )

    coordenadas = []
    colores = []
    for lat, lon, opciones in encontrados:
        coordenadas.append([float(lat), float(lon)])
        color = re.search(r'"color"\s*:\s*"([^"]+)"', opciones)
        colores.append(color.group(1).lower() if color else "")

    if colores[:10] != ["red"] * 10 or colores[10:] != ["blue"] * 90:
        raise ValueError("El orden de centros y tiendas no coincide con el mapa original.")
    return coordenadas


def leer_recorrido(texto, numero_centro):
    partes = [parte.strip() for parte in texto.split("->")]
    ruta = []
    for parte in partes:
        centro = re.fullmatch(r"Centro\s+(\d+)", parte)
        tienda = re.fullmatch(r"Tienda\s+(\d+)", parte)
        if centro:
            ruta.append(int(centro.group(1)) - 1)
        elif tienda:
            ruta.append(9 + int(tienda.group(1)))  # Tienda 1 = índice 10
        else:
            raise ValueError(f"Nombre de ubicación no reconocido: {parte}")

    if ruta[0] != numero_centro or ruta[-1] != numero_centro:
        raise ValueError(f"La ruta del Centro {numero_centro + 1} no regresa a su centro.")
    if any(nodo < 10 or nodo > 99 for nodo in ruta[1:-1]):
        raise ValueError("Una ruta contiene un nodo inválido como tienda.")
    return ruta


def distancia_y_costo(ruta, distancias, costos):
    return (
        sum(distancias[a][b] for a, b in zip(ruta, ruta[1:])),
        sum(costos[a][b] for a, b in zip(ruta, ruta[1:])),
    )


def obtener_rutas(distancias, costos):
    if not RUTAS_CSV.exists():
        raise FileNotFoundError(
            "Falta mejor_prueba_rutas.csv. Ejecuta primero evaluacion_rendimiento.py."
        )

    centros = []
    for numero_centro, fila in enumerate(
        csv.DictReader(RUTAS_CSV.open(encoding="utf-8-sig", newline=""))
    ):
        if numero_centro >= 10 or fila["Centro"].strip() != f"Centro {numero_centro + 1}":
            raise ValueError("Los centros del CSV no tienen el orden esperado.")

        inicial = leer_recorrido(fila["Ruta inicial"], numero_centro)
        optimizada = leer_recorrido(fila["Mejor ruta encontrada"], numero_centro)
        if sorted(inicial[1:-1]) != sorted(optimizada[1:-1]):
            raise ValueError(f"Las tiendas asignadas al Centro {numero_centro + 1} cambiaron.")

        di, ci = distancia_y_costo(inicial, distancias, costos)
        do, co = distancia_y_costo(optimizada, distancias, costos)
        if abs(di - float(fila["Distancia inicial (km)"])) > 0.02:
            raise ValueError(f"La distancia inicial del Centro {numero_centro + 1} no coincide.")
        if abs(do - float(fila["Distancia final (km)"])) > 0.02:
            raise ValueError(f"La distancia final del Centro {numero_centro + 1} no coincide.")

        centros.append({
            "id": numero_centro + 1,
            "inicial": inicial,
            "optimizada": optimizada,
            "tiendas": len(inicial) - 2,
            "distanciaInicial": round(di, 4),
            "distanciaOptimizada": round(do, 4),
            "costoInicial": round(ci, 4),
            "costoOptimizado": round(co, 4),
        })

    if len(centros) != 10:
        raise ValueError("Se esperaban rutas para los 10 centros.")

    for modalidad in ("inicial", "optimizada"):
        visitadas = [nodo for centro in centros for nodo in centro[modalidad][1:-1]]
        if len(visitadas) != 90 or set(visitadas) != set(range(10, 100)):
            raise ValueError(f"Hay tiendas repetidas o faltantes en rutas {modalidad}.")
    return centros


HTML = r'''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Comparación de rutas - Culiacán</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    * { box-sizing: border-box; }
    body { font-family: Arial, sans-serif; margin: 0; background: #f5f7fa; color: #1b2b40; }
    .contenedor { min-height: 100vh; display: grid; grid-template-columns: 330px minmax(0, 1fr); }
    aside { padding: 24px; background: white; box-shadow: 1px 0 12px #21324a16; z-index: 2; }
    h1 { font-size: 23px; line-height: 1.2; margin: 2px 0 8px; }
    .etiqueta { font-weight: 700; font-size: 11px; letter-spacing: 1.5px; color: #327a7d; text-transform: uppercase; }
    p { font-size: 13px; line-height: 1.55; color: #516071; }
    label { display: block; font-size: 13px; font-weight: 700; margin: 20px 0 8px; }
    select { display: block; width: 100%; padding: 11px; font: inherit; font-size: 14px; border: 1px solid #ccd5df; border-radius: 8px; background: #fff; color: #1b2b40; }
    .resumen { margin-top: 22px; padding: 16px; border-radius: 12px; background: #eef7f5; }
    .resumen h2 { font-size: 15px; margin: 0 0 14px; }
    .datos { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .valor { font-size: 19px; font-weight: 700; margin-top: 4px; }
    .descripcion { font-size: 11px; color: #586b7b; }
    .mejora { color: #13795a; font-weight: 700; font-size: 15px; margin-top: 16px; }
    .leyenda { margin-top: 23px; padding-top: 15px; border-top: 1px solid #e0e7ee; }
    .leyenda h2 { font-size: 14px; margin: 0 0 10px; }
    .legend-row { display:flex; align-items:center; gap: 9px; font-size: 13px; margin: 10px 0; }
    .linea { width: 28px; border-top: 4px solid #117e76; display: inline-block; }
    .linea.inicial { border-top: 3px dashed #56687a; }
    .punto { width: 12px; height: 12px; border-radius: 50%; display: inline-block; background: #2563eb; }
    .punto.centro { background: #c53030; }
    .nota { margin-top: 23px; font-size: 12px; background: #fff5e6; padding: 12px; border-left: 3px solid #da9a32; border-radius: 5px; }
    main { min-width: 0; position: relative; }
    #map { width: 100%; height: 100vh; min-height: 590px; }
    .titulo-mapa { position: absolute; right: 16px; top: 16px; z-index: 600; padding: 9px 13px; border-radius: 8px; background: #ffffffec; box-shadow: 0 2px 12px #0002; font-size: 12px; max-width: 260px; }
    .orden { width: 23px; height: 23px; background: white; border: 2px solid #2672de; border-radius: 50%; text-align: center; line-height: 19px; color: #1c54a6; font-size: 11px; font-weight: bold; box-shadow: 0 1px 4px #0005; }
    .centro-numero { background: #ad2929; color: white; border-radius: 14px; padding: 2px 5px; font-weight: 700; font-size: 11px; border: 1px solid white; }
    @media (max-width: 760px) { .contenedor { display: flex; flex-direction: column; } aside { padding: 18px; } #map { height: 65vh; min-height: 420px; } .titulo-mapa { display: none; } }
  </style>
</head>
<body>
<div class="contenedor">
  <aside>
    <div class="etiqueta">Proyecto de optimización</div>
    <h1>Rutas de distribución en Culiacán</h1>
    <p>Comparación entre los recorridos iniciales por vecino más cercano y las rutas obtenidas con Recocido Simulado (mejor prueba, semilla 46).</p>

    <label for="centro">Centro de distribución</label>
    <select id="centro">
      <option value="todos">Todos los centros</option>
      <option value="1">Centro 1</option><option value="2">Centro 2</option>
      <option value="3">Centro 3</option><option value="4">Centro 4</option>
      <option value="5">Centro 5</option><option value="6">Centro 6</option>
      <option value="7">Centro 7</option><option value="8">Centro 8</option>
      <option value="9">Centro 9</option><option value="10">Centro 10</option>
    </select>

    <label for="vista">Rutas a mostrar</label>
    <select id="vista">
      <option value="optimizada">Optimizadas</option>
      <option value="inicial">Iniciales</option>
      <option value="ambas">Ambas (comparación)</option>
    </select>

    <div class="resumen">
      <h2 id="tituloResumen">Resumen general</h2>
      <div class="datos">
        <div><div class="descripcion">Distancia inicial</div><div class="valor" id="distanciaInicial">–</div></div>
        <div><div class="descripcion">Distancia optimizada</div><div class="valor" id="distanciaOptimizada">–</div></div>
        <div><div class="descripcion">Costo inicial (u.c.)</div><div class="valor" id="costoInicial">–</div></div>
        <div><div class="descripcion">Costo optimizado (u.c.)</div><div class="valor" id="costoOptimizado">–</div></div>
      </div>
      <div class="mejora" id="mejora">–</div>
      <div class="descripcion" id="totalTiendas" style="margin-top:8px">–</div>
    </div>

    <div class="leyenda">
      <h2>Leyenda</h2>
      <div class="legend-row"><span class="punto centro"></span> Centro de distribución (rojo)</div>
      <div class="legend-row"><span class="punto"></span> Tienda (azul)</div>
      <div class="legend-row"><span class="linea inicial"></span> Ruta inicial (línea discontinua)</div>
      <div class="legend-row"><span class="linea"></span> Ruta optimizada (línea continua)</div>
      <p>Al mostrar todos los centros, cada ruta usa un color distinto. Selecciona un centro para ver el orden de visitas.</p>
    </div>
    <div class="nota"><strong>Importante:</strong> los segmentos son líneas directas entre coordenadas, no trayectos por calles. Las distancias y los costos provienen de las matrices del proyecto, no de medir las líneas dibujadas.</div>
  </aside>
  <main>
    <div id="map"></div>
    <div class="titulo-mapa">10 centros · 90 tiendas · Mejor ejecución: semilla 46</div>
  </main>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script id="datos" type="application/json">__DATOS_JSON__</script>
<script>
(function () {
  const datos = JSON.parse(document.getElementById('datos').textContent);
  const puntos = datos.coordenadas;
  const centros = datos.centros;
  const colores = ['#d44d51','#e88b31','#9671cf','#128999','#5a8d3d',
                   '#c06492','#5b7cc3','#9e7947','#a44935','#38947b'];
  if (typeof L === 'undefined') {
    document.getElementById('map').innerHTML = '<p style="padding:40px">No se pudo cargar el mapa base. Comprueba tu conexión a Internet y vuelve a abrir el HTML.</p>';
    return;
  }

  const map = L.map('map').setView([24.80, -107.40], 12);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  }).addTo(map);
  const capas = L.layerGroup().addTo(map);
  const selectorCentro = document.getElementById('centro');
  const selectorVista = document.getElementById('vista');

  function nombreNodo(n) { return n < 10 ? 'Centro ' + (n + 1) : 'Tienda ' + (n - 9); }
  function dos(n) { return n.toFixed(2); }

  function mostrarResumen(filas) {
    const sumar = campo => filas.reduce((total, f) => total + f[campo], 0);
    const di = sumar('distanciaInicial');
    const doKm = sumar('distanciaOptimizada');
    const ci = sumar('costoInicial');
    const co = sumar('costoOptimizado');
    const ti = sumar('tiendas');
    const porcentaje = ci > 0 ? 100 * (ci - co) / ci : 0;
    const esTodo = filas.length === 10;
    document.getElementById('tituloResumen').textContent = esTodo ? 'Resumen general' : 'Centro ' + filas[0].id;
    document.getElementById('distanciaInicial').textContent = dos(di) + ' km';
    document.getElementById('distanciaOptimizada').textContent = dos(doKm) + ' km';
    document.getElementById('costoInicial').textContent = dos(ci);
    document.getElementById('costoOptimizado').textContent = dos(co);
    document.getElementById('mejora').textContent = 'Reducción de costo: ' + dos(porcentaje) + '%';
    document.getElementById('totalTiendas').textContent = ti + ' tiendas atendidas';
  }

  function dibujar() {
    capas.clearLayers();
    const eleccion = selectorCentro.value;
    const vista = selectorVista.value;
    const mostrarTodos = eleccion === 'todos';
    const elegidos = mostrarTodos ? centros : centros.filter(c => String(c.id) === eleccion);
    const bounds = [];
    const tiendasActivas = new Set();

    for (const c of elegidos) {
      const rutaPreferida = c.optimizada;
      rutaPreferida.slice(1, -1).forEach(n => tiendasActivas.add(n));
      const base = colores[c.id - 1];
      const inicial = c.inicial.map(n => puntos[n]);
      const optimizada = c.optimizada.map(n => puntos[n]);
      if (vista === 'inicial' || vista === 'ambas') {
        const lineaInicial = L.polyline(inicial, {
          color: mostrarTodos ? base : '#64748b', weight: mostrarTodos ? 2.8 : 3.8,
          opacity: vista === 'ambas' ? 0.55 : 0.9, dashArray: '7, 6'
        }).bindPopup('Centro ' + c.id + ' · Ruta inicial: ' + dos(c.distanciaInicial) + ' km');
        lineaInicial.addTo(capas);
      }
      if (vista === 'optimizada' || vista === 'ambas') {
        const lineaOptimizada = L.polyline(optimizada, {
          color: mostrarTodos ? base : '#047f72', weight: mostrarTodos ? 3.5 : 5,
          opacity: mostrarTodos ? 0.86 : 0.94
        }).bindPopup('Centro ' + c.id + ' · Ruta optimizada: ' + dos(c.distanciaOptimizada) + ' km');
        lineaOptimizada.addTo(capas);
      }
      rutaPreferida.forEach(n => bounds.push(puntos[n]));
    }

    // Los 10 centros siempre son visibles; se destaca el centro seleccionado.
    puntos.slice(0, 10).forEach((p, i) => {
      const activo = mostrarTodos || Number(eleccion) === i + 1;
      L.circleMarker(p, {
        radius: activo ? 8 : 6, color: '#fff', weight: 2,
        fillColor: '#ba2934', fillOpacity: activo ? 1 : 0.42
      }).bindPopup('<strong>Centro ' + (i + 1) + '</strong>').addTo(capas);
      if (activo) {
        L.marker(p, { icon: L.divIcon({
          className: '', html: '<span class="centro-numero">C' + (i+1) + '</span>',
          iconSize: [25, 18], iconAnchor: [12, 27]
        }) }).addTo(capas);
      }
    });

    // Con un centro seleccionado se muestra el número de visita junto a la tienda.
    const rutaNumerada = !mostrarTodos
      ? (vista === 'inicial' ? elegidos[0].inicial : elegidos[0].optimizada)
      : [];
    const posicion = new Map();
    rutaNumerada.slice(1, -1).forEach((n, i) => posicion.set(n, i + 1));
    for (let n = 10; n < 100; n++) {
      const activo = tiendasActivas.has(n);
      const popup = '<strong>' + nombreNodo(n) + '</strong>' +
        (posicion.has(n) ? '<br>Orden de visita mostrado: ' + posicion.get(n) : '');
      L.circleMarker(puntos[n], {
        radius: activo ? 4.7 : 2.8, color: activo ? '#1c5aa6' : '#cbd5e1',
        weight: activo ? 1.5 : 1, fillColor: activo ? '#2f73df' : '#a2afbf',
        fillOpacity: activo ? 0.95 : 0.23
      }).bindPopup(popup).addTo(capas);
      if (posicion.has(n)) {
        L.marker(puntos[n], {icon: L.divIcon({
          className: '', html: '<div class="orden">' + posicion.get(n) + '</div>',
          iconSize: [23, 23], iconAnchor: [-7, 22]
        })}).bindPopup(popup).addTo(capas);
      }
    }
    mostrarResumen(elegidos);
    if (bounds.length) map.fitBounds(bounds, {padding: [38, 38], maxZoom: 13});
  }
  selectorCentro.addEventListener('change', dibujar);
  selectorVista.addEventListener('change', dibujar);
  dibujar();
})();
</script>
</body>
</html>'''


def main():
    _, distancias, costos = cargar_datos()
    coordenadas = obtener_coordenadas()
    centros = obtener_rutas(distancias, costos)

    contenido = json.dumps({"coordenadas": coordenadas, "centros": centros}, ensure_ascii=False)
    # Mantiene seguros los datos incrustados dentro del HTML.
    contenido = contenido.replace("<", "\\u003c")
    MAPA_SALIDA.write_text(
        HTML.replace("__DATOS_JSON__", contenido), encoding="utf-8"
    )

    distancia_inicial = sum(c["distanciaInicial"] for c in centros)
    distancia_final = sum(c["distanciaOptimizada"] for c in centros)
    costo_inicial = sum(c["costoInicial"] for c in centros)
    costo_final = sum(c["costoOptimizado"] for c in centros)
    print("ETAPA 6 - MAPA INTERACTIVO DE RUTAS")
    print("-" * 44)
    print("Centros localizados: 10")
    print("Tiendas localizadas: 90")
    print("Se comparan las rutas iniciales con la mejor prueba (semilla 46).")
    print(f"Distancia inicial: {distancia_inicial:.2f} km")
    print(f"Distancia optimizada: {distancia_final:.2f} km")
    print(f"Costo inicial: {costo_inicial:.2f} u.c.")
    print(f"Costo optimizado: {costo_final:.2f} u.c.")
    print("Verificación: las 90 tiendas aparecen exactamente una vez en ambos resultados.")
    print("Archivo creado:", MAPA_SALIDA.name)
    print("Ábrelo en tu navegador con conexión a Internet para cargar el mapa base.")
    print("Nota: las líneas no siguen calles; representan el orden de visita.")


if __name__ == "__main__":
    main()
