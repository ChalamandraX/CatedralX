# CatedralX — motor financiero de análisis

CatedralX es el motor financiero experimental del ecosistema Chalamandra Magistral. Esta versión ejecuta análisis determinista sobre precios observados y conserva los subsistemas de Hurst, geometría, energía libre y giro como diagnósticos complementarios. La etiqueta financiera final ya no depende de la decisión estocástica del subsistema antiguo.

## Alcance actual

- Entrada: al menos 30 observaciones de precio, positivas y finitas, en orden cronológico. No se crean precios sintéticos cuando falta historial.
- Señal: compara el impulso de las últimas 5 observaciones y el de las últimas 20. La señal `buy`/`sell` solo aparece cuando ambos impulsos normalizados apuntan en la misma dirección; en los demás casos devuelve `hold`.
- Protección: si la volatilidad de las últimas 10 observaciones llega a al menos el doble de la volatilidad de referencia previa —o la volatilidad de referencia es prácticamente cero y la reciente aumenta—, se bloquea la señal direccional. El umbral hamiltoniano de protección también fuerza `hold` y revisión, nunca una orden de “cerrar todo”.
- Métricas: rendimiento acumulado desde la primera observación, variación de la última observación, volatilidad por observación, expansión de volatilidad, drawdown máximo de la serie, medias móviles y puntuaciones de impulso.
- Determinismo: con los mismos precios y los mismos parámetros, la clasificación y sus métricas financieras son reproducibles.
- Persistencia: el estado se guarda en `~/.local/state/chalamandra/catedralx/hormonas.json` por defecto, fuera de este repositorio. Puede cambiarse mediante `CATEDRALX_STATE_PATH`, que no debe apuntar dentro del checkout.

`signal_strength` está acotada entre 0 y 1 y es una **fuerza heurística, no una probabilidad de acierto**. `buy`, `sell` y `hold` son etiquetas de análisis, no órdenes ni recomendaciones para operar. El motor marca `trading_enabled=false`, `orders_created=false` y `orders_executed=false`.

## EUR/USD y datos de mercado

La integración opcional de `agents` (`pipeline/fx_market_data.py`) consulta la API pública de Frankfurter para tipos de cambio de referencia diarios. La frecuencia se identifica como `daily_reference` y no debe confundirse con cotización intradía o datos tick-by-tick. El conector comprueba el par, la forma de la respuesta, valores válidos, cantidad mínima de observaciones y antigüedad del último dato.

El puente se registra en `agents` como `catedralx_reasoning`. Configuración relevante: `CATEDRALX_PATH` apunta a este checkout y `CATEDRALX_STATE_PATH` a un archivo de estado externo. Ninguna de estas rutas habilita ejecución de órdenes.

## Pruebas

Desde el directorio raíz de este repositorio, con `pytest` y `numpy` disponibles:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=elite pytest -q -p no:cacheprovider tests/test_financial_engine.py
```

La suite cubre tendencias ascendentes y descendentes, mercado plano, bloqueo por expansión de volatilidad, entradas inválidas, reproducibilidad del ciclo público, persistencia fuera del código fuente y la prohibición de fabricar precios.

## Pendiente antes de cualquier uso operativo

Esta versión **no está validada para trading real**. Todavía requiere backtesting histórico con fechas y costes reales, validación fuera de muestra, comparación contra benchmarks, pruebas de estabilidad, límites de pérdida y exposición definidos con contexto de cartera, comisiones/spread/deslizamiento, dimensionamiento de posiciones, gestión de fallos de datos y auditoría. No contiene un ejecutor de órdenes ni debe conectarse a una cuenta de trading como si fuera un sistema listo para producción.
