# EcoMix IA: Plataforma web inteligente para el diseño y optimización de mezclas de concreto

**Universidad Privada de Tacna**  
Facultad de Ingeniería  
Escuela Profesional de Ingeniería de Sistemas

**Proyecto:** Sistema de EcoMix IA  
**Curso:** Programación Web II  
**Docente:** Mtro. Enrique Félix LANCHIPA VALENCIA

**Integrantes:**

- Guillén Laveriano, Joel Adrián — 0098018499
- Medina Quispe, Joan Cristian — 2022074255

Tacna – Perú, 2026

**Versión del documento:** 1.0

## Control de versiones

| Versión | Hecha por | Revisada por | Aprobada por | Fecha | Motivo |
| --- | --- | --- | --- | --- | --- |
| 1.0 | JGL, JCM | ELV | ELV | 12/10/2026 | Versión Original |

> Nota de transcripción: el PDF original presenta la tabla de control de versiones dos veces (páginas 2 y 3). Se muestra una sola vez para evitar duplicaciones sin pérdida de información.

## Índice general

- 1. Introducción (p. 5)
  - 1.1. Propósito (p. 5)
  - 1.2. Alcance (p. 5)
  - 1.3. Definiciones, siglas y abreviaturas (p. 6)
  - 1.4. Referencias (p. 7)
  - 1.5. Visión general (p. 8)
- 2. Posicionamiento (p. 8)
  - 2.1. Oportunidad de negocio (p. 8)
  - 2.2. Definición del problema (p. 9)
- 3. Descripción de los interesados y usuarios (p. 10)
  - 3.1. Resumen de los interesados (p. 10)
  - 3.2. Resumen de los usuarios (p. 11)
  - 3.3. Entorno de usuario (p. 12)
  - 3.4. Perfiles de los interesados (p. 12)
  - 3.5. Perfiles de los usuarios (p. 13)
  - 3.6. Necesidades de los interesados y usuarios (p. 13)
- 4. Vista general del producto (p. 15)
  - 4.1. Perspectiva del producto (p. 15)
  - 4.2. Resumen de capacidades (p. 15)
  - 4.3. Suposiciones y dependencias (p. 16)
  - 4.4. Costos y precios (p. 17)
  - 4.5. Licenciamiento e instalación (p. 18)
- 5. Características del producto (p. 19)
- 6. Restricciones (p. 20)
- 7. Rangos de calidad (p. 21)
- 8. Precedencia y prioridad (p. 23)
- 9. Otros requerimientos del producto (p. 25)
  - a. Estándares legales (p. 25)
  - b. Estándares de comunicación (p. 25)
  - c. Estándares de cumplimiento de la plataforma (p. 25)
  - d. Estándares de calidad y seguridad (p. 25)
- Conclusiones (p. 27)
- Recomendaciones (p. 28)
- Bibliografía (p. 29)
- Webgrafía (p. 29)

---

## 1. Introducción

El diseño de mezclas de concreto con cementos altamente adicionados exige equilibrar resistencia a compresión, trabajabilidad, costo y huella de carbono. La búsqueda de proporciones convenientes suele requerir conocimiento especializado y ciclos de ensayo en laboratorio que pueden extenderse hasta los 28 días para verificar la resistencia a esa edad. Esta situación motiva el estudio de herramientas digitales que ayuden a explorar alternativas antes de efectuar las validaciones experimentales.

EcoMix IA se propone como una plataforma web inteligente que combine una base de datos de materiales, un modelo predictivo de resistencia, un mecanismo de optimización de mezclas y un asistente de inteligencia artificial para explicar las recomendaciones. La propuesta surge en el marco del Reto 2 de Yura S.A., presentado para la Hackathon Innova Sur 2026, y se desarrolla académicamente en el curso Programación Web II de la Universidad Privada de Tacna.

La plataforma pretende apoyar al profesional en la evaluación preliminar de formulaciones que alcancen una resistencia objetivo con un costo y una huella de CO₂ estimados menores, sin sustituir los ensayos, los criterios de ingeniería ni las obligaciones normativas correspondientes.

### 1.1. Propósito

