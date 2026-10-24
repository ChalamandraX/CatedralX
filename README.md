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

## Retroalimentación estadística offline

Cada ejecución válida de elite/REASON/razon.py registra una predicción con un prediction_id único, el precio de referencia y el timestamp de mercado observado. El ID aparece en la salida JSON y sirve para asociar los resultados posteriores.

Flujo manual y verificable:

1. Obtener una observación fresca: python elite/bin/feed_once.py.
2. Ejecutar un análisis de una sola vez: python elite/REASON/razon.py. Conserva el prediction_id de la salida JSON.
3. Cuando venza el horizonte, obtener una observación nueva con python elite/bin/feed_once.py.
4. Etiquetar el resultado observado, por ejemplo: python elite/bin/feedback_label.py ID_DE_PREDICCION --horizon 5m. Horizontes disponibles: 1m, 5m, 15m y 1h.
5. Consultar las estadísticas: python elite/bin/feedback_report.py.

El etiquetador usa el precio y timestamp del snapshot real, calcula el rendimiento desde el precio de referencia de la predicción y asigna una clase ex post: buy si el retorno alcanza o supera +0.05%, sell si cae hasta -0.05% o menos, y hold entre ambos umbrales. Este umbral es una convención de evaluación, no una recomendación de compra o venta; puede cambiarse mediante --neutral-threshold-pct. Se permite una etiqueta por predicción y horizonte. Las observaciones demasiado tempranas, demasiado tardías o caducadas se rechazan.

El informe calcula predicciones identificadas y pendientes, exactitud por horizonte, matriz de confusión, precisión y recall por clase, y métricas por régimen. El retorno alineado excluye hold y no incluye comisiones, spread, deslizamiento, dimensionamiento de posición ni contexto de cartera: no representa P&L de una estrategia ni demuestra ventaja predictiva. signal_strength sigue siendo una fuerza heurística, no una probabilidad, por lo que no se calculan métricas de calibración probabilística.

El historial append-only se guarda por defecto en ~/.local/state/chalamandra/catedralx/feedback.jsonl; puede redirigirse mediante CATEDRALX_FEEDBACK_PATH. El reporte es de solo lectura. No hay reentrenamiento automático ni ejecución de órdenes. El etiquetado requiere una acción explícita tras observar cada horizonte; esta versión no incluye un programador o servicio de etiquetado continuo. Las predicciones históricas sin ID se contabilizan como registros heredados no vinculables y no se pueden puntuar retrospectivamente mediante este esquema.

## Ciclo económico, impacto y reinversión gobernada

`elite/FEX/GOVERNANCE/economic_cycle.py` añade un registro auditable por ciclo para conectar evidencia con decisiones de mejora: `measure → evaluate → propose → authorize → verify → feedback`. Cada medición exige métrica, fuente, periodo, unidad, fórmula, valor y timestamp con zona horaria; objetivo e incertidumbre son opcionales y explícitos. Las evaluaciones registran evidencia y no permiten afirmar causalidad sin declarar un método causal. Las propuestas incluyen resultado esperado y plan de verificación. La autorización exige aprobador y justificación explícitos.

Ejemplo de uso desde la raíz del repositorio, con `PYTHONPATH=elite`:

```python
from FEX.GOVERNANCE.economic_cycle import registrar_evento, resumir_ciclos

cycle_id = registrar_evento("measure", {
    "metric": "personas_atendidas",
    "source": "registro_servicio_v1",
    "period": "2026-Q3",
    "unit": "personas",
    "formula": "conteo_unico_de_personas",
    "value": 120,
    "target": 150,
    "uncertainty": 3,
    "observed_at": "2026-10-23T10:00:00Z",
})
# El resto de etapas debe registrarse en orden y con el mismo cycle_id.
print(resumir_ciclos())
```

El ledger append-only vive por defecto en `~/.local/state/chalamandra/catedralx/impact_cycle.jsonl`; se puede cambiar con `CATEDRALX_IMPACT_LEDGER_PATH`. No se inventan objetivos ni porcentajes de reinversión, no se mueve dinero, no se ejecutan órdenes, no hay reentrenamiento automático y una autorización registrada no equivale a ejecutar una acción. La medición de impacto social requiere fuentes y diseños de evaluación adecuados; una variación temporal por sí sola no demuestra causalidad.

También se puede usar el CLI `python elite/bin/impact_cycle.py` o el punto de entrada de la Catedral `bash BIN/catedral impact-cycle`. Para registrar una etapa, pasa `--event measure|evaluate|propose|authorize|verify|feedback` y `--payload '{...}'`; las etapas posteriores requieren `--cycle-id` con el ID que devolvió `measure`. Para consultar el ledger usa `bash BIN/catedral impact-cycle --report`. El comando registra evidencia y estados únicamente; no ejecuta la propuesta.
