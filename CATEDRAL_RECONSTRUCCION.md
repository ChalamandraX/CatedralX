# Catedral Modular — reconstrucción de vectores

Este documento registra la implementación que se está reconstruyendo dentro del repositorio existente `CatedralX`. No implica que el sistema esté listo para producción ni que se haya validado para operar en mercados reales.

## Arquitectura y rutas actuales

| Vector | Ruta canónica en este checkout | Estado |
|---|---|---|
| RSX / PERCEIVE | `elite/PERCEIVE/` | Validación de precios, contrato sensorial, escritura atómica, comprobación de frescura y detector de movimientos. `stream_altar.py` consulta velas públicas cerradas de BTC/USDT de Binance; `feed_once.py` actualiza el snapshot una vez. `bunker.py` conserva su entrada existente y rechaza precios sintéticos. |
| SCX / REASON | `elite/REASON/` | Orquestador financiero determinista, contratos `SensoryInput` / `CathedralState`, analizadores existentes de Hurst, geometría, energía libre, giroscopio y Hamiltoniano. Se unificó la variable de ruta del snapshot con RSX. |
| MCX / OPTIMIZE | `elite/MCX/OPTIMIZE/` | Se añadieron funciones explícitas para estado afectivo acotado, homeostasis, sentimiento léxico de referencia, entropía, fatiga proxy, ratio BTC/oro, registro económico y estimación configurable de reserva. No son mediciones biológicas ni asesoría fiscal. |
| AEX / ACTION | `elite/AEX/` y `elite/AEX/DECISION/` | Se añadió una frontera de intención que falla cerrada. No existe integración de órdenes reales; el ejecutor nuevo deniega el envío. |
| DSX / DEFENSE | `elite/DSX/DEFENSE/` | Se conservaron los controles de recursos existentes y se añadieron rate limiting, copia explícita de respaldo y utilidades de codificación. Base64 no es cifrado. No se activaron reinicios automáticos ni dispersión de scripts. |
| MSX / INTERFACE | `elite/bin/` | Panel JSON de solo lectura y servidor HTTP de estado limitado a loopback `127.0.0.1:5050`, rutas `/status` y `/health`. |
| FEX / FEEDBACK | `elite/FEX/FEEDBACK/` | Registro append-only de predicciones y resultados etiquetados. No se realiza reentrenamiento automático ni se afirma que el modelo mejore sin evaluación. |

## Contrato del latido

1. RSX puede recibir observaciones por adaptador o consultar bajo demanda el endpoint público de velas de Binance; no usa claves ni endpoints de órdenes.
2. Los precios se validan: deben ser positivos, finitos y contar con al menos 30 observaciones.
3. RSX escribe un snapshot atómico en `/dev/shm/cathedral_snapshot.json` por defecto. La ruta se puede cambiar con `CATEDRALX_SNAPSHOT_PATH`.
4. SCX analiza la entrada y produce un estado. La persistencia de estado usa `CATEDRALX_STATE_PATH` o, por defecto, `~/.local/state/chalamandra/catedralx/hormonas.json`.
5. MCX ofrece funciones puras para métricas internas; no habilita por sí mismo una operación.
6. DSX provee límites y comprobaciones, pero los daemons no se inician automáticamente.
7. MSX expone únicamente estado local de solo lectura.
8. FEX registra predicciones y resultados; el aprendizaje no se actualiza sin etiquetas y evaluación separada.

## Proveedor RSX operativo