El propósito de este documento es establecer la visión inicial de EcoMix IA: el problema al que responde, la oportunidad que representa, los usuarios e interesados, el alcance funcional, las capacidades previstas, las restricciones, las metas de calidad y las prioridades del proyecto.

El informe servirá como referencia común para orientar la planificación, el diseño de la arquitectura, el levantamiento posterior de requisitos y la preparación de un producto mínimo viable (MVP) demostrable. No constituye todavía una especificación exhaustiva de requisitos ni un expediente de validación de ingeniería civil.

### 1.2. Alcance

La primera versión propuesta comprenderá: (a) autenticación y perfiles de administrador e ingeniero; (b) catálogo de materiales, con propiedades, precios y factores de emisión configurables; (c) registro de resistencia objetivo, edad, materiales y parámetros de diseño; (d) predicción de resistencia a 7 y 28 días mediante un modelo entrenado con datos abiertos; (e) generación de por lo menos tres alternativas de mezcla que permitan comparar costo y CO₂; (f) contraste referencial con un diseño obtenido a partir de ACI 211; (g) explicación de recomendaciones mediante un asistente de IA; y (h) historial, reportes PDF y despliegue web previsto en Azure.

Quedan fuera del alcance inicial la ejecución de ensayos físicos, el uso de sensores IoT, la calibración con datos propios de Yura S.A. y la emisión de certificados de conformidad o aprobaciones normativas. Estas posibilidades podrán evaluarse en fases posteriores. Asimismo, la plataforma no automatizará por sí sola la aprobación de una mezcla para una obra real.

### 1.3. Definiciones, siglas y abreviaturas

| Término | Definición aplicada al proyecto |
| --- | --- |
| EcoMix IA | Nombre de la propuesta de sistema web de apoyo al diseño de mezclas de concreto. |
| IA | Inteligencia artificial; en el proyecto incluye predicción basada en datos e interpretación asistida por un modelo generativo. |
| ML / ML.NET | Aprendizaje automático / framework de Microsoft para entrenar y ejecutar modelos en el ecosistema .NET. |
| MVP | Producto mínimo viable con funciones suficientes para demostrar el flujo principal. |
| f’c | Resistencia a compresión del concreto considerada como objetivo de diseño. |
| a/c | Relación agua/cemento; cuando se usan adiciones, deberá distinguirse de la relación agua/material cementante (a/mc). |
| ACI 211 | Referencia técnica del American Concrete Institute para proporcionamiento de mezclas de concreto. |
| CO₂ / CO₂e | Dióxido de carbono / dióxido de carbono equivalente; la unidad ambiental adoptada deberá documentarse. |
| R² | Coeficiente de determinación utilizado para evaluar el ajuste de modelos de regresión. |
| SQL Server | Gestor de base de datos relacional propuesto. |
| API | Interfaz de programación para integrar servicios, incluido el asistente de IA. |
| UCI | UCI Machine Learning Repository, fuente del dataset abierto de resistencia a compresión. |

### 1.4. Referencias

Este informe utiliza como fuente funcional principal la presentación EcoMix IA – Plataforma web inteligente para el diseño y optimización de mezclas de concreto con cementos altamente adicionados (Equipo EcoMix IA, 2026), especialmente sus diapositivas 2 a 6. El documento FD02 – Informe Visión de Proyecto: Sistema de Gestión y Firma Digital de Documentos se ha utilizado únicamente como modelo de estructura y profundidad documental, no como fuente de requisitos de EcoMix IA.

Como fuentes técnicas de consulta se consideran el dataset Concrete Compressive Strength de UCI, el documento ACI PRC-211.1-22, las guías oficiales de ML.NET y ASP.NET Core, la documentación de Azure y el marco peruano de protección de datos personales. Las referencias completas se reúnen en Bibliografía y Webgrafía.

### 1.5. Visión general

Declaración de visión: EcoMix IA será una plataforma web de apoyo a la decisión que permita registrar parámetros de una mezcla de concreto, estimar su resistencia, explorar alternativas con distintos costos y emisiones de CO₂ y presentar comparaciones comprensibles para un ingeniero o responsable técnico.

