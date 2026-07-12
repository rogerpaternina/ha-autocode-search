# Entorno Docker de desarrollo

Este entorno ejecuta la imagen estable de Home Assistant y monta la integración
local desde `../custom_components` en `/config/custom_components`. La
configuración, la base de datos y los archivos creados por Home Assistant se
persisten en `docker/config/`.

No instala HACS ni Broadlink. Configura primero cualquier entidad `remote` que
necesites desde la interfaz de Home Assistant.

## Inicio

Desde la carpeta `docker/` ejecuta:

```sh
docker compose up -d
```

Abre `http://localhost:8123` y completa el asistente inicial de Home Assistant.

## Operación

Ver los registros, incluidos los de `autocode_search` en nivel `debug`:

```sh
docker compose logs -f
```

Reiniciar Home Assistant después de modificar el componente o la configuración:

```sh
docker compose restart
```

La zona horaria del contenedor es `America/Bogota` y el puerto publicado es el
`8123` del host.

