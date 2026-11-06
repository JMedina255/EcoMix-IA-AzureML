# Lista de Verificación y Plan de Contingencia — EcoMix IA (Fase 6.4)
## Protocolo Operativo para la Demostración en Vivo ante el Jurado

**Objetivo:** Garantizar una ejecución técnica impecable de la sustentación de 3 minutos, previendo contingencias de red, arranque en frío de la nube y desacoplamiento de entorno.

---

## 1. Fase Preflight (T-15 minutos antes de la sustentación)

- [ ] **1.1 Conectividad a Internet:**
  - Comprobar que la laptop del expositor cuente con acceso a internet activo y estable (red del auditorio o punto de acceso móvil 4G/5G).
  - Verificar conectividad básica con Azure ejecutando en PowerShell:
    ```powershell
    Test-NetConnection -ComputerName ca-ecomix-inference-api.salmontree-d9db53a4.chilecentral.azurecontainerapps.io -Port 443
    ```
- [ ] **1.2 Secretos Locales del Servidor Web:**
  - Confirmar que el archivo `Web.Secrets.config` exista en la raíz del repositorio web (`C:\Users\Admin\Desktop\Proyectos\ML EcomixIA Sistema\Web.Secrets.config`).
  - Verificar que contenga las claves válidas:
    ```xml
    <appSettings>
      <add key="EcoMix:MlServiceEndpoint" value="https://ca-ecomix-inference-api.salmontree-d9db53a4.chilecentral.azurecontainerapps.io/api/v1/predict/concrete-strength" />
      <add key="EcoMix:MlServiceApiKey" value="[CLAVE_PRIVADA_AZURE]" />
      <add key="EcoMix:MlServiceTimeoutSeconds" value="45" />
    </appSettings>
    ```
- [ ] **1.3 Compilación y Servidor Web Local (IIS Express):**
  - Iniciar IIS Express mediante el archivo de configuración del proyecto:
    ```powershell
    & "C:\Program Files\IIS Express\iisexpress.exe" /config:"C:\Users\Admin\Desktop\Proyectos\ML EcomixIA Sistema\.vs\EcomixIA\config\applicationhost.config" /site:"EcomixIA"
    ```
  - Abrir el navegador en `https://localhost:44357/Mezclas/Simulador` y verificar que la página cargue limpiamente.

---

## 2. Fase de Calentamiento Cloud (T-5 minutos antes de la sustentación)

> [!TIP]
> **Estrategia frente al Cold Start:**  
> En reposo, Azure Container Apps escala a cero réplicas para no consumir saldo. El primer arranque toma entre 8.4 y 8.8 segundos. Para que la demostración de 3 minutos sea ágil y las respuestas tarden solo ~130 ms, se recomienda realizar una petición previa de precalentamiento (*warm-up*).

- [ ] **2.1 Petición de Calentamiento:**
  - En el formulario web abierto, presionar el botón **«Canónica (280 kg cto)»** y pulsar **«Predecir Resistencia con EcoMix IA»**.
  - Si el clúster estaba en cero réplicas, esperar los ~8.5 segundos del arranque inicial.
  - Una vez desplegado el resultado (21.96 / 31.15 MPa), el contenedor permanecerá activo durante los siguientes 10 a 15 minutos en estado caliente.
- [ ] **2.2 Limpiar la Pantalla:**
  - Recargar la página (`F5`) para que el formulario quede listo y en blanco para la presentación.

---

## 3. Guía de Ejecución en Vivo (Durante los 3 Minutos)

| Tiempo | Paso del Operador | Discurso del Orador | Resultado Esperado |
|:---:|---|---|---|
| **0:55** | Clic en preset **«Canónica (280 kg cto)»** | Explica la mezcla convencional de control ($280\text{ kg}$ cto, $a/c = 0.64$). | Formulario poblado instantáneamente. |
| **1:05** | Clic en **«Predecir Resistencia»** | Señala el despacho seguro y la comunicación de servidor a servidor. | Tarjetas: **21.96 MPa** (7d), **31.15 MPa** (28d), 0 advertencias ACI. |
| **1:35** | Clic en preset **«Ecológica (54.5% SCM)»** | Introduce el Reto 2 de Yura: sustitución del 46.4% de clínker por escoria y ceniza. | Formulario con $150\text{ kg}$ cto, $100\text{ kg}$ escoria, $80\text{ kg}$ ceniza. |
| **1:45** | Clic en **«Predecir Resistencia»** | Destaca la velocidad en caliente (~139 ms) y superación de los 25 MPa estructurales. | Tarjetas: **25.98 MPa** (7d), **33.61 MPa** (28d), 2 advertencias ACI ámbar. |
| **2:05** | Señala las advertencias ACI | Explica la importancia de extender el curado húmedo por cinética puzolánica. | Tarjetas explicativas de durabilidad y curado visibles. |
| **2:15** | Clic en preset **«Inválida»** y Clic en **«Predecir»** | Explica la doble barrera: ModelState local vs HTTP 422 ProblemDetails en Azure. | Banner rojo estructurado; la aplicación sigue operando sin caídas. |

---

## 4. Plan de Contingencia Técnico (Falla de Red o Caída Cloud)

Si durante la sustentación falla la conexión a internet del aula o el servicio en la nube experimenta latencias excesivas, el equipo aplicará inmediatamente el protocolo de contingencia **sin improvisar valores sintéticos ni alterar el código**:

```
                               ¿Falla de Conexión?
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                 [SÍ - RED INESTABLE]       [SÍ - TOTALMENTE OFFLINE]
                         │                         │
                         ▼                         ▼
                  CONTINGENCIA A            CONTINGENCIA B
             Visor Interactivo Local   Galería de Evidencias Reales
             (docs-interactive/...)    (docs/evidencias-fase-6-3/...)
```

### Protocolo de Contingencia A — Visor Interactivo Local:
1. Abrir en el navegador local el archivo:  
   [`C:\Users\Admin\Desktop\Proyectos\ML EcomixIA Sistema\docs-interactive\index.html`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs-interactive/index.html).
2. Presentar la arquitectura general interactiva, el flujo del ingeniero y la ficha técnica de los modelos.

### Protocolo de Contingencia B — Galería de Evidencias Verificadas:
1. Proyectar directamente las capturas auténticas de alta resolución obtenidas en la Fase 6.3 ubicadas en:  
   [`docs/evidencias-fase-6-3/`](file:///C:/Users/Admin/Desktop/Proyectos/ML%20EcomixIA%20Sistema/docs/evidencias-fase-6-3/).
2. Demostrar con las capturas `03-prediccion-convencional-completada.png` y `04-prediccion-ecologica-advertencias.png` los resultados del VotingEnsemble y la telemetría oficial de Azure.
3. Declarar con honestidad académica:  
   *"Debido a la inestabilidad de la red del recinto, proyectamos las evidencias de ejecución obtenidas directamente durante la auditoría de integración previa en Chile Central."*

---

## 5. Post-Demostración

- [ ] Cerrar la consola de IIS Express con `Ctrl+C` en la terminal.
- [ ] No dejar procesos colgados consumiendo memoria.
- [ ] Comprobar que no se hayan generado archivos sin seguimiento en Git (`git status`).