El flujo previsto es: ingreso de materiales y condiciones → predicción → generación de alternativas → comparación con el diseño de referencia → explicación asistida por IA → almacenamiento y reporte. El producto se concibe como un prototipo académico que demuestre la viabilidad tecnológica de esta secuencia antes de plantear una aplicación industrial.

## 2. Posicionamiento

### 2.1. Oportunidad de negocio

El diseño tradicional de mezclas puede involucrar diversas formulaciones, revisiones y ensayos sucesivos. EcoMix IA plantea una oportunidad de innovación al proporcionar una herramienta que explore computacionalmente alternativas antes de comprometer recursos en todas las pruebas posibles. La utilidad esperada se relaciona con la comparación más rápida de opciones, la documentación de decisiones y la consideración conjunta de variables económicas y ambientales.

La propuesta podría resultar de interés para laboratorios de materiales, ingenieros civiles, áreas técnicas de empresas cementeras, productores de concreto e instituciones académicas. En el contexto del reto de Yura S.A., la oportunidad consiste en presentar una demostración funcional de cómo los datos y la IA pueden complementar el análisis de mezclas con cementos altamente adicionados. No se presupone contrato, patrocinio, validación ni adopción formal por parte de Yura S.A.

| Aspecto | Posicionamiento propuesto |
| --- | --- |
| Para | Profesionales y equipos técnicos que evalúan formulaciones de concreto. |
| Que necesitan | Comparar resistencia estimada, costo y huella de CO₂ de varias mezclas. |
| EcoMix IA es | Una plataforma web de apoyo a la decisión que combina predicción, optimización y explicación. |
| A diferencia de | Un registro manual o una hoja de cálculo aislada, integra comparación, historial y reportes en un mismo flujo. |
| Valor esperado | Explorar alternativas y orientar ensayos posteriores, sin reemplazarlos. |

### 2.2. Definición del problema

Problema central: la exploración de mezclas de concreto que cumplan una resistencia requerida y consideren costo, trabajabilidad y emisiones puede demandar numerosas iteraciones y recursos, mientras que la información necesaria para comparar escenarios no siempre está integrada en una sola herramienta digital.

| Dimensión del problema | Consecuencia potencial | Respuesta prevista de EcoMix IA |
| --- | --- | --- |
| Iteraciones de diseño y ensayo | Mayor tiempo para identificar formulaciones prometedoras. | Preselección de alternativas mediante predicciones y reglas de optimización. |
| Múltiples variables de evaluación | Dificultad para apreciar compensaciones entre resistencia, costo y CO₂. | Comparación unificada en tablas y gráficos. |
| Datos de materiales dispersos | Menor consistencia al preparar diferentes escenarios. | Catálogo centralizado con propiedades, precios y factores ambientales. |
| Interpretación especializada | Resultados poco accesibles para usuarios menos familiarizados con modelos predictivos. | Explicaciones de criterios, supuestos y diferencias entre mezclas. |
| Trazabilidad limitada | Dificultad para repetir una simulación y conocer sus datos de entrada. | Historial con parámetros, resultados y versión del modelo utilizado. |

Esta formulación constituye una hipótesis de necesidad identificada en la presentación inicial y deberá contrastarse con entrevistas o pruebas con profesionales del sector.

## 3. Descripción de los interesados y usuarios

### 3.1. Resumen de los interesados

| Interesado | Interés principal | Responsabilidad o participación prevista |
| --- | --- | --- |
| Equipo EcoMix IA | Desarrollar y demostrar la solución. | Análisis, diseño, programación, entrenamiento, pruebas y presentación. |
| Docente de Programación Web II | Evaluar el proyecto académico. | Seguimiento y retroalimentación metodológica. |
| Yura S.A. (referente del reto) | Soluciones potenciales para el desafío planteado. | Posible evaluación de la pertinencia de la propuesta dentro del evento; colaboración adicional no confirmada. |
| Ingenieros y especialistas en concreto | Consistencia y utilidad de las alternativas. | Posibles entrevistas, revisión de criterios y pruebas de aceptación. |
| Administradores del sistema | Disponibilidad y gestión de datos. | Mantenimiento del catálogo, usuarios y configuración. |
| Organizadores y evaluadores de la hackathon | Evidencia de innovación y viabilidad. | Evaluación del prototipo y de su presentación. |

