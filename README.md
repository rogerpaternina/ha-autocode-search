# AutoCode Search

![Tests](https://github.com/rogerpaternina/ha-autocode-search/actions/workflows/tests.yml/badge.svg)

![Quality](https://github.com/rogerpaternina/ha-autocode-search/actions/workflows/quality.yml/badge.svg)

![Hassfest](https://github.com/rogerpaternina/ha-autocode-search/actions/workflows/hassfest.yml/badge.svg)

Integración personalizada para Home Assistant que, en una versión futura,
permitirá buscar códigos infrarrojos para dispositivos.

> El motor de búsqueda de códigos IR todavía no está implementado.

## Instalación con HACS

1. En HACS, abre **Integraciones** y selecciona el menú de tres puntos.
2. Añade este repositorio como repositorio personalizado de tipo
   **Integración**.
3. Busca e instala **Autocode Search**.
4. Reinicia Home Assistant.
5. Ve a **Ajustes > Dispositivos y servicios > Añadir integración** y busca
   **Autocode Search**.

La integración se configura exclusivamente desde la interfaz de Home
Assistant; no admite configuración YAML.

## Adaptador para entidades `remote`

`HomeAssistantRemoteAdapter` puede utilizar cualquier entidad `remote.*` que
implemente la acción estándar `remote.send_command`, con independencia del
hardware que la respalde. Recibe la instancia `hass` y el `entity_id`; al enviar
un código llama a esa acción con dicho identificador.

El Config Flow todavía no selecciona una entidad `remote`, por lo que el
adaptador no se crea automáticamente aún. Para comprobar la comunicación con
hardware real, instala esta integración, configura tu entidad `remote.*` y, en
**Herramientas para desarrolladores > Acciones**, ejecuta `remote.send_command`
con el `entity_id` de la entidad y un `command` válido. El adaptador usa esa
misma llamada; la conexión del Config Flow al motor se incorporará después.

## Desarrollo

La integración vive en `custom_components/autocode_search`. Su estructura ya
incluye un coordinador y los puntos de extensión para futuras entidades.

## Licencia

Este proyecto se distribuye bajo la [licencia MIT](LICENSE).
