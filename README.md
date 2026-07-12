# Autocode Search

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

## Desarrollo

La integración vive en `custom_components/autocode_search`. Su estructura ya
incluye un coordinador y los puntos de extensión para futuras entidades.

## Licencia

Este proyecto se distribuye bajo la [licencia MIT](LICENSE).