### 3.2. Resumen de los usuarios

Los roles de aplicación definidos en la presentación inicial son Administrador e Ingeniero. En esta etapa no se incorporan roles adicionales sin una necesidad validada.

| Usuario | Objetivo de uso | Funciones principales |
| --- | --- | --- |
| Administrador | Mantener datos y condiciones de funcionamiento. | Gestionar acceso, roles, materiales, precios y factores de CO₂. |
| Ingeniero | Estudiar una mezcla y alternativas viables. | Definir parámetros, ejecutar predicciones, comparar opciones, revisar explicaciones, consultar historial y exportar informes. |

### 3.3. Entorno de usuario

Se prevé el acceso desde navegadores modernos en computadoras y dispositivos móviles, mediante una interfaz web responsive. En el entorno académico, el equipo utilizará datos abiertos para entrenar el modelo y registros configurables para costos y factores ambientales. En una adopción real se requeriría revisar las condiciones particulares del laboratorio, los materiales disponibles y la conectividad.

El recorrido esperado del ingeniero es el siguiente: iniciar sesión, seleccionar materiales, ingresar la resistencia f’c y demás parámetros, solicitar una predicción para la edad correspondiente, obtener alternativas, revisar la comparación con ACI 211, consultar la explicación y guardar o exportar la evaluación. El administrador tendrá un flujo separado de mantenimiento del catálogo y cuentas.

### 3.4. Perfiles de los interesados

| Perfil | Necesidad / expectativa | Criterio preliminar de éxito |
| --- | --- | --- |
| Equipo de desarrollo | Alcance realizable con los recursos y plazos académicos. | Flujo de demostración completo y documentado. |
| Docente y evaluadores | Correspondencia entre propuesta, requisitos, evidencia y demostración. | Prototipo funcional con resultados reproducibles y límites declarados. |
| Referente empresarial del reto | Potencial utilidad en un contexto de formulación de concretos. | Alternativas comprensibles y técnicamente revisables. |
| Especialista técnico | Reconocer supuestos, datos y restricciones de cada recomendación. | Resultados interpretables, verificables y adecuados para una evaluación preliminar. |

### 3.5. Perfiles de los usuarios

| Campo | Administrador | Ingeniero |
| --- | --- | --- |
| Conocimiento esperado | Manejo básico de sistemas y catálogos técnicos. | Conocimientos de dosificación y propiedades del concreto. |
| Uso principal | Configuración y mantenimiento periódico. | Simulación, comparación y consulta según necesidad. |
| Entradas | Usuarios, materiales, costos, factores de CO₂. | Parámetros de diseño, materiales, resistencias objetivo y edad. |
| Resultados | Catálogos y controles actualizados. | Predicciones, alternativas, gráficos, explicaciones y PDF. |
| Necesidad de seguridad | Gestión restringida por permisos. | Privacidad e integridad de sus diseños almacenados. |

### 3.6. Necesidades de los interesados y usuarios

| Código | Necesidad | Prioridad inicial | Criterio de aceptación preliminar |
| --- | --- | --- | --- |
| N01 | Iniciar sesión con perfil de administrador o ingeniero. | Alta | Acceso diferenciado por rol. |
| N02 | Mantener materiales y propiedades relevantes. | Alta | Crear, consultar y actualizar registros del catálogo. |
| N03 | Ingresar parámetros de una mezcla de referencia. | Alta | Validaciones de valores y unidades. |
| N04 | Obtener resistencia estimada a 7 y 28 días. | Alta | Mostrar valor predicho y datos utilizados. |
| N05 | Generar tres o más alternativas comparables. | Alta | Presentar opciones con resistencia, costo y CO₂ estimados. |
| N06 | Contrastar propuestas con una referencia ACI 211. | Media | Tabla o gráfico con criterios homogéneos de comparación. |
| N07 | Comprender la justificación de alternativas. | Media | Explicación de parámetros y advertencia de límites del modelo. |
| N08 | Revisar simulaciones previas y emitir PDF. | Media | Historial consultable y reporte exportable. |
| N09 | Registrar condiciones y versión del modelo usado. | Alta | Cada recomendación queda asociada a entradas y versión. |

