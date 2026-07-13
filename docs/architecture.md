# Arquitectura de AutoCode Search

Este documento describe la arquitectura completa de la integración AutoCode Search para Home Assistant.

## Visión general

```text
┌─────────────────────────────────────────────────────────────┐
│                      Home Assistant                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Sensors  │  │ Binary   │  │ Buttons  │  │ Services  │  │
│  │          │  │ Sensors  │  │          │  │           │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬─────┘  │
│       │             │             │               │         │
│       └─────────────┴─────────────┴───────────────┘         │
│                            │                                │
│                     ┌──────▼──────┐                         │
│                     │ Coordinator │                         │
│                     └──────┬──────┘                         │
└────────────────────────────┼────────────────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │        SearchEngine          │
              │  ┌────────────────────────┐  │
              │  │    SearchSession       │  │
              │  └────────────────────────┘  │
              └──────────────┬──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │     Composite Provider       │
              │  ┌────────┐ ┌──────┐ ┌────┐  │
              │  │SmartIR │ │ IRDB │ │LIRC│  │
              │  └────────┘ └──────┘ └────┘  │
              │         ProviderRanking       │
              └──────────────┬──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │       Success Memory         │
              │    SuccessRepository         │
              │    StorageBackend            │
              └──────────────┬──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │      Remote Adapter          │
              │  HomeAssistantRemoteAdapter  │
              │  ┌──────────────────────┐  │
              │  │ BroadlinkRawStrategy │  │
              │  │   GenericStrategy    │  │
              │  └──────────────────────┘  │
              └──────────────┬──────────────┘
                             │
                     remote.send_command
```

## Capas

### Home Assistant

La capa de presentación incluye:

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| Config Flow | `config_flow.py` | Asistente de configuración (remote, tipo, marca, proveedor). |
| Coordinator | `coordinator.py` | Sincroniza el estado del motor con las entidades HA. |
| Services | `services.py` | Registra y ejecuta los 11 servicios del dominio. |
| Sensors | `sensor.py` | 16 sensores de diagnóstico de solo lectura. |
| Binary Sensors | `binary_sensor.py` | `running` y `waiting_confirmation`. |
| Buttons | `button.py` | `confirm_success` y `reject_result`. |
| Diagnostics | `diagnostics.py` | Datos de diagnóstico para soporte. |

### SearchEngine

El motor central (`engine/search_engine.py`) gestiona el ciclo de vida de una búsqueda:

```text
start_search ──► load codes ──► send code ──► next/previous
                     │              │
                     ▼              ▼
                  pause/resume   finish/cancel
                     │              │
                     ▼              ▼
              awaiting_confirmation
                     │
              confirm / reject
```

- **SearchSession** (`models/search_session.py`) — Almacena el estado de la sesión activa: códigos, índice actual, filtros, tiempos y metadatos.
- **SearchFilter** (`models/search_filter.py`) — Filtros opcionales por fabricante, modelo, tipo y comando.
- **IRCode** (`models/ir_code.py`) — Modelo de un código infrarrojo con payload, protocolo, proveedor y metadatos.

### Providers

```text
                    CompositeCodeProvider
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    SmartIRProvider   IRDBProvider   LIRCProvider
           │               │               │
    smartir.py          irdb.py         lirc.py
           │               │               │
    InMemoryCodeProvider (tests)
```

| Provider | Fuente | Descripción |
|----------|--------|-------------|
| **SmartIR** | Archivos JSON de SmartIR | Códigos comunitarios filtrados por dispositivo. |
| **IRDB** | Base de datos IRDB | Miles de códigos para múltiples categorías. |
| **LIRC** | Archivos `.lircd.conf` | Códigos del sistema LIRC instalado. |
| **Composite** | Todos los anteriores | Unifica, deduplica y ordena según ranking. |
| **InMemory** | Lista en memoria | Proveedor de pruebas. |

