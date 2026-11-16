# AF7 · Análisis de patrones de compra

Aplicación académica local en español para Online Retail. Permite preparar datos, ejecutar Apriori propio, explorar reglas y simular recomendaciones explicables. No requiere cuentas, base de datos externa ni servicios remotos después de instalar las dependencias.

## Instalación en Windows y Visual Studio Code

Con el entorno ya instalado, el inicio habitual es:

```powershell
python apriori_online_retail.py
```

Este comando abre Streamlit y usa automáticamente el Python de `.venv`, sin necesidad de activar el entorno. Detén la aplicación con Ctrl+C. Con argumentos como `--datos salida_af7`, el mismo script conserva la ejecución de minería por consola.

Python 3.12 recomendado (verificado con 3.12.10). Abre esta carpeta en VS Code y usa PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

Selecciona el intérprete `.venv\Scripts\python.exe` mediante “Python: Select Interpreter”. Si PowerShell impide activar el entorno, no es necesario cambiar la política: usa directamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Abre http://127.0.0.1:8501. Detén el servidor con Ctrl+C. Los comandos se ejecutan desde la raíz de AF7_Apriori; no dependen del nombre de usuario.

## Pantallas

1. **Panel de análisis:** sigue el proceso: datos de Online Retail → limpieza → resultados de Apriori → exploración de conjuntos → evaluación → ejemplos reales. Las opciones avanzadas quedan al final. Los parámetros aplicados aparecen con los resultados de Apriori, separados de los editables para una nueva ejecución.
2. **Reglas de asociación:** busca por nombre/código en antecedentes, consecuentes o ambos. Abre los filtros para establecer soporte y confianza en porcentaje, lift, número de productos y orden ascendente/descendente. Selecciona una fila para ver su interpretación; inicialmente se explica la primera regla. Si no hay coincidencias, restablece los filtros. La gráfica con información emergente está en un desplegable.
3. **Recomendaciones:** abre el catálogo desplegable, recorre los productos ordenados alfabéticamente y elige uno: se agrega inmediatamente. Puedes buscar dentro del selector, pero escribir es opcional. El catálogo incluye todos los artículos, tengan o no reglas aplicables; los nombres repetidos se diferencian por código. La canasta muestra “Eliminar” por artículo y “Limpiar canasta”. No hay botón para solicitar sugerencias: se actualizan automáticamente.

### Explorar conjuntos sin conocer productos

El panel muestra inicialmente 25 conjuntos ordenados por soporte de mayor a menor. Puedes filtrar por los tamaños realmente disponibles, elegir dos o más artículos, establecer un soporte mínimo y cambiar el orden. El límite de filas y la paginación evitan una tabla excesiva sin ocultar el resto de los conjuntos.

La búsqueda por nombre/código es secundaria y está en un desplegable. La tabla prioriza productos, número de artículos y soporte porcentual; “Consultar productos completos y códigos de un conjunto” permite leer todos los nombres sin recortes. La descarga conserva todos los conjuntos que cumplen los filtros, no solo la página visible. Un conjunto frecuente es la base para construir reglas, no una recomendación por sí mismo.

### Probar recomendaciones

Cada opción del catálogo muestra un estado calculado con las reglas del análisis utilizado:

- **X recomendaciones disponibles:** número de productos diferentes que el recomendador puede sugerir al seleccionar únicamente ese artículo. No depende de la canasta actual ni del máximo visible.
- **Requiere combinarse con otro artículo:** participa en antecedentes, pero por sí solo no activa reglas.
- **Sin reglas aplicables:** no participa en antecedentes de las reglas disponibles.

Puedes alternar entre “Todos” y “Con recomendaciones directas”. El cálculo se conserva en caché junto con las reglas; si cambia el análisis se utilizan sus estados correspondientes. El filtro no elimina artículos del catálogo completo ni modifica las reglas.

Puedes elegir cualquier producto del catálogo o abrir “Probar con una canasta de ejemplo”. Hay hasta seis tarjetas: tres productos individuales y tres combinaciones de dos o tres productos. Cada tarjeta identifica la sugerencia esperada y “Cargar ejemplo” sustituye la canasta y muestra recomendaciones automáticamente.

Los ejemplos se seleccionan de manera determinista entre las reglas del análisis utilizado y se verifican con el mismo recomendador. La sugerencia esperada es la primera, por lo que aparece incluso con máximo 1. En las combinaciones se comprueba además que, al retirar cualquiera de sus artículos, ninguna otra regla aplicable mantenga esa sugerencia. Si faltan casos que cumplan estos criterios se muestran solo los válidos y se informa. Son combinaciones para demostrar el sistema, no necesariamente facturas históricas.