## 4. Vista general del producto

### 4.1. Perspectiva del producto

EcoMix IA se plantea como una aplicación web nueva, con arquitectura basada en ASP.NET Core MVC y C#, vistas Razor, estilos Bootstrap 5, gráficos con Chart.js y persistencia en SQL Server o Azure SQL. El componente predictivo se desarrollará inicialmente con ML.NET, considerando un algoritmo de regresión como FastTree, y el asistente explicativo recurrirá a una API de IA generativa de Claude u OpenAI, pendiente de selección. El despliegue previsto es Azure App Service.

En términos lógicos, la solución estará organizada en interfaz de usuario, servicios de aplicación, repositorio de datos, motor predictivo, generador de alternativas, módulo explicativo y generación de reportes. La predicción y el optimizador deberán mantenerse separados de la IA generativa: las cifras técnicas deben provenir del cálculo o de fuentes estructuradas, mientras que el asistente debe limitarse a interpretarlas y contextualizarlas.

El conjunto de datos abierto de UCI proporciona 1030 observaciones, ocho variables de entrada (componentes y edad) y resistencia a compresión como salida. No contiene de forma directa precios de materiales, factores de CO₂ ni mediciones de asentamiento; por ello, estos aspectos requerirán datos adicionales o criterios claramente declarados. Su cobertura tampoco garantiza validez para todas las puzolanas o cementos altamente adicionados que pudieran emplearse en producción.

### 4.2. Resumen de capacidades

| Capacidad | Beneficio previsto |
| --- | --- |
| Autenticación y roles | Restringe las opciones administrativas y de análisis al perfil autorizado. |
| Catálogo de materiales | Reutiliza propiedades, costos y factores ambientales configurables. |
| Registro de parámetros | Normaliza la información de cada diseño de mezcla. |
| Predicción con ML.NET | Estima la resistencia a compresión para edades definidas. |
| Optimización multiobjetivo | Propone al menos tres alternativas y permite observar compromisos costo–CO₂. |
| Comparador ACI 211 | Incorpora una referencia de dosificación para examinar diferencias. |
| Asistente IA | Presenta una explicación legible de resultados y supuestos. |
| Historial y PDF | Documenta las evaluaciones y permite comunicarlas. |

### 4.3. Suposiciones y dependencias

| Tipo | Enunciado | Riesgo o acción de control |
| --- | --- | --- |
| Suposición | El dataset UCI permitirá entrenar un predictor inicial útil. | Evaluar métricas, sesgos, rangos y comportamiento en datos de prueba. |
| Suposición | Se contará con precios y factores de emisión representativos. | Registrar fuente, fecha y unidad de cada valor; evitar cifras inventadas. |
| Suposición | Los diseños podrán compararse mediante reglas técnicas consistentes. | Revisar restricciones con bibliografía y asesoría en tecnología del concreto. |
| Dependencia | Los datos UCI no incluyen trabajabilidad ni costos ni CO₂. | Incorporar fuentes externas; no atribuir esos cálculos al predictor UCI. |
| Dependencia | El uso de servicios de IA y Azure requiere cuentas y configuración. | Comprobar cuotas, límites, costos y disponibilidad antes de la demostración. |
| Dependencia | La comparación ACI 211 exige parámetros y criterios técnicos adicionales. | Documentar procedimiento y datos base antes de presentar resultados. |
| Dependencia | El dominio de aplicación puede diferir de los registros de entrenamiento. | Indicar que los resultados son preliminares y requieren ensayos. |

### 4.4. Costos y precios

EcoMix IA constituye, por ahora, una propuesta académica y no tiene un precio de comercialización definido. Tampoco se dispone todavía de un presupuesto aprobado de desarrollo o producción. La evaluación económica inicial identificará los rubros siguientes, sin atribuirles importes no verificados.