**ProviderRanking** (`providers/ranking.py`) determina el orden de consulta según el contexto de la búsqueda y el historial de éxitos.

### Learning

```text
confirm_success / mark_success
         │
         ▼
   SuccessMemory
         │
         ▼
  SuccessRepository
         │
         ▼
  StorageBackend (disco)
```

- **SuccessMemory** (`memory/success_memory.py`) — Almacén en memoria de códigos exitosos con búsqueda por contexto.
- **SuccessRepository** (`storage/success_repository.py`) — Capa de persistencia sobre el backend de almacenamiento.
- **StorageBackend** (`storage/storage_backend.py`) — Escritura y lectura JSON en el directorio de configuración de HA.

### Remote Adapter

```text
+--------------+
| SearchEngine |
+--------------+
        │
        v
+--------+
| IRCode |
+--------+
        │
        v
+----------------------+
| HomeAssistantRemote  |
|      Adapter         |
+----------------------+
        │
   ┌────┴────┐
   ▼         ▼
Broadlink  Generic
Strategy   Strategy
   │         │
   └────┬────┘
        v
+---------------------+
| remote.send_command |
+---------------------+
```

Cuando el adaptador detecta que la entidad `remote` pertenece a Broadlink y recibe un paquete Base64 válido, selecciona **BroadlinkRawStrategy** que añade el prefijo `b64:` antes de llamar a `remote.send_command`. Los demás códigos pasan por **GenericStrategy** sin modificación.

Consulta [broadlink_protocol.md](broadlink_protocol.md) para detalles del protocolo Broadlink.

## Flujo de una búsqueda

```text
Usuario                Services           Coordinator        SearchEngine
   │                      │                    │                  │
   │── start_search ─────►│                    │                  │
   │                      │── create session ─►│── start ────────►│
   │                      │                    │                  │── load codes
   │                      │                    │                  │── send code #1
   │                      │                    │◄── update ───────│
   │◄── sensors update ───│◄───────────────────│                  │
   │                      │                    │                  │
   │── next_code ────────►│                    │── next ─────────►│
   │                      │                    │                  │── send code #2
   │                      │                    │                  │
   │── pause ────────────►│                    │── pause ────────►│
   │── resume ───────────►│                    │── resume ───────►│
   │── cancel ───────────►│                    │── cancel ───────►│
   │                      │                    │                  │
   │── confirm_success ──►│                    │── confirm ──────►│
   │                      │                    │                  │── save to memory
```

## Estructura de directorios

```text
custom_components/autocode_search/
├── __init__.py              # Setup / unload
├── manifest.json
├── config_flow.py           # UI configuration
├── coordinator.py           # State bridge
├── services.py              # HA services
├── services.yaml            # Service schemas
├── sensor.py                # Diagnostic sensors
├── binary_sensor.py         # Running / confirmation
├── button.py                # Confirm / reject buttons
├── const.py                 # Constants
├── diagnostics.py           # Debug data
├── success_workflow.py      # Confirmation workflow
├── adapters/
│   ├── base.py
│   ├── broadlink.py
│   └── home_assistant_remote.py
├── engine/
│   └── search_engine.py
├── memory/
│   ├── models.py
│   └── success_memory.py
├── models/
│   ├── ir_code.py
│   ├── search_filter.py
│   └── search_session.py
├── providers/
│   ├── base.py
│   ├── composite.py
│   ├── factory.py
│   ├── filtering.py
│   ├── irdb.py
│   ├── lirc.py
│   ├── memory.py
│   ├── ranking.py
│   └── smartir.py
└── storage/
    ├── storage_backend.py
    └── success_repository.py
```

## Restricciones de diseño

- **Una sola instancia** — `single_config_entry: true` en el manifest.
- **Sin configuración YAML** — Todo se configura desde el Config Flow.
- **Sin dependencias externas** — `requirements: []` en el manifest.
- **Arquitectura estable** — El motor, proveedores y memoria no deben modificarse sin un sprint dedicado.