La canasta presenta dos columnas y dos filas visibles (cuatro artículos); los adicionales quedan en el área con desplazamiento interno. El máximo de recomendaciones se configura debajo de la descripción del catálogo.

Al agregar, eliminar o cargar un ejemplo se muestran inmediatamente las sugerencias correspondientes. Presentan producto y motivo; en “Ver evidencia” se consultan la regla completa, soporte, confianza, lift y códigos. Si varias reglas respaldan un producto, se conserva la mejor según confianza, lift y soporte, con desempate determinista.

Cambiar el máximo actualiza los resultados visibles reutilizando una consulta en caché de hasta 20 sugerencias. Limpiar la canasta elimina las recomendaciones anteriores y muestra orientación. Si no hay reglas aplicables, se informa y se ofrece una canasta de ejemplo cuando existe. Ninguna de estas acciones vuelve a ejecutar Apriori.

### Análisis activo, métricas y exportaciones

El selector aparece en Panel y Reglas e identifica cada análisis con fecha/hora de Ciudad de México, soporte, confianza e identificador breve. Cambiarlo reinicia canasta, consulta y filtros con un aviso. Recomendaciones utiliza internamente la misma ejecución activa y su catálogo, sin mostrar el selector ni los parámetros técnicos. Las cifras siempre se leen de esa ejecución.

- **Soporte:** porcentaje de canastas de entrenamiento que contienen todos los productos de la regla.
- **Confianza:** porcentaje con todos los consecuentes entre las canastas que contienen todos los antecedentes.
- **Lift:** factor respecto a la frecuencia del consecuente; no es un porcentaje. La asociación no implica causalidad.

Las tablas muestran soporte/confianza en porcentaje con dos decimales y lift con tres. Los CSV de reglas, conjuntos, recomendaciones y evaluación conservan los valores originales (proporciones sin redondeo visual), códigos y columnas técnicas. Las exportaciones de exploradores respetan los filtros aplicados.

El tema se configura con opciones oficiales de Streamlit en `.streamlit/config.toml`, sin selectores CSS internos. La pregunta inicial de correo está desactivada para evitar que bloquee el arranque. Los controles incorporados del propio Streamlit pueden conservar textos de su biblioteca que no tengan una opción pública de traducción.

La navegación conserva el análisis activo. Cambiar de análisis inicia una canasta nueva. Cambiar de pantalla o de producto no entrena el algoritmo.

## Preparación y ejecución por consola

El Excel debe estar en `Datos/Online Retail.xlsx`. Los CSV originales de `salida_af7/` ya permiten ejecutar minería sin releer Excel.

Preparar y analizar en una sola operación (recomendado para obtener el desglose actualizado):

```powershell
python -m src.services.analisis --preparar --validar-mlxtend
```

Analizar la preparación histórica:

```powershell
python -m src.services.analisis --datos salida_af7 --min-soporte 0.01 --min-confianza 0.50 --min-lift 1.0001 --validar-mlxtend
```

Para limitar explícitamente el tamaño añade `--max-tamano 3`. Si se omite, no se limita el tamaño.

Se conservan ambas entradas históricas, ahora conectadas a los módulos compartidos:

```powershell
python .\Preparacion\limpieza_datos.py --entrada ".\Datos\Online Retail.xlsx" --salida ".\salida_af7\preparacion_manual_nueva"
python .\apriori_online_retail.py --datos ".\salida_af7" --evaluar --graficas --validar-mlxtend
```

La salida manual de limpieza debe ser una carpeta nueva o vacía. La entrada histórica de minería siempre evalúa sobre prueba; `--evaluar` se conserva por compatibilidad. Ya no se activa una demostración artificial al faltar los archivos: se muestra el error.

## Estructura

```text
app.py                         Entrada Streamlit y navegación
.streamlit/config.toml         Tema y arranque local sin pregunta de correo
requirements.txt               Versiones directas verificadas
requirements-lock.txt          Entorno completo de la ejecución verificada
.gitignore
Datos/Online Retail.xlsx       Fuente original conservada
Preparacion/limpieza_datos.py   Entrada compatible de preparación
apriori_online_retail.py        Entrada compatible de minería y gráficas PNG
src/
  data/limpieza.py              Carga, limpieza, catálogo y exportación protegida
  data/canastas.py              Canastas binarias y carga de particiones
  mining/apriori.py             Apriori propio con bitsets y poda
  mining/reglas.py              Reglas, métricas y tabla de conjuntos
  mining/validacion.py          Comparación opcional con MLxtend
  recommendations/recomendador.py  Índice, recomendaciones y evaluación
  services/analisis.py          Coordinación y CLI
  utils/archivos.py             Rutas, persistencia, JSON y SHA-256
  utils/interfaz.py             Caché de lecturas y componentes Streamlit
  utils/visualizacion.py        Gráficas PNG de la entrada histórica
pages/
  1_Panel_de_analisis.py
  2_Reglas_de_asociacion.py
  3_Recomendaciones.py
tests/                         Pruebas unitarias, servicio e interacción
salida_af7/
  *.csv, resumen_preparacion.json  Preparación histórica conservada
  preparaciones/preparacion_*/     Nuevas preparaciones completas
  analisis/ejecucion_*/            Resultados independientes por ejecución
RESULTADOS_VERIFICADOS.md       Evidencia de la integración y resultados reales
INFORME_REDISENO.md             Cambios de interfaz y pruebas del rediseño
```