- Fuente por defecto: mercado spot público de Binance, par `BTCUSDT`, velas de un minuto.
- Endpoint: `https://data-api.binance.vision/api/v3/klines`; la documentación oficial describe ese host como acceso a datos públicos que no necesita clave API. No se usa para crear órdenes.
- El adaptador elimina la vela que aún no ha cerrado, comprueba precios finitos y positivos, exige al menos 30 velas cerradas y rechaza datos cuya última vela cerrada tenga más de 120 segundos.
- Comandos: `bash BIN/catedral feed-once` solo refresca RSX; `bash BIN/catedral ciclo` refresca RSX y luego ejecuta un análisis SCX; `bash BIN/catedral motor` usa el snapshot ya existente.
- Se puede seleccionar otro símbolo spot compatible mediante `CATEDRALX_MARKET_SYMBOL`; por defecto es `BTCUSDT`. El precio es el cierre de la última vela completada, no un tick en tiempo real.
- Los resultados son análisis de una muestra reciente. No validan rentabilidad, no son señales ejecutables y no autorizan trading.

## Pruebas ejecutadas

Entorno usado en la VM: entorno virtual existente en `/home/azureuser/workspace/repos/agents/venv`.

```bash
cd /home/azureuser/workspace/repos/CatedralX
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=elite /home/azureuser/workspace/repos/agents/venv/bin/python -m pytest -q -p no:cacheprovider tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=elite /home/azureuser/workspace/repos/agents/venv/bin/python -m compileall -q elite tests
```

Última verificación en la VM: 23 tests pasaron; `compileall` terminó sin errores; una descarga real escribió 59 velas cerradas y el ciclo SCX terminó con `ANALYSIS_COMPLETE` / `hold`. El estado marcó el feed como saludable. La prueba verde no valida rentabilidad ni trading real; estos resultados corresponden a una única ejecución.

## Pendiente

- Añadir backoff y estrategia de recuperación ante errores/rate limits del proveedor; decidir si se necesita un segundo proveedor independiente y documentar sus diferencias.
- Añadir pruebas unitarias para los analizadores heredados y resolver diferencias entre rutas históricas y rutas canónicas.
- Auditar el código heredado y sus dependencias antes de retirar duplicados.
- Añadir evaluación walk-forward, costes de transacción, exposición de cartera y límites de pérdida antes de considerar cualquier uso financiero.
- Revisar el endpoint y el manejo de datos sensibles antes de exponerlo fuera de localhost.
- No conectar claves de API ni habilitar ejecución de órdenes en esta fase.

## Seguridad operativa

No se han iniciado daemons, no se han enviado órdenes, no se han conectado claves ni se han creado precios sintéticos. Los archivos nuevos no sustituyen automáticamente las rutas históricas `~/LAB`; el mapeo de arriba documenta cómo queda el trabajo dentro del checkout real `CatedralX`.


## Discrepancia entre señales: diagnóstico y criterio canónico

Se comprobó que el campo heredado `decision_subsistema_original` procedía de `cerebellum.colapsar_qubit`, que usa muestreo aleatorio entre tendencia y rango. Eso hacía que el diagnóstico heredado pudiera variar aun con la misma entrada.

Corrección aplicada:
- El ciclo SCX usa ahora `colapsar_qubit_determinista` para que el diagnóstico heredado sea reproducible con la misma serie.
- El campo heredado se conserva solo como `diagnostico_no_autoritativo`; no gobierna la decisión financiera ni habilita acciones.
- La decisión canónica sigue viniendo de `analyze_financial_market`: exige que el momentum corto y medio confirme una misma dirección antes de emitir `buy` o `sell`. Si los horizontes discrepan o no superan sus umbrales, devuelve `hold`.
- La salida de `razon.py` expone `legacy_diagnostic_signal`, su rol y el hecho de que ya no usa muestreo estocástico en este camino.

Prueba de regresión: se añadió una serie donde el momentum de corto plazo es positivo y el de medio plazo negativo; el resultado esperado es `hold`. Otra prueba verifica que el diagnóstico heredado determinista es repetible y respeta la defensa por cortisol.

Verificación posterior a estos cambios: 25 tests pasaron, `compileall` y `git diff --check` terminaron sin errores; se ejecutó otra vez el ciclo real y el estado siguió saludable. No se activaron órdenes.
