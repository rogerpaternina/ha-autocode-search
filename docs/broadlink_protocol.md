# Protocolo Broadlink en Home Assistant

## Conclusión

Para transmitir un código Broadlink arbitrario desde una entidad `remote` de la
integración Broadlink, se debe llamar al servicio estándar
`remote.send_command` con el paquete codificado en Base64 y el prefijo `b64:`.
No se debe proporcionar `device` para este caso.

```yaml
action: remote.send_command
target:
  entity_id: remote.living_room
data:
  command: "b64:JgAcAB0dHB44HhweGx4cHR06HB0cHhwdHB8bHhwADQUAAAAAAAAAAAAAAAA="
```

`Jg...` es el paquete binario nativo de Broadlink codificado con Base64; no es
un código Pronto, LIRC ni texto arbitrario. Cualquier formato externo debe
convertirse primero al formato de paquete que espera el dispositivo Broadlink
y después codificarse en Base64.

## Cómo procesa Home Assistant el comando

La implementación `BroadlinkRemote.async_send_command()` valida `command` como
una lista no vacía de cadenas. Por tanto, el servicio acepta una sola cadena o
una lista de cadenas. Para cada cadena, `_extract_codes()` sigue esta regla:

1. Si empieza por `b64:`, elimina ese prefijo y trata el resto como Base64.
2. Si no empieza por `b64:`, busca el nombre del comando aprendido en el
   almacenamiento usando `device` y `command`.
3. Decodifica el valor Base64 a `bytes` mediante `data_packet()`.
4. Envía esos bytes con `device.async_request(device.api.send_data, code)`.

El prefijo es obligatorio. Sin `b64:`, una cadena Base64 se interpreta como el
nombre de un comando aprendido y requiere `device`.

## Códigos aprendidos

`async_learn_command()` usa la API del dispositivo para entrar en modo de
aprendizaje y consultar el paquete capturado. El resultado binario se convierte
a Base64 antes de guardarse. Los comandos aprendidos se guardan en
`/config/.storage/broadlink_remote_<MAC>_codes`; Home Assistant advierte que
ese archivo no debe editarse manualmente.

Un paquete aprendido previamente puede reutilizarse directamente: basta con
anteponer `b64:` a su valor Base64. También pueden enviarse paquetes IR o RF;
el tipo se identifica por el propio paquete, aunque la entidad debe soportar
RF para poder transmitirlo.

## Biblioteca subyacente y API de bytes

La integración declara la dependencia `broadlink==0.19.0`, es decir,
python-broadlink. La llamada efectiva termina en `send_data(data: bytes)` de
esa biblioteca.

Dentro de Home Assistant se accede a ella como:

```python
await device.async_request(device.api.send_data, packet_bytes)
```

`device.api` y `device.async_request` pertenecen a la implementación interna
de la integración Broadlink; no son un contrato público para otras
integraciones. Aunque `send_data(bytes)` existe en python-broadlink, usarlo a
través de esos objetos internos acoplaría AutoCode Search a detalles privados,
autenticación, reintentos y cambios de Home Assistant.

## Integración correcta para AutoCode Search

La arquitectura debe continuar usando `IRAdapter` y el servicio estándar de
Home Assistant. Cuando un proveedor entregue un paquete Broadlink Base64, el
adaptador de remote deberá enviar:

```python
await hass.services.async_call(
    "remote",
    "send_command",
    {
        "entity_id": entity_id,
        "command": f"b64:{base64_packet}",
    },
    blocking=True,
)
```

No debe enviar `device` ni `command` con un nombre de botón para este flujo.
Esto mantiene el motor independiente de Broadlink y permite que el adaptador
trate explícitamente los formatos de cada entidad remote en una futura mejora.

## Respuestas a la investigación

| Pregunta | Respuesta |
| --- | --- |
| ¿Formato directo soportado? | Sí: `b64:<paquete Base64>`. |
| ¿Qué espera `command`? | Una cadena o lista de cadenas; nombres de comandos aprendidos o valores Base64 prefijados con `b64:`. |
| ¿Se puede usar Base64 aprendido previamente? | Sí, añadiendo `b64:` y omitiendo `device`. |
| ¿Usa python-broadlink? | Sí, Home Assistant declara `broadlink==0.19.0`. |
| ¿Hay API de bytes? | Sí, `send_data(bytes)` en python-broadlink; Home Assistant la llama internamente mediante `device.api.send_data`. No se debe usar esa ruta privada desde AutoCode Search. |

## Fuentes

- [Código actual de `remote.py` de Broadlink](https://github.com/home-assistant/core/blob/dev/homeassistant/components/broadlink/remote.py)
- [Helper `data_packet()`](https://github.com/home-assistant/core/blob/dev/homeassistant/components/broadlink/helpers.py)
- [Manifest y dependencia de Broadlink](https://github.com/home-assistant/core/blob/dev/homeassistant/components/broadlink/manifest.json)
- [Documentación de la integración Broadlink](https://www.home-assistant.io/integrations/broadlink/)
