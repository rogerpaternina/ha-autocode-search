# AutoCode Search

![Tests](https://github.com/rogerpaternina/ha-autocode-search/actions/workflows/tests.yml/badge.svg)
![Quality](https://github.com/rogerpaternina/ha-autocode-search/actions/workflows/quality.yml/badge.svg)
![Hassfest](https://github.com/rogerpaternina/ha-autocode-search/actions/workflows/hassfest.yml/badge.svg)

Integración personalizada para [Home Assistant](https://www.home-assistant.io/) que busca automáticamente códigos infrarrojos para tus dispositivos. Consulta múltiples fuentes de códigos IR, los prueba secuencialmente a través de tu emisor infrarrojo y aprende de los resultados exitosos para acelerar futuras búsquedas.

## Características

- **SmartIR** — Códigos de la comunidad SmartIR, filtrados por fabricante, modelo y tipo de dispositivo.
- **IRDB** — Base de datos IRDB con miles de códigos para televisores, receptores AV y más.
- **LIRC** — Soporte para archivos de configuración LIRC instalados en el sistema.
- **Composite Provider** — Combina SmartIR, IRDB y LIRC en una sola búsqueda, eliminando duplicados.
- **Success Memory** — Recuerda los códigos que funcionaron y los prioriza en búsquedas futuras.
- **Persistent Storage** — Los éxitos se guardan en disco y sobreviven reinicios de Home Assistant.
- **Smart Ranking** — Ordena los proveedores según el contexto de la búsqueda (fabricante, modelo, historial).

## Arquitectura

```text
Home Assistant
      │
      ▼
Coordinator
      │
      ▼
SearchEngine ──► SearchSession
      │                │
      ▼                ▼
Composite Provider   SearchFilter
      │
      ├── SmartIR Provider
      ├── IRDB Provider
      └── LIRC Provider
      │
      ▼
Success Memory ◄── Storage Backend
      │
      ▼
Remote Adapter (Broadlink, ESPHome, …)
```

La integración expone sensores de diagnóstico, sensores binarios, botones de confirmación y once servicios para controlar la búsqueda desde Lovelace, automatizaciones o la consola de desarrollador.

Consulta [docs/architecture.md](docs/architecture.md) para diagramas detallados de cada componente.

## Instalación

### Con HACS (recomendado)

1. En HACS, abre **Integraciones** y selecciona el menú de tres puntos.
2. Añade este repositorio como repositorio personalizado de tipo **Integración**.
3. Busca e instala **Autocode Search**.
4. Reinicia Home Assistant.
5. Ve a **Ajustes → Dispositivos y servicios → Añadir integración** y busca **Autocode Search**.

### Manual

1. Copia la carpeta `custom_components/autocode_search` en el directorio `custom_components` de tu configuración de Home Assistant.
2. Reinicia Home Assistant.
3. Añade la integración desde la interfaz.

### Requisitos

- Home Assistant 2026.1.0 o superior.
- Una entidad `remote.*` configurada (Broadlink, ESPHome, etc.).

Matriz completa de compatibilidad: [docs/compatibility.md](docs/compatibility.md).

## Versión actual

**1.0.0-rc1** — Release Candidate. Notas de versión:
[docs/release_notes_v1.md](docs/release_notes_v1.md).

## Configuración

La integración se configura exclusivamente desde la interfaz; no admite configuración YAML.

Durante el asistente de configuración seleccionarás:

| Paso | Descripción |
|------|-------------|
| **Remote** | Entidad `remote.*` que transmitirá los códigos IR. |
| **Device type** | Tipo de dispositivo (TV, aire acondicionado, ventilador, etc.). |
| **Brand** | Marca del dispositivo. |
| **Provider** | Fuente de códigos preferida. |

### Providers

| Valor | Descripción |
|-------|-------------|
| `auto` | Usa el **Composite Provider** que consulta SmartIR, IRDB y LIRC en orden inteligente. |
| `smartir` | Solo códigos de SmartIR. |
| `irdb` | Solo códigos de IRDB. |
| `lirc` | Solo archivos LIRC del sistema. |

### Composite

Cuando el proveedor está en `auto`, el **Composite Provider**:

1. Consulta cada proveedor según el ranking calculado.
2. Elimina códigos duplicados.
3. Devuelve una lista unificada ordenada.

Los sensores **Provider order** y **Provider ranking reason** muestran el orden y el motivo en tiempo real.

### SearchFilter

Al iniciar una búsqueda puedes aplicar filtros opcionales:

| Campo | Efecto |
|-------|--------|
| `manufacturer` | Filtra códigos por fabricante. |
| `model` | Filtra códigos por modelo. |
| `device_type` | Filtra por tipo de dispositivo y se registra en la sesión. |
| `brand` | Metadato de sesión (marca configurada). |
| `command` | Filtra por nombre de comando (p. ej. `POWER`, `MUTE`). |

## Dashboard

Un dashboard Lovelace listo para importar está disponible en [`examples/lovelace-dashboard.yaml`](examples/lovelace-dashboard.yaml).

### Importar el dashboard

1. Copia los helpers de [`examples/entities.yaml`](examples/entities.yaml) y los scripts de [`examples/scripts.yaml`](examples/scripts.yaml) a tu configuración.
2. Ve a **Ajustes → Paneles de control → Añadir panel → Importar desde YAML**.
3. Selecciona `examples/lovelace-dashboard.yaml`.
4. Sustituye `remote.living_room` por tu entidad `remote` configurada.

### Capturas de pantalla

Las capturas de ejemplo están planificadas para la versión estable 1.0.0.
Consulta [docs/roadmap.md](docs/roadmap.md#v10--release-assets).

<!-- Placeholders until screenshots are added -->
![Estado de búsqueda](docs/images/dashboard-status.png)
![Confirmación de resultado](docs/images/dashboard-confirmation.png)
![Estadísticas de aprendizaje](docs/images/dashboard-stats.png)

El dashboard incluye:

- **Estado** — Progreso, tiempo, código actual, fabricante, modelo, proveedor y ranking.
- **Estadísticas** — Éxitos registrados, último éxito, duplicados eliminados y proveedores utilizados.
- **Controles condicionales** — Iniciar, pausar, reanudar, cancelar, confirmar o rechazar según el estado de la búsqueda.
- **Comandos rápidos** — Botones para buscar POWER, VOLUME UP, MUTE e INPUT.

## Servicios

| Servicio | Descripción |
|----------|-------------|
| `autocode_search.start_search` | Inicia una búsqueda y envía el primer código. |
| `autocode_search.next_code` | Envía el siguiente código. |
| `autocode_search.previous_code` | Envía el código anterior. |
| `autocode_search.pause` | Pausa la búsqueda activa. |
| `autocode_search.resume` | Reanuda una búsqueda pausada. |
| `autocode_search.cancel` | Cancela la búsqueda activa. |
| `autocode_search.finish_search` | Finaliza la búsqueda activa. |
| `autocode_search.confirm_success` | Confirma que el último código probado funcionó. |
| `autocode_search.reject_result` | Rechaza el resultado pendiente. |
| `autocode_search.mark_success` | Registra manualmente un código exitoso. |
| `autocode_search.clear_success_memory` | Borra todos los éxitos memorizados. |

### Ejemplo: iniciar búsqueda

```yaml
action: autocode_search.start_search
data:
  entity_id: remote.living_room
  manufacturer: LG
  model: OLED55
  device_type: tv
  brand: lg
  command: POWER
```

## Automatizaciones

Ejemplos completos en [`examples/automations.yaml`](examples/automations.yaml):

| Automatización | Descripción |
|----------------|-------------|
| **Confirmar con botón físico** | Llama a `confirm_success` al pulsar un botón. |
| **Rechazar tras 15 min** | Llama a `reject_result` si no hay respuesta. |
| **Notificación móvil** | Avisa cuando la búsqueda espera confirmación. |
| **Inicio rápido** | Busca POWER en un LG OLED55 conocido. |

## Scripts

Ejemplos en [`examples/scripts.yaml`](examples/scripts.yaml):

| Script | Comando |
|--------|---------|
| `script.search_start` | Inicia búsqueda con los helpers configurados. |
| `script.search_power` | Busca el comando POWER. |
| `script.search_volume_up` | Busca VOLUME UP. |
| `script.search_mute` | Busca MUTE. |
| `script.search_input` | Busca INPUT. |

## Entidades expuestas

La integración crea un dispositivo **Autocode Search** con sensores de diagnóstico, sensores binarios y botones:

| Entidad | Tipo | Descripción |
|---------|------|-------------|
| Progress | sensor | Porcentaje de progreso (0–100). |
| Codes tested | sensor | Códigos probados hasta el momento. |
| Total codes | sensor | Total de códigos tras filtrar. |
| Current command | sensor | Comando IR actual. |
| Current manufacturer | sensor | Fabricante del código actual. |
| Current model | sensor | Modelo del código actual. |
| Elapsed time | sensor | Tiempo transcurrido (HH:MM:SS). |
| Filter summary | sensor | Resumen del filtro activo. |
| Providers used | sensor | Proveedores consultados. |
| Duplicates removed | sensor | Duplicados eliminados por el composite. |
| Provider order | sensor | Orden de proveedores aplicado. |
| Provider ranking reason | sensor | Motivo del ranking. |
| Success records | sensor | Éxitos memorizados. |
| Last success | sensor | Último éxito registrado. |
| Last provider | sensor | Proveedor del último código probado. |
| Last tested command | sensor | Último comando probado. |
| Running | binary_sensor | `on` mientras la búsqueda está en ejecución. |
| Waiting confirmation | binary_sensor | `on` cuando espera confirmación del usuario. |
| Confirm success | button | Confirma el resultado. |
| Reject result | button | Rechaza el resultado. |

## Desarrollo

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para instrucciones de desarrollo, tests y calidad de código.

### Herramientas de desarrollo

| Herramienta | Uso |
|-------------|-----|
| `tools/benchmark.py` | Medir tiempos de carga de proveedores y memoria |
| `tools/coverage.sh` | Ejecutar pytest con informe HTML de cobertura |
| `tools/release_check.py` | Validar preparación de release antes de etiquetar |
| `docs/profiling.md` | Guía de cProfile y py-spy |

Entorno Docker disponible en [`docker/`](docker/).

## Licencia

Este proyecto se distribuye bajo la [licencia MIT](LICENSE).