## Decisiones de procesamiento

Se conserva la política original: normalizar espacios/códigos; excluir campos clave ausentes, cancelaciones que empiezan con C, cantidad/precio inválidos, códigos administrativos conocidos y duplicados exactos. Las descripciones inválidas detectadas son nulas o vacías; no existe clasificación semántica automática de textos.

Cada fila excluida se asigna al primer criterio aplicable. El desglose nuevo separa descripción/otros campos y cantidad/precio con prioridad de cantidad; esos subconteos no se vuelven a sumar al total. Los históricos siguen siendo legibles.

`StockCode` identifica el producto. La descripción más frecuente es la etiqueta del catálogo; las variantes no crean productos nuevos. Hay códigos con varias descripciones y nombres compartidos por distintos códigos, por lo que la interfaz muestra también el código.

Cada factura es un conjunto de códigos, independientemente de las cantidades compradas. El corte cronológico es 80% de facturas para entrenamiento y 20% para prueba. El servicio rechaza duplicados factura-producto, campos clave vacíos, particiones vacías, solapamiento de facturas y un corte no cronológico.

Apriori usa los bitsets y la poda de la implementación original. Se corrigió la comparación de soporte en el umbral decimal para evitar excluir, por redondeo de la multiplicación, conjuntos exactamente frecuentes.

Parámetros iniciales: soporte 0.01, confianza 0.50, lift mínimo 1.0001 (estrictamente mayor que 1), tamaño sin límite. No se ajustan silenciosamente. Se aborta al superar un millón de candidatos por nivel, 200,000 reglas o 120 segundos en cada etapa de minería. El límite de tiempo se comprueba cooperativamente; no es una interrupción del proceso por el sistema operativo. MLxtend es opcional y su comparación puede consumir memoria/tiempo adicionales fuera de esos límites.

## Persistencia, caché y evidencia

Cada ejecución recibe un nombre UTC y un identificador único. Nunca sobrescribe otra ejecución. `analisis.json` se escribe al finalizar y actúa como marcador de ejecución completa; incluye parámetros, tamaños, resumen de preparación, duración y huellas SHA-256 de las entradas. El catálogo se copia junto a cada análisis para conservar las etiquetas.

Resultados: `conjuntos_frecuentes.csv`, `reglas_asociacion.csv`, `evaluacion.csv`, `ejemplos_recomendaciones.csv`, `catalogo_productos.csv` y `analisis.json`. Los PNG opcionales se generan con `--graficas`. La interfaz descarga conjuntos, exclusiones, reglas filtradas, evaluación, ejemplos y recomendaciones.

Streamlit mantiene caché de lecturas por ruta y versión del archivo, y el entrenamiento solo ocurre al pulsar “Ejecutar análisis”. Las recomendaciones consultan reglas guardadas; aceptan consecuentes múltiples, exigen el antecedente completo y excluyen productos seleccionados. Se ordenan por confianza, lift, soporte y código para resolver empates de forma reproducible.

La evaluación oculta un producto por canasta de prueba con dos o más productos (semilla 42) y compara hit rate@k con popularidad en entrenamiento. Los ejemplos muestran sugerencias sobre canastas reales completas; no prueban una compra futura. Las asociaciones no implican causalidad.

## Pruebas

```powershell
python -m pytest -q
python -m pip check
```

Incluyen conteo exhaustivo, umbral decimal, contraste con MLxtend, métricas, límites, limpieza, prevención de sobrescritura y persistencia. Las pruebas de AppTest cubren búsqueda, agregar/eliminar/limpiar, ejemplos, actualizaciones, filtros, formatos, exportación y cambio de análisis. Las pruebas con resultados reales se omiten si no hay análisis guardado; el cambio de contexto necesita dos ejecuciones.

AppTest no ofrece una acción directa de selección de filas de tabla. Esa prueba conserva el renderizado real y simula la respuesta del widget para comprobar que la fila seleccionada determina el detalle mostrado.

La validación de interfaz se realizó mediante AppTest y una comprobación HTTP del servidor. No se realizó inspección visual en un navegador automatizado. Existe una advertencia de deprecación de pandas al construir la matriz dispersa para MLxtend; la comparación fue satisfactoria.
