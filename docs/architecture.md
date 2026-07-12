# Arquitectura de AutoCode Search

## Envío de un paquete Broadlink nativo

Cuando el adaptador detecta que la entidad `remote` pertenece a la integración
Broadlink y recibe un paquete Base64 válido de Broadlink, selecciona
`BroadlinkRawStrategy`. La estrategia añade el prefijo oficial `b64:` antes de
usar la acción estándar de Home Assistant.

```text
+--------------+
| SearchEngine |
+--------------+
        |
        v
+--------+
| IRCode |
+--------+
        |
        v
+----------------------+
| BroadlinkRawStrategy |
+----------------------+
        |
        v
+---------------------+
| remote.send_command |
+---------------------+
        |
        v
+------------------+
| python-broadlink |
+------------------+
        |
        v
+-------------+
| send_data() |
+-------------+
```

Los comandos no identificados como paquetes Broadlink, incluidos los nombres de
comandos aprendidos, continúan por `GenericStrategy` y se envían sin cambios.