| Recurso o concepto | Tratamiento económico previsto | Situación inicial |
| --- | --- | --- |
| ASP.NET Core, C# y ML.NET | Tecnologías de desarrollo que pueden utilizarse sin pagar licencia por ML.NET. | Seleccionadas para el prototipo. |
| SQL Server / Azure SQL | Puede utilizarse una edición o entorno apropiado para pruebas; el hospedaje administrado puede generar cargos. | Plan y modalidad pendientes de definir. |
| Azure App Service | Hospedaje de la plataforma según plan contratado. | Costo sujeto a región, configuración y consumo. |
| API de IA generativa | Posible facturación por uso según proveedor y modelo. | Proveedor, cuotas y presupuesto no definidos. |
| Materiales: cemento, escoria, ceniza volante, puzolana, agua, agregados y aditivos | Precios unitarios utilizados como entradas para el cálculo de mezclas, no como precio del software. | Requieren fuente local y fecha de consulta. |
| Factores de emisión | Parámetros para estimar el indicador ambiental por volumen de mezcla. | Requieren fuente metodológica y unidad validada. |
| Trabajo de desarrollo y pruebas | Horas de análisis, programación, documentación y validación. | Esfuerzo académico por estimar. |

Para una mezcla, el costo podrá calcularse de manera preliminar como Costo estimado (S/ por m³) = Σ(cantidad del material por m³ × precio unitario del material). Del mismo modo, CO₂ estimado (kg CO₂e por m³) = Σ(cantidad del material por m³ × factor de emisión del material), siempre que las unidades, los límites del cálculo y las fuentes sean compatibles. Estas fórmulas son una propuesta de cálculo y no constituyen por sí mismas un análisis de ciclo de vida certificado.

### 4.5. Licenciamiento e instalación

ML.NET es un framework abierto distribuido bajo licencia MIT. Para el dataset UCI Concrete Compressive Strength se indica licencia CC BY 4.0, por lo que deben conservarse la atribución y las condiciones correspondientes. Las demás dependencias se revisarán individualmente y el uso de Azure o de APIs generativas se regirá por las condiciones vigentes de sus proveedores.

Para una instalación inicial se prevé: preparar la aplicación ASP.NET Core MVC, configurar SQL Server, cargar el catálogo, integrar el modelo entrenado, parametrizar las credenciales del servicio de IA mediante configuración segura, habilitar autenticación y HTTPS, probar los reportes y publicar en un entorno de Azure adecuado. En el contexto de la hackathon podrá priorizarse una demostración local reproducible si el despliegue público o la integración de terceros comprometen la estabilidad del MVP.

## 5. Características del producto

Las características funcionales se identifican con los mismos códigos de la presentación inicial:

| Código | Característica propuesta | Descripción |
| --- | --- | --- |
| RF01 | Autenticación y roles | El sistema permitirá acceso diferenciado para administrador e ingeniero. |
| RF02 | Gestión de materiales | El administrador podrá mantener materiales, propiedades, costos y factores de CO₂. |
| RF03 | Registro de parámetros | El ingeniero introducirá f’c objetivo, edad, materiales y criterios de trabajabilidad que se definan. |
| RF04 | Predicción de resistencia | El sistema estimará resistencia a compresión a 7 y 28 días a partir de un modelo validado estadísticamente para los datos disponibles. |
| RF05 | Alternativas optimizadas | El sistema generará al menos tres formulaciones comparables, sujetas a restricciones y criterios de costo y CO₂. |
| RF06 | Comparación de diseños | El sistema mostrará tablas y gráficos contrastando alternativas con un diseño de referencia basado en ACI 211. |
| RF07 | Explicación técnica con IA | El asistente resumirá criterios, compensaciones, datos y límites de cada alternativa, sin sustituir la aprobación profesional. |
| RF08 | Historial y reportes | Cada evaluación podrá almacenarse y exportarse en un reporte PDF con entradas, resultados y advertencias. |

El diseño detallado de casos de uso, reglas, excepciones y validaciones quedará para la etapa de especificación de requisitos. El carácter «optimizado» de una mezcla se interpretará siempre respecto de las funciones objetivo, restricciones y datos configurados.

