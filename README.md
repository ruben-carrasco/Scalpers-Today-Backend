# ScalperToday Backend

Backend profesional para calendario económico con análisis de IA institucional, sistema de alertas y notificaciones push.

## 🚀 Inicio Rápido

```bash
cd proyecto
python -m pip install -r requirements.txt
cp .env.example .env
python -m scalper_today
```

- **Servidor:** `http://127.0.0.1:8000`
- **Documentación Interactiva:** `http://127.0.0.1:8000/docs`

## 📚 Documentación

- [API Reference](docs/API_REFERENCE.md) - Referencia completa de endpoints.
- [Documentación Proyecto DAM](docs/DOCUMENTACION_PROYECTO_DAM.md) - Documentación académica detallada.

## 🏛️ Arquitectura Senior (Clean Architecture)

El proyecto sigue una estructura de **Organización por Dominios** con regla de dependencia estricta y **una sola clase por archivo** para máxima mantenibilidad.

```
src/scalper_today/
├── api/                    # Capa de Entrada (Controllers)
│   ├── schemas/           # Pydantic (auth/, events/, alerts/, home/, shared/)
│   ├── exception_handlers.py # Manejo global de errores
│   └── dependencies/      # Inyección de dependencias (Container)
├── domain/                 # El corazón del sistema (Lógica Pura)
│   ├── entities/          # Dataclasses (auth/, events/, alerts/, home/)
│   ├── usecases/          # Lógica agrupada (auth/, events/, alerts/, home/, briefing/)
│   ├── dtos/              # Requests/Results (auth/, events/, alerts/, notifications/)
│   └── interfaces/        # Contratos (repositories/, services/)
└── infrastructure/         # Capa de Salida (Detalles técnicos)
    ├── database/          # SQLAlchemy + Migraciones Alembic
    ├── ai/                # OpenRouter (Gemini 2.5 Flash)
    └── notifications/     # Expo Push Service
```

## ✨ Características Principales

- **Clean Architecture & SOLID**: Código modular, desacoplado y altamente testable.
- **Tipado Estricto**: Eliminación total de diccionarios genéricos en favor de esquemas Pydantic.
- **Analisis IA Institucional**: Integración con OpenRouter (Gemini) para análisis rápido y profundo.
- **Suite de Pruebas (29 tests)**: Cobertura completa con Pytest (Unit e Integración).
- **Gestión de BD con Alembic**: Migraciones seguras para evolucionar el esquema SQLite.
- **Notificaciones Inteligentes**: Sistema de alertas con condiciones combinables y envío vía Expo.
- **Swagger Premium**: Documentación enriquecida con ejemplos, seguridad JWT y tags organizados.

## 🧪 Calidad y Pruebas

El proyecto incluye una red de seguridad profesional:

```bash
# Ejecutar toda la suite de pruebas
python -m pytest tests -v

# Linter y Formatter automático
python -m ruff check --fix .
python -m ruff format .
```

## 🔐 Configuración

Variables de entorno requeridas (`.env`):

```env
OPENROUTER_API_KEY=sk-or-v1-...
JWT_SECRET_KEY=tu_secreto_para_jwt
REFRESH_API_KEY=clave_para_forzar_refresh
APP_ENV=production
```

## ☁️ Despliegue

- **Producción**: `https://scalpertoday-ruben.azurewebsites.net`
- **CI/CD**: GitHub Actions para despliegue automático a Azure App Service.
- **Automation**: Job programado cada 30 min para refrescar el calendario económico.

## ⚖️ Licencia

MIT - Rubén Carrasco Frías
