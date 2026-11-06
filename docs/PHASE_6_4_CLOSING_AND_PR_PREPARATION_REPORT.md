# Informe de Cierre, Evidencias y Preparación de Sustentación — Fase 6.4-R

**Proyecto:** EcoMix IA  
**Marco:** Reto 2 de Yura S.A. | Hackathon Innova Sur 2026 | Universidad Privada de Tacna  
**Repositorio ML:** `JMedina255/EcoMix-IA-AzureML` (Rama: `fix/phase-05-api-hardening`)  
**Repositorio Web:** `joeguillenl/EcomixIA` (Rama: `feat/integration-fastapi-service`)  
**Servicio Cloud:** `ca-ecomix-inference-api` en Azure Container Apps (`chilecentral`)  
**Fecha:** Noviembre 2026  
**Veredicto:** **FASE 6.4-R COMPLETADA AL 100% — MÉTRICAS OFICIALES CERTIFICADAS Y PAQUETE DE SUSTENTACIÓN AJUSTADO**

---

## 1. Resumen Ejecutivo y Correcciones de la Revisión (Fase 6.4-R)

En esta revisión final se aplicaron rigurosamente las correcciones conceptuales y métricas oficiales sobre la documentación de sustentación:

1. **Alineación con el Reporte Oficial de Evaluación (`reports/evaluation_wheat_cheese_4swj34tkjn.json`):**
   - **MAE Oficial:** Corregido de 3.48 MPa al valor auditado exacto de **$3.2822\text{ MPa}$**.
   - **Métricas Globales Certificadas:**
     - Coeficiente de Determinación: **$R^2 = 0.9121$**
     - Error Cuadrático Medio: **$\text{RMSE} = 4.7592\text{ MPa}$**
     - Error Absoluto Medio: **$\text{MAE} = 3.2822\text{ MPa}$**
     - Error Normalizado: **$\text{NRMSE} = 0.0673\text{ (6.73\%)}$**
2. **Delimitación Precisa del Alcance del Reto 2 de Yura S.A.:**
   - Se precisó que la funcionalidad demostrada corresponde al **núcleo de inferencia en tiempo real de resistencia ($f'_c$) y análisis exploratorio de sustitución de SCM** en el simulador interactivo.
   - **Trabajo Pendiente (Fase 7):** El motor de optimización multiobjetivo automatizado para minimizar simultáneamente costo económico ($\text{S/./m}^3$) y huella de carbono ($\text{kg CO}_2\text{e/m}^3$) continúa en desarrollo.
3. **Carácter Informativo de las Reglas del Validador ACI:**
   - Las advertencias (`WARN_HIGH_SCM_REPLACEMENT`, `WARN_HIGH_WATER_CEMENT_RATIO`) se presentan explícitamente como **reglas técnicas informativas y preventivas** basadas en las directrices de curado del código **ACI PRC-211.1-22**.
   - **No constituyen certificación oficial ACI ni aprobación estructural.**
4. **Diferenciación de Barreras de Validación en Diagrama y Guion:**
   - **Validación Local (ASP.NET MVC 5):** Intercepción sintáctica inmediata (`ModelState.IsValid`) en **~8 ms sin costo en Azure**.
   - **Validación Remota (FastAPI / Azure Container Apps):** Intercepción de inconsistencias físicas de mezcla (relación $w/b > 4.0$) mediante **HTTP 422 Unprocessable Entity** bajo **RFC 7807 ProblemDetails** en **~163 ms**.

---

## 2. Auditoría del Catálogo de Evidencias Visuales

Se verificaron las 7 capturas de pantalla de [`docs/evidencias-fase-6-3/`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/evidencias-fase-6-3/):

| N° | Archivo | Peso | Contenido Auténtico | Estado DevSecOps |
|:---:|---|:---:|---|:---:|
| 1 | `01-pagina-principal-navegacion.png` | 135.9 KB | Portal EcoMix IA con acceso al Simulador ML | Sin secretos |
| 2 | `02-formulario-simulador-vacio.png` | 145.2 KB | Formulario con 7 inputs en kg/m³, presets y descargo ético | Sin secretos |
| 3 | `03-prediccion-convencional-completada.png` | 182.7 KB | Caso 1 (Canónica): 280 kg cto $\rightarrow$ 21.96 / 31.15 MPa, a/c 0.643 | Paridad 100% VotingEnsemble |
| 4 | `04-prediccion-ecologica-advertencias.png` | 198.0 KB | Caso 2 (Exploración SCM): 150 cto + 180 SCM $\rightarrow$ 25.98 / 33.61 MPa + 2 Reglas Informativas ACI | Viabilidad exploratoria acreditada |
| 5 | `05-manejo-dosificacion-invalida.png` | 137.5 KB | Banner rojo con errores detallados (Doble barrera) | Manejo robusto sin caídas de UI |
| 6 | `06-resultado-peticion-http.png` | 66.4 KB | Inspección DevTools con POST 200 y JSON sanitizado | `X-API-Key: [REDACTED]` confirmado |
| 7 | `07-azure-container-apps-estado.png` | 55.9 KB | Consola Azure CLI: `ca-ecomix-inference-api` Succeeded | 0 réplicas en reposo ($0.00 cómputo) |

Trazabilidad completa documentada en [`docs/MATRIZ_EVIDENCIAS_PRESENTACION.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/MATRIZ_EVIDENCIAS_PRESENTACION.md).

---

## 3. Paquete de Presentación Ajustado

Se sincronizaron los cuatro documentos clave:
1. [`PRESENTACION_ECOMIX_IA_AVANCE.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/PRESENTACION_ECOMIX_IA_AVANCE.md): Ocho diapositivas proyectables con métricas oficiales ($R^2=0.9121$, $\text{RMSE}=4.7592\text{ MPa}$, $\text{MAE}=3.2822\text{ MPa}$), alcance claro y diagramas.
2. [`GUION_EXPOSICION_ECOMIX_IA.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/GUION_EXPOSICION_ECOMIX_IA.md): Guion cronometrado para exposición técnica de 3 minutos exactos (180 s) con pautas críticas para los presentadores.
3. [`MATRIZ_EVIDENCIAS_PRESENTACION.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/MATRIZ_EVIDENCIAS_PRESENTACION.md): Trazabilidad cruzada entre diapositivas, capturas, componentes C#/Python, códigos HTTP y métricas oficiales.
4. [`CHECKLIST_DEMO_ECOMIX_IA.md`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/CHECKLIST_DEMO_ECOMIX_IA.md): Protocolo preflight (T-15 min), precalentamiento cloud (T-5 min) y contingencia técnica offline.

---

## 4. Estado de Preparación para Edición en Canva

El contenido de las 8 diapositivas se encuentra completamente delimitado y redactado en lenguaje de síntesis visual, ideal para transferir a una plantilla corporativa o académica en Canva:
- Textos cortos y directos (máximo 4 bullets por lámina).
- Métricas destacadas en tipografía grande ($R^2=0.9121$, $3.28\text{ MPa}$, $139\text{ ms}$).
- Espacios designados para incrustar las capturas de pantalla de [`docs/evidencias-fase-6-3/`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/evidencias-fase-6-3/).
- Diagramas de flujo y arquitectura exportables en formato vectorial/Mermaid.

---

## 5. Dictamen Final y Recomendaciones

1. **Gobernanza:** Todos los valores numéricos coinciden con los artefactos de evaluación certificados en Azure ML.
2. **Control de Versiones:** Los cambios documentales quedan asentados en commits atómicos locales en ambas ramas sin realizar push ni merge.
