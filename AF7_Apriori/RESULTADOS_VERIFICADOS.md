# AF7: informe de implementación y resultados verificados

Fecha de verificación: 15 de noviembre de 2026, America/Mexico_City.

## Entrega

Se implementó una aplicación local Streamlit con panel de análisis, explorador de reglas y canasta simulada. Se conservó Apriori propio; MLxtend se usa para contrastar resultados. La estructura definitiva y los comandos están en README.md.

Se crearon app.py, requirements.txt, requirements-lock.txt, .gitignore, los módulos de src/, las tres páginas de pages/ y las pruebas de tests/. Se modificaron README.md, apriori_online_retail.py y Preparacion/limpieza_datos.py. Las entradas históricas ahora delegan a módulos compartidos. No se modificaron AF4 ni otros proyectos, ni se hicieron commits.

Los seis CSV históricos se conservaron. Las nuevas preparaciones reproducen exactamente esos CSV: sus SHA-256 coinciden byte por byte. Los resúmenes nuevos añaden desglose, por lo que su JSON cambia de forma intencional.

## Datos reales

Ejecución completa de referencia:

`salida_af7/analisis/ejecucion_20261115T233227Z_5fc3b202/`

Preparación utilizada:

`salida_af7/preparaciones/preparacion_20261115T233051Z_7c847778/`

| Indicador | Resultado |
|---|---:|
| Registros originales | 541,909 |
| Campos clave faltantes | 1,454 |
| Cancelaciones después del filtro anterior | 9,288 |
| Cantidad o precio inválidos después de cancelaciones | 1,063 |
| Servicios o ajustes después de los filtros anteriores | 2,315 |
| Duplicados exactos restantes | 5,221 |
| Total excluido | 19,341 |
| Registros válidos | 522,568 |
| Pares únicos factura-producto | 517,318 |
| Facturas / canastas completas | 19,773 |
| Productos diferentes completos | 3,803 |
| Facturas de entrenamiento | 15,818 |
| Productos en entrenamiento | 3,744 |
| Facturas de prueba | 3,955 |
| Productos en prueba | 2,994 |
| Conjuntos frecuentes | 1,996 |
| Reglas | 1,146 |

Los campos clave faltantes corresponden a 1,454 descripciones nulas/vacías y cero registros adicionales por otros campos clave. El grupo cantidad/precio se desglosa en 474 por cantidad no positiva/no numérica y 589 por precio no positivo/no numérico después de excluir cantidades inválidas. Las exclusiones son secuenciales y disjuntas; los subconteos no se suman otra vez al total.

Parámetros: soporte 0.01; confianza 0.50; lift mínimo 1.0001; tamaño sin límite. La minería usa solamente entrenamiento. Apriori propio y MLxtend coincidieron en los 1,996 conjuntos y sus soportes. La duración registrada del servicio fue 47.095 segundos, incluida la validación opcional y excluida la preparación de Excel; no es una garantía de tiempo para otros equipos.

## Ejemplo real

De la canasta de prueba con códigos 20719, 20724, 20978, 20979 y 22621 se sugiere 22355, CHARLOTTE BAG SUKI DESIGN.

Regla: WOODLAND CHARLOTTE BAG (20719) y RED RETROSPOT CHARLOTTE BAG (20724) → CHARLOTTE BAG SUKI DESIGN (22355).

- Soporte: 0.017132380831963587 (aproximadamente 1.713%).
- Confianza: 0.6514423076923078 (aproximadamente 65.144%).
- Lift: 13.925019490644493.

La regla fue calculada en entrenamiento y aplicada a una canasta de prueba que no contiene el producto sugerido. Es una recomendación ilustrativa basada en asociación, no evidencia de una venta posterior.

## Evaluación

Se ocultó un producto por cada una de las 3,686 canastas de prueba con al menos dos productos. Semilla: 42. Cobertura de Apriori: 63.022%.

| k | Acierto popularidad | Acierto Apriori |
|---|---:|---:|
| 1 | 0.678% | 3.961% |
| 3 | 1.302% | 6.050% |
| 5 | 1.709% | 6.837% |
| 10 | 3.011% | 7.298% |

Los porcentajes son hit rate@k respecto a todas las canastas evaluadas, incluidas aquellas sin reglas aplicables.

## Comprobaciones

- 21 pruebas automatizadas satisfactorias: limpieza, presencia binaria, conteo exhaustivo, umbrales, límites, comparación de conjuntos y métricas con MLxtend, recomendaciones con consecuentes múltiples, ausencia de reglas, fuentes ausentes, persistencia y protección contra sobrescritura.
- Streamlit AppTest recorrió las tres páginas y comprobó agregar productos, recomendar, excluir seleccionados y limpiar la canasta.
- El servidor local inició correctamente y /_stcore/health respondió HTTP 200, contenido ok.
- pip check informó que no había dependencias rotas.
- Se generaron cuatro PNG en la ejecución de referencia: productos frecuentes, soporte/confianza, reglas por lift y comparación de métodos.
- git diff --check no encontró errores de espacios.

## Correcciones y límites

Se corrigieron rutas de ejecución, ausencia de dependencias, falta de selección de productos, argumentos ignorados, sobrescritura de resultados, ausencia de validación de parámetros y una comparación de soporte que podía excluir por redondeo un conjunto exactamente en el umbral (7 de 100 con soporte 0.07).

Los controles abortan minería excesiva en lugar de cambiar los parámetros. La validación opcional con MLxtend puede consumir recursos adicionales. Las descripciones solo tienen validación de ausencia/espacios; sus variantes se resuelven mediante catálogo por código. El programa no clasifica semánticamente los textos.

La interfaz se comprobó con AppTest, no mediante inspección visual de un navegador. La construcción de la matriz dispersa de validación produce una advertencia de deprecación de pandas; no impidió la comparación satisfactoria con MLxtend.

Para documentar la sección 8 pueden usarse los CSV, el JSON de trazabilidad, los cuatro PNG y las tablas descargables de la aplicación. Los nombres UTC de las carpetas identifican ejecuciones independientes.
