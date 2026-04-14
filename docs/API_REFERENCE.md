# API Reference

Referencia técnica de la API HTTP del backend `ScalperToday`.

Base path común:

```text
/api/v1
```

## Seguridad

### JWT Bearer

Rutas protegidas por JWT:

- `GET /auth/me`
- `/alerts/*`

Cabecera:

```http
Authorization: Bearer <token>
```

### API key

Ruta protegida por API key:

- `POST /macro/refresh`

Cabecera:

```http
X-API-Key: <refresh_api_key>
```

## Authentication

### `POST /auth/register`

Crea una cuenta nueva y devuelve usuario + token.

Campos principales:

- `email`
- `password`
- `name`
- `language`
- `currency`
- `timezone`

Respuestas:

- `201` usuario creado
- `400` entrada inválida
- `409` email ya existente

### `POST /auth/login`

Autentica por email y contraseña.

Respuestas:

- `200` login correcto
- `401` credenciales inválidas
- `403` cuenta deshabilitada

### `GET /auth/me`

Devuelve el perfil autenticado.

Respuestas:

- `200` perfil actual
- `401` token inválido o expirado

## Events

### `GET /macro`

Devuelve los eventos económicos normalizados de hoy.

Comportamiento:

- intenta resolver eventos del día actual;
- si no hay datos disponibles en provider ni en caché local, devuelve `503`.

Respuestas:

- `200` lista de `EventResponse`
- `503` proveedor/caché sin datos

### `POST /macro/refresh`

Fuerza refresh desde el provider externo y actualiza la caché/persistencia del día.

Protección:

- requiere `X-API-Key`
- tiene rate limiting anti abuso

Respuestas:

- `200` refresh realizado
- `403` API key inválida o ausente
- `429` demasiadas peticiones

### `GET /brief`

Devuelve el briefing diario generado a partir de eventos y análisis IA.

## Mobile - Home

### `GET /home/summary`

Endpoint principal de la home móvil.

Incluye:

- saludo y fecha/hora formateadas
- estadísticas del día
- próximo evento
- sentimiento de mercado
- highlights

## Mobile - Events

### `GET /events/filtered`

Filtrado y paginación de eventos.

Query params:

- `importance` = `1..3`
- `country`
- `has_data`
- `search`
- `offset`
- `limit`

Respuesta:

- `total`
- `filters_applied`
- `events`

### `GET /events/by-importance/{importance}`

Devuelve eventos por importancia.

Respuestas:

- `200` lista filtrada
- `400` importancia inválida

### `GET /events/upcoming`

Devuelve próximos eventos a partir del conjunto del día.

Query params:

- `limit` entre `1` y `20`

### `GET /config/countries`

Devuelve países disponibles para filtros en móvil.

## Alerts

Todas las rutas de este bloque requieren JWT.

### `POST /alerts/`

Crea una alerta del usuario autenticado.

Campos principales:

- `name`
- `description`
- `conditions`
- `push_enabled`

Notas:

- `status` de alerta y `push_enabled` son independientes;
- una alerta puede seguir activa aunque el push esté desactivado.

### `GET /alerts/`

Lista alertas del usuario.

Query params:

- `include_deleted`

### `GET /alerts/{alert_id}`

Obtiene una alerta concreta.

Respuestas:

- `200`
- `404` no encontrada
- `403` sin permisos

### `PUT /alerts/{alert_id}`

Actualiza una alerta existente.

Campos opcionales:

- `name`
- `description`
- `conditions`
- `status`
- `push_enabled`

### `DELETE /alerts/{alert_id}`

Elimina una alerta.

Query params:

- `hard_delete`

Por defecto el borrado es lógico.

### `POST /alerts/device-token`

Registra un token Expo del dispositivo autenticado.

Campos:

- `token`
- `device_type`
- `device_name`

### `GET /alerts/device-tokens`

Lista tokens del usuario.

Query params:

- `active_only`

## System

### `GET /health`

Health check general.

Incluye:

- estado del servicio
- versión
- entorno
- chequeos de base de datos y configuración IA

### `GET /health/live`

Liveness probe simple.

### `GET /health/ready`

Readiness probe.

Puede devolver `503` si la aplicación no está lista.

## Errores y comportamiento relevante

- `401`: autenticación inválida o expirada
- `403`: acceso no autorizado o API key incorrecta
- `404`: recurso inexistente
- `409`: conflicto de registro
- `429`: rate limit
- `503`: dependencia temporalmente no disponible

## Contratos recomendados

Para payloads exactos y ejemplos actualizados, la fuente de verdad es OpenAPI:

- `/docs`
- `/redoc`
