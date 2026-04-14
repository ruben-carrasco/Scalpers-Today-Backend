# ScalperToday Backend

Backend de `ScalperToday`, una API FastAPI orientada a calendario macroeconómico, briefing con IA, alertas personalizadas y notificaciones push para la app móvil.

Este repositorio está documentado con enfoque de desarrollador: arquitectura real, ejecución local, despliegue y decisiones técnicas relevantes para mantenimiento y memoria de TFG.

## Objetivo del backend

El backend centraliza cuatro responsabilidades:

- obtener y normalizar eventos macroeconómicos del día;
- enriquecer esos eventos con análisis generado por IA;
- exponer endpoints consumidos por la aplicación móvil;
- gestionar autenticación, alertas y tokens de dispositivos para push.

## Stack técnico

- Python `3.11`
- FastAPI
- SQLAlchemy `async` + SQLite
- Alembic para migraciones
- HTTPX para integraciones externas
- OpenRouter para análisis con LLM
- Expo Push Notifications para entrega de notificaciones
- Pytest y Ruff para calidad

Dependencias principales: [pyproject.toml](/Users/rubencarrascofrias/Documents/TFG/proyecto/pyproject.toml)

## Arquitectura real

El backend sigue una variante de Clean Architecture organizada por capas:

```text
src/scalper_today/
├── api/                  # Entrada HTTP: app, rutas, schemas, handlers
├── domain/               # Entidades, DTOs, interfaces y casos de uso
├── infrastructure/       # DB, provider externo, IA, notificaciones, auth
└── config.py             # Settings centralizados
```

### Capas

`api/`
- define rutas FastAPI, OpenAPI, seguridad y composición HTTP;
- no contiene lógica de negocio compleja;
- delega en el contenedor y en casos de uso.

`domain/`
- contiene entidades como `EconomicEvent`, `Alert`, `User`;
- define interfaces (`repositories`, `services`, `providers`);
- implementa casos de uso puros del sistema.

`infrastructure/`
- implementa detalles técnicos concretos;
- repositorios SQLAlchemy;
- provider del calendario económico;
- integración con OpenRouter;
- JWT y Expo Push.

### Inyección de dependencias

La composición principal se resuelve en [container.py](/Users/rubencarrascofrias/Documents/TFG/proyecto/src/scalper_today/api/dependencies/container.py).

Ahí se inicializan:

- `DatabaseManager`
- `httpx.AsyncClient`
- `ForexFactoryCalendarProvider`
- `OpenRouterAnalyzer`
- servicios de autenticación JWT
- repositorios y casos de uso

## Flujo principal de datos

### 1. Eventos macroeconómicos

1. `GET /api/v1/macro` llama a `get_macro_events()`.
2. El caso de uso consulta primero la base de datos para eventos de hoy.
3. Si no hay datos válidos, usa `ForexFactoryCalendarProvider`.
4. El provider descarga `ff_calendar_thisweek.json`, filtra por fecha actual en `Europe/Madrid` y normaliza a `EconomicEvent`.
5. El backend persiste eventos y expone el resultado a la app.

### 2. Briefing y análisis IA

1. A partir de los eventos de hoy se generan resúmenes y análisis.
2. El backend usa OpenRouter para producir `summary`, `macroContext`, `technicalLevels` y `tradingStrategies`.
3. La app móvil consume esos textos desde `home`, `brief` y detalle de evento.

### 3. Alertas y push

1. El usuario crea alertas autenticado por JWT.
2. El backend guarda condiciones, estado y `push_enabled`.
3. Los tokens Expo del dispositivo se registran en `/api/v1/alerts/device-token`.
4. El scheduler revisa eventos cercanos y dispara notificaciones cuando se cumplen condiciones.

## Fuente de datos actual

La fuente activa del calendario es `ForexFactory` a través del feed JSON semanal:

- variable: `FOREXFACTORY_CALENDAR_URL`
- valor por defecto: `https://nfs.faireconomy.media/ff_calendar_thisweek.json`

Importante:

- actualmente el backend usa un **provider JSON**, no scraping HTML;
- cada evento se normaliza al modelo interno `EconomicEvent`;
- el campo `url` no apunta a una ficha individual de ForexFactory, sino a la fuente del feed utilizada por el provider.

## Seguridad y protección

### JWT

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

El backend firma tokens con `JWT_SECRET_KEY` y valida el acceso en rutas protegidas como `/api/v1/alerts/*`.

### API key para refresh manual

`POST /api/v1/macro/refresh` requiere:

- cabecera `X-API-Key`
- coincidencia con `REFRESH_API_KEY`

### Rate limiting

Hay protecciones en memoria para:

- login/register por IP + email
- refresh forzado de eventos por IP + ruta

Estas protecciones son útiles para una sola instancia, pero no sustituyen un rate limiter distribuido si el sistema escalara horizontalmente.

## Variables de entorno

Archivo base: [.env.example](/Users/rubencarrascofrias/Documents/TFG/proyecto/.env.example)

### Obligatorias en práctica

- `OPENROUTER_API_KEY`
- `JWT_SECRET_KEY`
- `REFRESH_API_KEY`

### Importantes

- `FOREXFACTORY_CALENDAR_URL`
- `DATABASE_PATH`
- `APP_ENV`
- `APP_DEBUG`
- `CORS_ORIGINS`
- `NOTIFICATION_CHECK_INTERVAL`
- `NOTIFICATION_BEFORE_MINUTES`
- `JWT_TOKEN_EXPIRE_DAYS`

## Ejecución local

### 1. Instalar dependencias

```bash
cd proyecto
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 2. Configurar entorno

```bash
cp .env.example .env
```

Rellena al menos las claves necesarias.

### 3. Ejecutar migraciones

```bash
alembic upgrade head
```

### 4. Iniciar la API

```bash
uvicorn src.scalper_today.api.app:app --reload
```

Documentación interactiva:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Calidad y pruebas

### Lint

```bash
ruff check .
```

### Tests

```bash
pytest
```

## Despliegue

El backend está preparado para despliegue en Azure App Service.

Puntos relevantes del despliegue:

- base de datos SQLite en ruta persistente de Azure;
- configuración mediante Application Settings;
- GitHub Actions para build y deploy;
- validación en arranque de configuración crítica como JWT y provider.

Antes de desplegar, conviene revisar:

- variables de entorno presentes en Azure;
- ruta persistente de la base de datos;
- ejecución de migraciones en arranque;
- permisos y OIDC si el deploy usa `azure/login`.

## Limitaciones y decisiones técnicas

- SQLite simplifica el despliegue y el TFG, pero limita escalado concurrente.
- El rate limiting actual es en memoria y no distribuido.
- El calendario económico depende de una fuente externa gratuita y no contractual.
- El análisis IA depende de OpenRouter; sin clave, el sistema puede arrancar pero degradará funcionalidades de análisis.
- `push_enabled` y `status` de una alerta son conceptos distintos: una alerta puede seguir activa pero no enviar push.

## Documentación relacionada

- referencia de API: [API_REFERENCE.md](/Users/rubencarrascofrias/Documents/TFG/proyecto/docs/API_REFERENCE.md)
- memoria/proyecto DAM previa: [DOCUMENTACION_PROYECTO_DAM.md](/Users/rubencarrascofrias/Documents/TFG/proyecto/docs/DOCUMENTACION_PROYECTO_DAM.md)