## 6. Restricciones

| Código | Restricción inicial |
| --- | --- |
| R-01 | El producto se desarrollará como sistema web en ASP.NET Core MVC y C#. |
| R-02 | El almacenamiento estructurado utilizará SQL Server o Azure SQL. |
| R-03 | El prototipo utilizará datos públicos para el entrenamiento inicial; no contará todavía con calibración propia de Yura. |
| R-04 | Las predicciones solo serán aplicables dentro de límites razonables de datos y variables disponibles. |
| R-05 | No se ejecutarán ensayos físicos, ni se integrarán sensores IoT en el alcance inicial. |
| R-06 | El resultado del optimizador no equivale a certificación técnica ni normativa. |
| R-07 | Los precios y factores de CO₂ deberán ser identificables, configurables y estar respaldados. |
| R-08 | Las claves de API y credenciales no podrán almacenarse en el código fuente público. |
| R-09 | El asistente generativo no alterará los resultados numéricos obtenidos por el motor de cálculo. |
| R-10 | El tiempo, presupuesto y acceso a servicios externos condicionarán la extensión del MVP. |

## 7. Rangos de calidad

Las medidas siguientes son objetivos de diseño pendientes de comprobación, no resultados obtenidos:

| Atributo | Meta o criterio propuesto | Comprobación prevista |
| --- | --- | --- |
| Exactitud predictiva | R² ≥ 0.85 como objetivo inicial. | Evaluación con datos separados de entrenamiento y reporte de R² y error de predicción. |
| Rendimiento de predicción | Tiempo menor a 2 segundos por consulta normal. | Prueba cronometrada en el ambiente definido. |
| Rendimiento de optimización | Tiempo menor a 10 segundos por solicitud normal. | Medición de múltiples ejecuciones con escenarios comparables. |
| Usabilidad | Interfaz responsive y formularios con validaciones. | Pruebas de flujo desde computadora y dispositivo móvil. |
| Seguridad | ASP.NET Core Identity, HTTPS y secretos fuera del código. | Verificación de controles de acceso, configuración y pruebas básicas. |
| Trazabilidad | Conservar datos de entrada, resultados y versión del modelo. | Reproducción y consulta de simulaciones guardadas. |
| Integridad | Un mismo conjunto de parámetros debe conservar resultados identificables. | Pruebas de persistencia y del reporte generado. |
| Transparencia técnica | Cada propuesta debe indicar supuestos y carácter estimativo. | Revisión de resultados e informes por el equipo técnico. |

## 8. Precedencia y prioridad

Se propone una secuencia de implementación que preserve un flujo demostrable de extremo a extremo. P1 denota imprescindible para el MVP; P2, necesaria para ampliar la demostración; y P3, mejora posterior si el tiempo lo permite.

| Orden | Componente | Prioridad | Dependencia principal |
| --- | --- | --- | --- |
| 1 | Base de datos y catálogo básico | P1 | Estructura de datos y materiales. |
| 2 | Formulario de parámetros y validaciones | P1 | Catálogo y reglas de entrada. |
| 3 | Modelo predictivo de resistencia | P1 | Preparación, entrenamiento y evaluación de datos. |
| 4 | Motor de generación de tres alternativas | P1 | Predictor, costos, factores ambientales y restricciones. |
| 5 | Comparación tabular de alternativas | P1 | Resultados de predicción y optimización. |
| 6 | Autenticación, roles e historial persistente | P2 | Modelo de usuarios y almacenamiento. |
| 7 | Referencia ACI 211 y gráficos comparativos | P2 | Procedimiento técnico y datos de referencia. |
| 8 | Asistente IA y reporte PDF | P2 | Resultados estructurados y plantillas de presentación. |
| 9 | Publicación estable en Azure y mejoras de experiencia | P3 | Integración, configuración y pruebas completas. |

## 9. Otros requerimientos del producto

### a. Estándares legales

El sistema deberá considerar la Ley N.º 29733, Ley de Protección de Datos Personales, y su reglamento aprobado por el Decreto Supremo N.º 016-2024-JUS, en lo que resulte aplicable al tratamiento de cuentas, perfiles e historiales. También deberá observar las licencias y obligaciones de atribución de datasets, software y recursos utilizados.

