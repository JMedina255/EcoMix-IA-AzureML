# 🏛️ EcoMix IA — Documentación Interactiva con Archify

Portal de arquitectura técnica y diagramas de flujo interactivos para el proyecto **EcoMix IA**, generados y validados con [Archify 3.2](https://github.com/tt-a1i/archify).

El proyecto se fundamenta en el documento oficial de ingeniería y diseño de producto:  
📄 [**FD02-EPIS — Informe Visión de Proyecto: EcoMix IA**](../FD02-EPIS-Informe_Vision_EcoMixIA.md) (Versión 1.0, 12/10/2026), formulado en el marco del **Reto 2 de Yura S.A.** para la **Hackathon Innova Sur 2026** (asignatura Programación Web II, Universidad Privada de Tacna; autores: Joel Adrián Guillén Laveriano y Joan Cristian Medina Quispe; docente: Mtro. Enrique Félix Lanchipa Valencia).

---

## 📂 1. Estructura de Archivos

```text
docs/
├── FD02-EPIS-Informe_Vision_EcoMixIA.md # Documento maestro de visión y especificación funcional v1.0
└── archify/
    ├── index.html                       # Portal interactivo principal (Página de inicio responsive)
    ├── diagrams/                        # Artefactos HTML interactivos y recibos de entrega
    │   ├── 02-arquitectura-general.html # Diagrama D02: Arquitectura General del Sistema
    │   ├── 03-flujo-ingeniero.html      # Diagrama D03: Flujo Funcional del Ingeniero
    │   ├── *.browser-check.json         # Recibos de comprobación en navegador real (Chrome headless)
    │   ├── *.visual-check.html          # Contact sheet visual con capturas automáticas
    │   └── *.visual-check.*.png         # Capturas en resoluciones 1440x900 y 2048x1320 (Light/Dark)
    ├── sources/                         # Especificaciones maestras editables en formato JSON
    │   ├── 02-arquitectura-general.json # Fuente D02 (schema_version: 1, type: architecture)
    │   └── 03-flujo-ingeniero.json      # Fuente D03 (schema_version: 2, type: workflow)
    ├── assets/                          # Recursos estáticos adicionales
    └── README.md                        # Guía de reproducción, validación y contratos técnicos
```

---

## ⚙️ 2. Prerrequisitos y Dependencias

- **Node.js**: Versión 18 o superior (entorno verificado con `v22.17.1`).
- **Archify**: Habilidad instalada en el entorno o ejecutable en `~/.agents/skills/archify/bin/archify.mjs`.
- **Google Chrome**: Opcional/Recomendado para comprobaciones automatizadas de renderizado real (`browser-check` y `visual-check`).
- **Git**: Repositorio clonado con historial para trazabilidad de código en `meta.repository.revision`.

---

## 🚀 3. Instrucciones de Exploración

1. **Abrir el Portal Principal:**  
   Abre [`docs/archify/index.html`](index.html) en cualquier navegador web moderno (Edge, Chrome, Firefox, Safari). Proporciona navegación unificada, matriz de auditoría de componentes y fundamentación técnica.

2. **Exploración de Diagramas:**  
   Desde el portal o directamente desde la carpeta `diagrams/`:
   - [**D02 — Arquitectura General**](diagrams/02-arquitectura-general.html): Vista modular interactiva con zoom, foco semántico, límites de subsistemas (*boundaries*), trazado ortogonal estricto y tarjetas de contexto de ingeniería.
   - [**D03 — Flujo Funcional del Ingeniero**](diagrams/03-flujo-ingeniero.html): Diagrama de carriles (*swimlanes*) en 5 niveles operativos (Usuario, Web MVC, Optimizador, Predictor/IA y Excepciones), con animación de pulso (*signal-flow*), validaciones físicas y degradación suave ante fallos.

---

## 🛠️ 4. Validación y Regeneración de Diagramas

Los diagramas son artefactos verificados contra los esquemas oficiales de Archify (`architecture.schema.json` y `workflow.schema.json`) y sus compuertas de calidad (*showcase quality profile*).

### A. Validar Especificaciones JSON

```bash
# Validar Diagrama D02 (Arquitectura General)
node "$HOME/.agents/skills/archify/bin/archify.mjs" validate architecture docs/archify/sources/02-arquitectura-general.json --quality showcase --repo-root . --json

# Validar Diagrama D03 (Flujo del Ingeniero)
node "$HOME/.agents/skills/archify/bin/archify.mjs" validate workflow docs/archify/sources/03-flujo-ingeniero.json --quality showcase --repo-root . --json
```

### B. Regenerar Artefactos HTML (Finalize)

El comando `finalize` ejecuta de manera atómica las 4 compuertas oficiales: **validación de esquema**, **compilación y entrega (*deliver*)**, **verificación estricta de artefacto (*check*)** y **comprobación en navegador real (*browser-check*)**:

```bash
# Regenerar D02 (Arquitectura)
node "$HOME/.agents/skills/archify/bin/archify.mjs" finalize architecture docs/archify/sources/02-arquitectura-general.json docs/archify/diagrams/02-arquitectura-general.html --quality showcase --repo-root . --json

# Regenerar D03 (Workflow)
node "$HOME/.agents/skills/archify/bin/archify.mjs" finalize workflow docs/archify/sources/03-flujo-ingeniero.json docs/archify/diagrams/03-flujo-ingeniero.html --quality showcase --repo-root . --json
```

### C. Inspección Visual Automatizada (Visual Check)

```bash
node "$HOME/.agents/skills/archify/bin/archify.mjs" visual-check docs/archify/diagrams/02-arquitectura-general.html --json
node "$HOME/.agents/skills/archify/bin/archify.mjs" visual-check docs/archify/diagrams/03-flujo-ingeniero.html --json
```

---

## 📐 5. Reglas Arquitectónicas y Contratos Técnicos (FD02)

1. **Aislamiento del Predictor ML (UCI 165):**
   - El modelo de Machine Learning toma 8 características físicas del dataset UCI ID 165 (cemento, escoria, ceniza, agua, aditivo superplastificante, grava, arena) y la edad de curado en días (`age = 7` y `age = 28`).
   - La resistencia requerida $f'_c$ es una restricción/objetivo del optimizador, **no** una variable de entrada del modelo ML.
   - El dataset UCI **no** contiene precios, factores de emisión ni medición de trabajabilidad (*slump*); por tanto, el predictor **nunca** calcula costos ni $\text{CO}_2\text{e}$.

2. **Fórmulas Analíticas de Sostenibilidad (FD02 §4.4):**
   - **Costo preliminar:** $\text{Costo/m}^3 = \sum (\text{cantidad}_i \times \text{precio unitario}_i)$ en $\text{S/./m}^3$.
   - **Huella ambiental:** $\text{CO}_2\text{e/m}^3 = \sum (\text{cantidad}_i \times \text{factor emisión}_i)$ en $\text{kg CO}_2\text{e/m}^3$.
   - **Distinción tecnológica:** Se distingue estrictamente la relación agua/cemento ($a/c$) de la relación agua/material cementante ($a/mc$) cuando se incorporan adiciones minerales (escoria, ceniza volante).

3. **Gobernanza del Asistente IA (R-09, RF07):**
   - El asistente de IA generativa (Claude / OpenAI) traduce e interpreta cualitativamente los resultados calculados; tiene **estrictamente prohibido** alterar, inventar o recalcular datos numéricos.
   - Si la API del LLM no responde o agota su cuota, la plataforma asegura **degradación suave**: los resultados numéricos, tablas y gráficos continúan presentándose y exportándose sin interrupción.

4. **Metas de Calidad (FD02 §7):**
   - Exactitud predictiva: $R^2 \ge 0.85$.
   - Latencia de inferencia predictiva: $< 2\text{ s}$.
   - Latencia de optimización multiobjetivo: $< 10\text{ s}$.
   - Trazabilidad e integridad (N09): almacenamiento persistente en SQL Server de parámetros de entrada, resultados y versión del modelo.

5. **Orden de Precedencia de Implementación (FD02 §8):**
   - **P1 (MVP Imprescindible):** Catálogo de materiales $\rightarrow$ Formulario de parámetros $\rightarrow$ Predictor ML 7d/28d $\rightarrow$ Generador de 3 alternativas $\rightarrow$ Tabla comparativa.
   - **P2 (Ampliación Demostración):** Autenticación y roles $\rightarrow$ Referencia ACI PRC-211.1-22 con gráficos Chart.js $\rightarrow$ Asistente IA y reporte PDF.
   - **P3 (Post-MVP):** Despliegue en Azure App Service y mejoras de experiencia de usuario.