El uso de criterios ACI para comparar mezclas será referencial y técnico, no una declaración automática de cumplimiento. Ninguna recomendación informática podrá presentarse como aprobación normativa o como sustituto de procedimientos de ensayo y control de calidad exigidos para una aplicación real.

### b. Estándares de comunicación

La interfaz y los servicios del sistema utilizarán mecanismos web compatibles con navegadores actuales, conexiones HTTPS y comunicación estructurada con los servicios internos o externos que se implementen. Las unidades de medida deberán expresarse de forma inequívoca (por ejemplo, kg/m³, MPa, S/m³ y kg CO₂e/m³). Las explicaciones distinguirán predicciones, datos ingresados, hipótesis y resultados calculados.

### c. Estándares de cumplimiento de la plataforma

La solución seguirá el stack planteado: ASP.NET Core MVC (C#), Razor, Bootstrap 5, Chart.js, SQL Server/Azure SQL, ML.NET y Azure App Service. La integración con Claude u OpenAI permanecerá desacoplada para permitir configurar o sustituir el proveedor. Su instalación y distribución deberán respetar las licencias vigentes de las herramientas y los planes utilizados.

### d. Estándares de calidad y seguridad

La plataforma deberá aplicar control de acceso por roles, validación de datos de entrada, gestión segura de credenciales, registro de operaciones relevantes y protección de información almacenada. Las predicciones deberán acompañarse de indicadores de evaluación y límites de uso. Para evitar recomendaciones engañosas, el generador de texto utilizará los resultados estructurados como referencia y no inventará propiedades ni cifras que el sistema no haya calculado.

## Conclusiones

EcoMix IA constituye una propuesta académica de aplicación web orientada a apoyar el análisis preliminar de mezclas de concreto con cementos altamente adicionados. Su aporte planteado es reunir en una misma plataforma el registro de parámetros, la predicción de resistencia, la exploración de alternativas y la comparación de costo y huella de carbono.

La presentación inicial permite delimitar ocho requerimientos funcionales, dos roles principales, un stack basado en ASP.NET Core MVC y ML.NET y metas medibles de predicción y rendimiento. Estos elementos proporcionan una base para elaborar posteriormente la especificación de requisitos, la arquitectura y la planificación del MVP.

La propuesta presenta dependencias que deben resolverse antes de reivindicar utilidad técnica: el dataset abierto proporciona composiciones, edad y resistencia, pero no precios, factores de CO₂ ni asentamiento. Asimismo, se requiere verificar qué tan bien generaliza el modelo a cementos altamente adicionados concretos y documentar el procedimiento de comparación ACI 211.

Por lo tanto, el beneficio de EcoMix IA deberá demostrarse mediante pruebas reproducibles, consulta con especialistas y —en etapas posteriores— validación experimental. La plataforma será una herramienta de apoyo a decisiones, no un reemplazo de la ingeniería ni de los ensayos de laboratorio.

## Recomendaciones

- Conservar el alcance del PPT como referencia y evitar añadir funciones no justificadas durante el desarrollo del MVP.

- Validar el dataset UCI y separar claramente sus variables de los datos adicionales necesarios para costo, CO₂ y trabajabilidad.

- Definir unidades, fuentes, fecha de actualización y restricciones técnicas para cada material del catálogo.

- Entrenar y evaluar el predictor antes de implementar la interfaz explicativa; registrar R² y errores, sin anticipar el cumplimiento de la meta.

- Construir primero un flujo completo de ingreso de datos, predicción y comparación de tres alternativas; incorporar después el resto de componentes.

- Solicitar una revisión conceptual a un especialista en tecnología del concreto antes de presentar recomendaciones como técnicamente viables.

- Documentar la procedencia del método ACI 211 y evitar presentarlo como certificación de los resultados.

- Mantener un presupuesto actualizado de Azure, SQL administrado y uso de APIs, junto con una alternativa de demostración local.

## Bibliografía

## Webgrafía
