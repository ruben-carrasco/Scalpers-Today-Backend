# PROYECTO DAM

## IES NERVIÓN
### Scalper Today API

**Rubén Carrasco, Curso 2024-2025**

---

# Índice

1. [Objetivos del EVS](#1-objetivos-del-evs)
   - 1.1. [Descripción general del sistema](#11-descripción-general-del-sistema)
   - 1.2. [Diagrama de contexto](#12-diagrama-de-contexto)
   - 1.3. [Estudio de la situación actual](#13-estudio-de-la-situación-actual)
   - 1.4. [Catálogo de requisitos](#14-catálogo-de-requisitos)
   - 1.5. [Alternativas a la solución](#15-alternativas-a-la-solución)
   - 1.6. [Alternativa seleccionada y justificación](#16-alternativa-seleccionada-y-justificación)
2. [Gestión del proyecto](#2-gestión-del-proyecto)
   - 2.1. [Backlog](#21-backlog)
   - 2.2. [Sprints](#22-sprints)
3. [Análisis de Sistemas de información (ASI)](#3-análisis-de-sistemas-de-información-asi)
   - 3.1. [Descripción general del entorno tecnológico del sistema](#31-descripción-general-del-entorno-tecnológico-del-sistema)
   - 3.2. [Catálogo de usuarios](#32-catálogo-de-usuarios)
   - 3.3. [Modelo de casos de uso](#33-modelo-de-casos-de-uso)
   - 3.4. [Especificación de casos de uso](#34-especificación-de-casos-de-uso)
   - 3.5. [Modelo de clases de análisis](#35-modelo-de-clases-de-análisis)
   - 3.6. [Interfaces de usuario (API)](#36-interfaces-de-usuario-api)
4. [Diseño de Sistemas de información (DSI)](#4-diseño-de-sistemas-de-información-dsi)
   - 4.1. [Diseño de la arquitectura del sistema](#41-diseño-de-la-arquitectura-del-sistema)
   - 4.2. [Modelo de las clases de diseño](#42-modelo-de-las-clases-de-diseño)
   - 4.3. [Modelo físico de datos](#43-modelo-físico-de-datos)
   - 4.4. [Diseño de la interfaz de la API](#44-diseño-de-la-interfaz-de-la-api)
   - 4.5. [Plan de migración y carga inicial de datos](#45-plan-de-migración-y-carga-inicial-de-datos)
   - 4.6. [Plan de pruebas](#46-plan-de-pruebas)

---

# 1. Objetivos del EVS

El objetivo de Scalper Today API es proporcionar una API REST para traders e inversores que ofrece información en tiempo real sobre eventos macroeconómicos del calendario económico, enriquecida con análisis de Inteligencia Artificial. El sistema permite a los usuarios recibir alertas personalizadas y tomar decisiones de trading más informadas.

## 1.1. Descripción general del sistema

El sistema consiste en una API REST desarrollada con FastAPI (Python) que proporciona servicios backend para una aplicación móvil de trading. El sistema se centra en tres funcionalidades principales:

1. **Calendario Macroeconómico**: Obtención y procesamiento de eventos económicos del día (tipos de interés, PIB, inflación, empleo, etc.) mediante web scraping de Investing.com.

2. **Análisis con Inteligencia Artificial**: Análisis automatizado de cada evento mediante IA generativa (Google Gemini 2.5 Flash vía OpenRouter), proporcionando:
   - Análisis rápido: Resumen, impacto y sentimiento
   - Análisis profundo: Contexto macroeconómico, niveles técnicos, estrategias de trading y activos impactados

3. **Sistema de Alertas y Notificaciones**: Permite a los usuarios crear alertas personalizadas basadas en condiciones específicas (importancia, país, divisa) y recibir notificaciones push en tiempo real mediante **Expo Push Service**.

El sistema permite a los usuarios registrarse, autenticarse mediante JWT, configurar sus preferencias (idioma, divisa, zona horaria) y gestionar dispositivos para notificaciones push.

## 1.2. Diagrama de contexto

```
                                    ┌─────────────────────────────────┐
                                    │        Scalper Today API        │
                                    │                                 │
                                    │  ┌───────────────────────────┐  │
         ┌──────────┐              │  │    FastAPI Application    │  │              ┌──────────────┐
         │  Usuario │◄────────────►│  │                           │  │◄────────────►│ Investing.com│
         │  (App)   │   REST API   │  │  - Eventos Económicos     │  │   Scraping   │  (Calendario │
         └──────────┘              │  │  - Análisis IA            │  │              │  Económico)  │
              │                    │  │  - Autenticación          │  │              └──────────────┘
              │                    │  │  - Alertas                │  │
              │                    │  └───────────────────────────┘  │              ┌──────────────┐
              │                    │                                 │◄────────────►│  OpenRouter  │
              │                    │  ┌───────────────────────────┐  │   API REST   │  (Gemini AI) │
              │                    │  │    SQLite Database        │  │              └──────────────┘
              │                    │  │  - Usuarios               │  │
              │                    │  │  - Eventos                │  │              ┌──────────────┐
              │                    │  │  - Alertas                │  │◄────────────►│     Expo     │
              │                    │  │  - Dispositivos           │  │   API REST   │    (Push)    │
              │                    │  └───────────────────────────┘  │              └──────────────┘
              │                    │                                 │
              │                    └─────────────────────────────────┘
              │                                    ▲
              │                                    │
              │         ┌──────────────────────────┘
              │         │
              ▼         ▼
         ┌─────────────────────┐
         │   GitHub Actions    │
         │   (Refresh Job)     │
         │   Cada 30 min       │
         └─────────────────────┘
```

## 1.3. Estudio de la situación actual

Actualmente existen varias aplicaciones de calendario económico para traders, pero presentan limitaciones significativas:

**Soluciones existentes:**
- **Investing.com App**: Proporciona el calendario económico pero sin análisis de IA ni alertas personalizadas avanzadas.
- **TradingView**: Ofrece calendario económico integrado pero limitado en análisis y sin capacidad de alertas por condiciones complejas.
- **Forex Factory**: Web tradicional sin aplicación móvil moderna ni análisis automatizado.

**Limitaciones de las soluciones actuales:**
- No integran análisis de IA generativa para interpretar eventos
- Las alertas son básicas (solo por importancia) sin combinación de condiciones
- No ofrecen estrategias de trading ni niveles técnicos automáticos
- Interfaces no optimizadas para traders de scalping/intradía

**Nuestra solución:**
Scalper Today API supera estas limitaciones ofreciendo:
- Análisis de IA en dos niveles (rápido y profundo)
- Sistema de alertas con condiciones combinables
- Briefing diario automatizado
- API optimizada para aplicaciones móviles
- Estrategia database-first para evitar rate limiting

## 1.4. Catálogo de requisitos

### 1.4.1. Requisitos funcionales

| Código | Descripción | Prioridad |
|--------|-------------|-----------|
| RF0 | Debe obtener eventos económicos del día desde Investing.com | 1 |
| RF1 | Debe almacenar eventos en base de datos para evitar scraping excesivo | 1 |
| RF2 | Debe generar análisis rápido con IA para todos los eventos | 1 |
| RF3 | Debe generar análisis profundo con IA para eventos de alto impacto | 1 |
| RF4 | Debe permitir registro de usuarios con email y contraseña | 1 |
| RF5 | Debe autenticar usuarios mediante JWT | 1 |
| RF6 | Debe permitir crear alertas con condiciones personalizadas | 2 |
| RF7 | Debe permitir gestionar dispositivos para notificaciones push | 2 |
| RF8 | Debe proporcionar briefing diario con resumen del mercado | 2 |
| RF9 | Debe permitir filtrar eventos por importancia, país y divisa | 2 |
| RF10 | Debe proporcionar endpoint de refresh protegido por API key | 2 |
| RF11 | Debe permitir actualizar y eliminar alertas | 3 |
| RF12 | Debe proporcionar health checks para monitoreo | 3 |

### 1.4.2. Requisitos de datos

| Código | Descripción | Prioridad |
|--------|-------------|-----------|
| RD0 | Deben guardarse los datos de perfil de cada usuario | 1 |
| RD1 | Deben guardarse los eventos económicos con sus análisis | 1 |
| RD2 | Deben guardarse las alertas y sus condiciones | 1 |
| RD3 | Deben guardarse los tokens de dispositivos para push | 2 |
| RD4 | Deben guardarse las preferencias del usuario (idioma, divisa, timezone) | 2 |

### 1.4.3. Requisitos de interfaz (API)

| Código | Descripción | Prioridad |
|--------|-------------|-----------|
| RI0 | Debe exponer endpoints RESTful con respuestas JSON | 1 |
| RI1 | Debe documentar la API automáticamente con OpenAPI/Swagger | 1 |
| RI2 | Debe retornar códigos HTTP apropiados (200, 201, 400, 401, 404, 500) | 1 |
| RI3 | Debe soportar CORS para clientes web y móviles | 2 |
| RI4 | Debe incluir paginación en listados extensos | 3 |

### 1.4.4. Requisitos no funcionales

| Código | Descripción | Prioridad |
|--------|-------------|-----------|
| RNF0 | Debe responder en menos de 5 segundos para endpoints sin IA | 1 |
| RNF1 | Debe ser desplegable en Azure App Service | 1 |
| RNF2 | Debe soportar operaciones asíncronas para mejor rendimiento | 1 |
| RNF3 | Debe hashear contraseñas con bcrypt | 1 |
| RNF4 | Debe validar tokens JWT en cada petición protegida | 1 |
| RNF5 | Debe manejar errores gracefully sin exponer información sensible | 2 |
| RNF6 | Debe poder escalar horizontalmente | 3 |

## 1.5. Alternativas a la solución

### 1.5.1. Alternativa I - Python FastAPI + SQLite

#### 1.5.1.1. Requisitos
- Python 3.11+
- SQLite como base de datos
- Azure App Service para despliegue

#### 1.5.1.2. Tecnologías implementadas
- **FastAPI**: Framework web moderno y rápido
- **SQLAlchemy**: ORM con soporte async
- **aiosqlite**: Driver SQLite asíncrono
- **Pydantic**: Validación de datos y settings
- **httpx**: Cliente HTTP asíncrono
- **BeautifulSoup4**: Parsing HTML para scraping
- **python-jose**: Manejo de JWT
- **passlib + bcrypt**: Hashing de contraseñas
- **OpenRouter API**: Integración con IA

#### 1.5.1.3. Estudio de riesgo

| Riesgo | Porcentaje | Prioridad |
|--------|------------|-----------|
| Rate limiting de Investing.com | 40% | 1 |
| Costos de API de IA | 30% | 1 |
| Limitaciones de SQLite en concurrencia | 20% | 2 |
| Cambios en estructura HTML de Investing.com | 25% | 2 |
| Cuota de Azure App Service gratuito | 35% | 2 |

### 1.5.2. Alternativa II - Node.js + PostgreSQL

#### 1.5.2.1. Requisitos
- Node.js 20+
- PostgreSQL como base de datos
- AWS Lambda para despliegue serverless

#### 1.5.2.2. Tecnologías implementadas
- **Express.js / Fastify**: Framework web
- **Prisma**: ORM
- **Puppeteer**: Scraping con navegador headless
- **jsonwebtoken**: Manejo de JWT
- **bcryptjs**: Hashing de contraseñas

#### 1.5.2.3. Estudio de riesgo

| Riesgo | Porcentaje | Prioridad |
|--------|------------|-----------|
| Complejidad de Puppeteer para scraping | 45% | 1 |
| Costos de PostgreSQL managed | 35% | 1 |
| Cold starts en Lambda | 30% | 2 |
| Tipado débil de JavaScript | 20% | 2 |

## 1.6. Alternativa seleccionada y justificación

He escogido la **Alternativa I (Python FastAPI + SQLite)** por las siguientes razones:

- **FastAPI** ofrece documentación automática OpenAPI, validación de tipos con Pydantic, y rendimiento excelente con async/await nativo
- **SQLite** es suficiente para el volumen de datos esperado y simplifica el despliegue (sin necesidad de servidor de BD externo)
- **Python** tiene mejor ecosistema para scraping (BeautifulSoup, requests) y procesamiento de datos
- **Azure App Service** ofrece tier gratuito F1 adecuado para desarrollo y pruebas
- La arquitectura async-first permite manejar múltiples peticiones simultáneas eficientemente
- El patrón database-first mitiga el riesgo de rate limiting al cachear eventos

La combinación de estas tecnologías permite un desarrollo rápido, despliegue simple y mantenimiento sencillo, ideal para un proyecto académico con posibilidad de escalar.

---

# 2. Gestión del proyecto

Para el desarrollo de este proyecto he decidido utilizar la metodología de desarrollo **Scrum** adaptada a un desarrollador individual.

## 2.1. Backlog

| Tema | ID | User Story |
|------|-----|------------|
| **Scraping** | SC0 | Como desarrollador, quiero obtener eventos del calendario económico de Investing.com para tener datos actualizados |
| | SC1 | Como desarrollador, quiero parsear correctamente la importancia (1-3 estrellas) para priorizar eventos |
| | SC2 | Como desarrollador, quiero extraer valores actual/previsto/anterior para mostrar al usuario |
| **Base de Datos** | DB0 | Como desarrollador, quiero almacenar eventos en SQLite para evitar scraping excesivo |
| | DB1 | Como desarrollador, quiero implementar estrategia database-first para reducir llamadas externas |
| | DB2 | Como desarrollador, quiero guardar análisis de IA junto a eventos para no regenerarlos |
| **IA** | IA0 | Como desarrollador, quiero integrar OpenRouter para análisis con Gemini |
| | IA1 | Como desarrollador, quiero generar análisis rápido (resumen, impacto, sentimiento) para todos los eventos |
| | IA2 | Como desarrollador, quiero generar análisis profundo (contexto macro, niveles técnicos, estrategias) para eventos importantes |
| | IA3 | Como desarrollador, quiero generar briefing diario automático del mercado |
| **Autenticación** | AU0 | Como usuario, quiero registrarme con email y contraseña |
| | AU1 | Como usuario, quiero iniciar sesión y recibir un token JWT |
| | AU2 | Como usuario, quiero ver mi perfil con mis datos |
| | AU3 | Como desarrollador, quiero validar contraseñas seguras (8+ chars, mayúscula, número, especial) |
| **Alertas** | AL0 | Como usuario, quiero crear alertas con condiciones personalizadas |
| | AL1 | Como usuario, quiero listar mis alertas activas |
| | AL2 | Como usuario, quiero actualizar o eliminar mis alertas |
| | AL3 | Como usuario, quiero registrar mis dispositivos para notificaciones push |
| **API** | AP0 | Como desarrollador, quiero endpoints RESTful documentados con Swagger |
| | AP1 | Como desarrollador, quiero endpoint /macro para obtener eventos del día |
| | AP2 | Como desarrollador, quiero endpoint /brief para obtener briefing diario |
| | AP3 | Como desarrollador, quiero endpoint /macro/refresh protegido para forzar actualización |
| | AP4 | Como desarrollador, quiero endpoints de health check para monitoreo |
| **Despliegue** | DE0 | Como desarrollador, quiero desplegar en Azure App Service |
| | DE1 | Como desarrollador, quiero GitHub Actions para CI/CD automático |
| | DE2 | Como desarrollador, quiero job programado cada 30 minutos para refrescar datos |

## 2.2. Sprints

### Sprint 1: Infraestructura Base
- **Fecha comienzo**: 15/01/2025
- **Fecha finalización**: 22/01/2025
- **Duración**: 7 días

**Tareas:**
- SC0 - Implementar scraper de Investing.com
- SC1, SC2 - Parseo de datos de eventos
- DB0 - Configurar SQLite con SQLAlchemy async
- DB1 - Implementar repositorio de eventos
- AP0 - Configurar FastAPI con OpenAPI

### Sprint 2: Inteligencia Artificial
- **Fecha comienzo**: 23/01/2025
- **Fecha finalización**: 30/01/2025
- **Duración**: 7 días

**Tareas:**
- IA0 - Integrar OpenRouter API
- IA1 - Implementar análisis rápido
- IA2 - Implementar análisis profundo
- IA3 - Implementar generación de briefing diario
- DB2 - Persistir análisis en base de datos

### Sprint 3: Autenticación y Usuarios
- **Fecha comienzo**: 31/01/2025
- **Fecha finalización**: 07/02/2025
- **Duración**: 7 días

**Tareas:**
- AU0 - Implementar registro de usuarios
- AU1 - Implementar login con JWT
- AU2 - Endpoint de perfil de usuario
- AU3 - Validación de contraseñas seguras

### Sprint 4: Sistema de Alertas
- **Fecha comienzo**: 08/02/2025
- **Fecha finalización**: 15/02/2025
- **Duración**: 7 días

**Tareas:**
- AL0 - CRUD de alertas
- AL1, AL2 - Listado y gestión de alertas
- AL3 - Registro de dispositivos FCM

### Sprint 5: Despliegue y CI/CD
- **Fecha comienzo**: 16/02/2025
- **Fecha finalización**: 23/02/2025
- **Duración**: 7 días

**Tareas:**
- DE0 - Configurar Azure App Service
- DE1 - GitHub Actions para deploy automático
- DE2 - Job programado de refresh
- AP3, AP4 - Endpoints de refresh y health check
- DB1 - Optimizar estrategia database-first

---

# 3. Análisis de Sistemas de información (ASI)

## 3.1. Descripción general del entorno tecnológico del sistema

Para realizar el análisis del sistema, utilizamos un framework web moderno de Python que nos permite desarrollar APIs REST de alto rendimiento. Esta tecnología es **FastAPI**.

El proyecto sigue una **arquitectura limpia (Clean Architecture)** con las siguientes capas:

```
src/scalper_today/
├── api/                    # Capa de Presentación (Controllers)
│   ├── app.py             # Factory de aplicación
│   ├── routes.py          # Endpoints de eventos y sistema
│   ├── auth_routes.py     # Endpoints de autenticación
│   ├── alert_routes.py    # Endpoints de alertas
│   ├── exception_handlers.py # Manejo global de errores
│   ├── schemas/           # Esquemas Pydantic agrupados por dominio
│   │   ├── auth/, events/, alerts/, home/, shared/
│   └── dependencies/      # Inyección de dependencias (Container)
├── domain/                 # Capa de Dominio (Lógica Pura)
│   ├── entities/          # Entidades (User, EconomicEvent, Alert...)
│   │   ├── auth/, events/, alerts/, home/
│   ├── usecases/          # Lógica de aplicación agrupada por dominio
│   │   ├── auth/, events/, alerts/, home/, briefing/
│   ├── dtos/              # Objetos de transferencia (Requests/Results)
│   │   ├── auth/, events/, alerts/, notifications/
│   ├── interfaces/        # Contratos (Repositories, Services)
│   └── exceptions/        # Excepciones personalizadas (atomizadas)
├── infrastructure/         # Capa de Infraestructura (Detalles técnicos)
│   ├── database/          # Implementación Repositorios & Alembic
│   ├── auth/              # Implementación JWT
│   ├── ai/                # Cliente OpenRouter (IA)
│   ├── scrapers/          # Scraper de Investing.com
│   └── notifications/     # Expo Push Service
└── config.py              # Configuración centralizada
```

En cuanto a base de datos, se utiliza **SQLite** con **SQLAlchemy** como ORM y **aiosqlite** para operaciones asíncronas.

## 3.2. Catálogo de usuarios

| Código | Nombre | Descripción |
|--------|--------|-------------|
| USUV1 | Usuario no registrado | Solo puede acceder a endpoints públicos: /macro, /brief, /health |
| USUV2 | Usuario registrado | Puede acceder a todos los endpoints, crear alertas, gestionar dispositivos |
| USUV3 | Sistema (GitHub Actions) | Accede al endpoint /macro/refresh con API key para actualización programada |

## 3.3. Modelo de casos de uso

```
                           ┌─────────────────────────────────────────────────────┐
                           │                    Sistema                          │
                           │                                                     │
    ┌──────────────┐       │  ┌─────────────────────┐                           │
    │   Usuario    │◄──────┼──┤ Obtener eventos     │                           │
    │ no registrado│       │  │ macroeconómicos     │                           │
    └──────────────┘       │  └─────────────────────┘                           │
           │               │  ┌─────────────────────┐                           │
           │        ◄──────┼──┤ Ver briefing diario │                           │
           │               │  └─────────────────────┘                           │
           │               │  ┌─────────────────────┐                           │
           │        ◄──────┼──┤ Filtrar eventos     │                           │
           │               │  └─────────────────────┘                           │
           │               │  ┌─────────────────────┐                           │
           │        ◄──────┼──┤ Registrarse         │                           │
           │               │  └─────────────────────┘                           │    ┌──────────────┐
           │               │  ┌─────────────────────┐                           │    │   Usuario    │
           └───────────────┼──┤ Iniciar sesión      │───────────────────────────┼───►│  registrado  │
                           │  └─────────────────────┘                           │    └──────────────┘
                           │  ┌─────────────────────┐                           │           │
                           │  │ Ver perfil          │◄──────────────────────────┼───────────┤
                           │  └─────────────────────┘                           │           │
                           │  ┌─────────────────────┐                           │           │
                           │  │ Crear alerta        │◄──────────────────────────┼───────────┤
                           │  └─────────────────────┘                           │           │
                           │  ┌─────────────────────┐                           │           │
                           │  │ Listar alertas      │◄──────────────────────────┼───────────┤
                           │  └─────────────────────┘                           │           │
                           │  ┌─────────────────────┐                           │           │
                           │  │ Actualizar alerta   │◄──────────────────────────┼───────────┤
                           │  └─────────────────────┘                           │           │
                           │  ┌─────────────────────┐                           │           │
                           │  │ Eliminar alerta     │◄──────────────────────────┼───────────┤
                           │  └─────────────────────┘                           │           │
                           │  ┌─────────────────────┐                           │           │
                           │  │ Registrar dispositivo│◄─────────────────────────┼───────────┘
                           │  └─────────────────────┘                           │
                           │  ┌─────────────────────┐      ┌──────────────┐     │
                           │  │ Forzar refresh      │◄─────┤GitHub Actions│     │
                           │  └─────────────────────┘      └──────────────┘     │
                           └─────────────────────────────────────────────────────┘
```

## 3.4. Especificación de casos de uso

### CU0 - Obtener eventos macroeconómicos

| Campo | Valor |
|-------|-------|
| **Versión** | 1.0 |
| **Actor principal** | USUV1 (usuario no registrado), USUV2 (usuario registrado) |
| **Descripción** | El sistema obtiene los eventos económicos del día con análisis de IA |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | Se retorna lista de eventos con análisis rápido y profundo |

**Secuencia normal:**

| Paso | Acción |
|------|--------|
| 1 | El usuario solicita GET /api/v1/macro |
| 2 | El sistema verifica si hay eventos en base de datos para hoy |
| 3 | Si hay eventos, se retornan directamente |
| 4 | Si no hay eventos, se ejecuta scraping de Investing.com |
| 5 | Los eventos se guardan en base de datos |
| 6 | Se genera análisis rápido con IA para todos los eventos |
| 7 | Se genera análisis profundo para eventos de alta importancia |
| 8 | Se retorna la lista de eventos con análisis |

**Extensiones:**

| Paso | Acción |
|------|--------|
| 4a | Si el scraping falla, se retorna lista vacía con log de error |
| 6a | Si la IA no está configurada, se omite el análisis |

**Frecuencia esperada:** 500/día

---

### CU1 - Registro de usuario

| Campo | Valor |
|-------|-------|
| **Versión** | 1.0 |
| **Actor principal** | USUV1 (usuario no registrado) |
| **Descripción** | El sistema registra un nuevo usuario |
| **Precondiciones** | El email no debe existir en el sistema |
| **Postcondiciones** | Se crea el usuario y se retorna token JWT |

**Secuencia normal:**

| Paso | Acción |
|------|--------|
| 1 | El usuario envía POST /auth/register con datos |
| 2 | El sistema valida formato de email |
| 3 | El sistema valida fortaleza de contraseña |
| 4 | El sistema verifica que el email no existe |
| 5 | Se hashea la contraseña con bcrypt |
| 6 | Se crea el usuario en base de datos |
| 7 | Se genera token JWT |
| 8 | Se retorna usuario + token |

**Extensiones:**

| Paso | Acción |
|------|--------|
| 2a | Si el email es inválido: HTTP 400 |
| 3a | Si la contraseña es débil: HTTP 400 |
| 4a | Si el email existe: HTTP 409 Conflict |

**Frecuencia esperada:** 20/día

---

### CU2 - Inicio de sesión

| Campo | Valor |
|-------|-------|
| **Versión** | 1.0 |
| **Actor principal** | USUV2 (usuario registrado) |
| **Descripción** | El sistema autentica al usuario |
| **Precondiciones** | El usuario debe existir y estar activo |
| **Postcondiciones** | Se retorna token JWT válido |

**Secuencia normal:**

| Paso | Acción |
|------|--------|
| 1 | El usuario envía POST /auth/login |
| 2 | El sistema busca usuario por email |
| 3 | Se verifica la contraseña con bcrypt |
| 4 | Se verifica que la cuenta esté activa |
| 5 | Se genera token JWT con claims del usuario |
| 6 | Se retorna token + datos del usuario |

**Extensiones:**

| Paso | Acción |
|------|--------|
| 2a | Si el usuario no existe: HTTP 401 |
| 3a | Si la contraseña es incorrecta: HTTP 401 |
| 4a | Si la cuenta está desactivada: HTTP 403 |

**Frecuencia esperada:** 100/día

---

### CU3 - Crear alerta

| Campo | Valor |
|-------|-------|
| **Versión** | 1.0 |
| **Actor principal** | USUV2 (usuario registrado) |
| **Descripción** | El sistema crea una alerta con condiciones |
| **Precondiciones** | Usuario autenticado con JWT válido |
| **Postcondiciones** | Se crea alerta asociada al usuario |

**Secuencia normal:**

| Paso | Acción |
|------|--------|
| 1 | El usuario envía POST /alerts/ con token |
| 2 | Se valida el token JWT |
| 3 | Se extraen las condiciones de la alerta |
| 4 | Se crea la entidad Alert con estado ACTIVE |
| 5 | Se persiste en base de datos |
| 6 | Se retorna la alerta creada |

**Extensiones:**

| Paso | Acción |
|------|--------|
| 2a | Si el token es inválido: HTTP 401 |
| 3a | Si no hay condiciones: HTTP 400 |

**Frecuencia esperada:** 50/día

---

### CU4 - Forzar refresh de eventos

| Campo | Valor |
|-------|-------|
| **Versión** | 1.0 |
| **Actor principal** | USUV3 (GitHub Actions) |
| **Descripción** | El sistema fuerza actualización de eventos |
| **Precondiciones** | API key válida en query param |
| **Postcondiciones** | Se actualizan eventos desde Investing.com |

**Secuencia normal:**

| Paso | Acción |
|------|--------|
| 1 | GitHub Actions llama POST /macro/refresh?api_key=XXX |
| 2 | Se valida la API key |
| 3 | Se ejecuta scraping con force_refresh=True |
| 4 | Se actualizan eventos en base de datos |
| 5 | Se regeneran análisis de IA |
| 6 | Se retorna confirmación con conteo |

**Extensiones:**

| Paso | Acción |
|------|--------|
| 2a | Si la API key es inválida: HTTP 403 |
| 3a | Si el scraping falla: HTTP 500 |

**Frecuencia esperada:** 32/día (cada 30 min de 6am-10pm)

## 3.5. Modelo de clases de análisis

```
┌─────────────────┐         ┌─────────────────┐
│     Usuario     │         │     Alerta      │
├─────────────────┤         ├─────────────────┤
│ id              │ 1     * │ id              │
│ email           ├─────────┤ user_id         │
│ password_hash   │         │ name            │
│ name            │         │ description     │
│ preferences     │         │ conditions[]    │
│ is_active       │         │ status          │
└─────────────────┘         │ push_enabled    │
        │                   └─────────────────┘
        │ 1
        │
        │ *
┌─────────────────┐
│ DeviceToken     │
├─────────────────┤
│ id              │
│ user_id         │
│ token           │
│ device_type     │
│ device_name     │
└─────────────────┘


┌─────────────────┐         ┌─────────────────┐
│ EconomicEvent   │         │   AIAnalysis    │
├─────────────────┤         ├─────────────────┤
│ id              │ 1     1 │ summary         │
│ time            ├─────────┤ impact          │
│ title           │         │ sentiment       │
│ country         │         │ macro_context   │
│ currency        │         │ technical_levels│
│ importance      │         │ strategies      │
│ actual          │         │ impacted_assets │
│ forecast        │         └─────────────────┘
│ previous        │
│ ai_analysis     │
└─────────────────┘
```

## 3.6. Interfaces de usuario (API)

Al ser una API REST, la interfaz de usuario es el contrato de endpoints. La documentación completa está disponible en `/docs` (Swagger UI) y `/redoc` (ReDoc).

### Endpoints principales:

**Base URL:** `https://scalpertoday-ruben.azurewebsites.net/api/v1`

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/macro` | Eventos del día con análisis | No |
| POST | `/macro/refresh` | Forzar actualización | API Key |
| GET | `/brief` | Briefing diario | No |
| GET | `/home/summary` | Resumen para home | No |
| GET | `/events/filtered` | Eventos filtrados | No |
| GET | `/health` | Health check | No |
| POST | `/auth/register` | Registro | No |
| POST | `/auth/login` | Login | No |
| GET | `/auth/me` | Mi perfil | JWT |
| POST | `/alerts/` | Crear alerta | JWT |
| GET | `/alerts/` | Listar alertas | JWT |
| PUT | `/alerts/{id}` | Actualizar alerta | JWT |
| DELETE | `/alerts/{id}` | Eliminar alerta | JWT |
| POST | `/alerts/device-token` | Registrar dispositivo | JWT |

---

# 4. Diseño de Sistemas de información (DSI)

## 4.1. Diseño de la arquitectura del sistema

### 4.1.1. Descripción general del entorno tecnológico

El sistema se despliega en **Azure App Service** (Plan F1 gratuito) con las siguientes características:

- **Runtime**: Python 3.11
- **WSGI Server**: Gunicorn con workers UVicorn (ASGI)
- **Base de datos**: SQLite embebida
- **CI/CD**: GitHub Actions
- **Scheduled Jobs**: GitHub Actions (cron cada 30 min)

### 4.1.2. Catálogo de requisitos de diseño

**Requisitos del modelo de datos:**

| Código | Descripción | Fecha |
|--------|-------------|-------|
| RD0 | El modelo utiliza SQLAlchemy con patrón Repository | 15/01/2025 |
| RD1 | El motor de base de datos es SQLite con aiosqlite | 15/01/2025 |
| RD2 | Las operaciones son asíncronas (async/await) | 15/01/2025 |
| RD3 | Los análisis de IA se almacenan como JSON | 20/01/2025 |

**Requisitos de la API:**

| Código | Descripción | Fecha |
|--------|-------------|-------|
| RA0 | Todos los endpoints retornan JSON | 15/01/2025 |
| RA1 | Se usa Pydantic para validación de request/response | 15/01/2025 |
| RA2 | Los errores siguen formato estándar {detail: string} | 15/01/2025 |
| RA3 | JWT usa algoritmo HS256 con expiración de 30 días | 01/02/2025 |

## 4.2. Modelo de las clases de diseño

### Entidades del Dominio

```python
@dataclass
class User:
    id: str                    # UUID
    email: str
    hashed_password: str
    name: Optional[str]
    avatar_url: Optional[str]
    preferences: UserPreferences
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class EconomicEvent:
    id: str
    time: str                  # "HH:MM"
    title: str
    country: str
    currency: str
    importance: int            # 1, 2, 3
    actual: Optional[str]
    forecast: Optional[str]
    previous: Optional[str]
    ai_analysis: Optional[AIAnalysis]
    _timestamp: datetime

@dataclass
class Alert:
    id: str                    # UUID
    user_id: str
    name: str
    description: Optional[str]
    conditions: List[AlertCondition]
    status: AlertStatus        # ACTIVE, PAUSED, DELETED
    push_enabled: bool
    trigger_count: int
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

@dataclass
class AlertCondition:
    alert_type: AlertType      # importance, currency, country
    value: Optional[str]

@dataclass
class DeviceToken:
    id: str
    user_id: str
    token: str
    device_type: str           # ios, android
    device_name: Optional[str]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]

@dataclass
class AIAnalysis:
    summary: str
    impact: str                # HIGH, MEDIUM, LOW
    sentiment: str             # BULLISH, BEARISH, NEUTRAL
    macro_context: Optional[str]
    technical_levels: Optional[str]
    trading_strategies: Optional[str]
    impacted_assets: Optional[str]
    is_deep_analysis: bool

@dataclass
class UserPreferences:
    language: str              # es, en
    currency: str              # usd, eur, gbp
    timezone: str              # Europe/Madrid, etc.
```

## 4.3. Modelo físico de datos

La aplicación utiliza SQLite con las siguientes tablas:

### Tabla: users

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | VARCHAR(36) | PRIMARY KEY |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| hashed_password | VARCHAR(255) | NOT NULL |
| name | VARCHAR(100) | NULL |
| avatar_url | VARCHAR(500) | NULL |
| preferences | JSON | DEFAULT '{}' |
| is_active | BOOLEAN | DEFAULT TRUE |
| is_verified | BOOLEAN | DEFAULT FALSE |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

### Tabla: economic_events

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | VARCHAR(100) | PRIMARY KEY |
| date | DATETIME | NOT NULL |
| time | VARCHAR(10) | NOT NULL |
| title | VARCHAR(500) | NOT NULL |
| country | VARCHAR(100) | |
| currency | VARCHAR(10) | |
| importance | INTEGER | DEFAULT 1 |
| actual | VARCHAR(50) | |
| forecast | VARCHAR(50) | |
| previous | VARCHAR(50) | |
| surprise | VARCHAR(20) | |
| analisis_rapido | JSON | |
| analisis_profundo | JSON | |
| has_quick_analysis | BOOLEAN | DEFAULT FALSE |
| has_deep_analysis | BOOLEAN | DEFAULT FALSE |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### Tabla: alerts

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | VARCHAR(36) | PRIMARY KEY |
| user_id | VARCHAR(36) | FOREIGN KEY → users.id |
| name | VARCHAR(100) | NOT NULL |
| description | VARCHAR(500) | |
| conditions | JSON | NOT NULL |
| status | VARCHAR(20) | DEFAULT 'ACTIVE' |
| push_enabled | BOOLEAN | DEFAULT TRUE |
| trigger_count | INTEGER | DEFAULT 0 |
| last_triggered_at | DATETIME | |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

### Tabla: device_tokens

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | VARCHAR(36) | PRIMARY KEY |
| user_id | VARCHAR(36) | FOREIGN KEY → users.id |
| token | VARCHAR(500) | UNIQUE, NOT NULL |
| device_type | VARCHAR(20) | NOT NULL |
| device_name | VARCHAR(100) | |
| is_active | BOOLEAN | DEFAULT TRUE |
| created_at | DATETIME | NOT NULL |
| last_used_at | DATETIME | |

## 4.4. Diseño de la interfaz de la API

### Request/Response Schemas (Pydantic)

**RegisterUserRequest:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "MiPassword123!",
  "name": "Juan García",
  "language": "es",
  "currency": "eur",
  "timezone": "Europe/Madrid"
}
```

**AuthResponse:**
```json
{
  "user": {
    "id": "uuid-xxx",
    "email": "usuario@ejemplo.com",
    "name": "Juan García",
    "preferences": {
      "language": "es",
      "currency": "eur",
      "timezone": "Europe/Madrid"
    }
  },
  "token": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 2592000
  }
}
```

**EconomicEvent Response:**
```json
{
  "id": "evt_001",
  "time": "14:30",
  "title": "Decisión de tipos de interés Fed",
  "country": "Estados Unidos",
  "currency": "USD",
  "importance": 3,
  "actual": "5.50%",
  "forecast": "5.50%",
  "previous": "5.25%",
  "surprise": "neutral",
  "ai_analysis": {
    "summary": "La Fed mantiene tipos, señal dovish...",
    "impact": "HIGH",
    "sentiment": "NEUTRAL",
    "macro_context": "En un contexto de inflación...",
    "technical_levels": "Soporte: 1.0800, Resistencia: 1.0950",
    "trading_strategies": "Buscar largos en correcciones...",
    "impacted_assets": "EUR/USD, Gold, US10Y"
  }
}
```

**CreateAlertRequest:**
```json
{
  "name": "Alertas EUR Alta Importancia",
  "description": "Eventos importantes para EUR",
  "conditions": [
    {"alert_type": "importance", "value": "3"},
    {"alert_type": "currency", "value": "EUR"}
  ],
  "push_enabled": true
}
```

## 4.5. Plan de migración y carga inicial de datos

El sistema utiliza **Alembic** para la gestión de migraciones de la base de datos, lo que permite evolucionar el esquema de SQLite de forma segura.

1. **Gestión de Versiones**: Se utiliza `alembic upgrade head` en el arranque del servidor (Azure `startup.sh`) para asegurar que todas las tablas existan y estén actualizadas.

2. **Carga inicial**: No requiere carga manual. El archivo SQLite se crea automáticamente si no existe.

3. **Datos de eventos**: Se obtienen dinámicamente de Investing.com mediante scraping y se cachean.

4. **Análisis de IA**: Se generan bajo demanda y se cachean para optimizar costes y rendimiento.

## 4.6. Plan de pruebas

Se ha implementado una suite de **29 pruebas automatizadas** utilizando el framework **Pytest**, cubriendo todas las capas de la Clean Architecture.

### 4.6.1. Resumen de Cobertura

- **Pruebas de API (Integración)**: Verifican los endpoints de autenticación, alertas, eventos y salud del sistema usando `FastAPI TestClient`.
- **Pruebas de Dominio (Unidad)**: Validan las reglas de negocio, el filtrado de eventos, los cálculos de importancia y la lógica del dashboard.
- **Pruebas de Infraestructura**: Mocks de respuestas de IA (OpenRouter) y simulación de HTML real para verificar el Scraper.

### 4.6.2. Ejecución de pruebas

```bash
# Ejecutar todas las pruebas con detalle
python -m pytest tests -v
```

### 4.6.3. Detalle de casos de prueba principales

| Código | Descripción | Capa | Resultado |
|--------|-------------|------|-----------|
| PR-AU | Registro, login y validación de JWT | API/Domain | PASSED |
| PR-AL | CRUD completo de alertas y tokens push | API | PASSED |
| PR-EV | Filtrado, obtención y mapeo de eventos | Domain | PASSED |
| PR-IA | Parseo de JSON de IA y lógica de mappers | Infra | PASSED |
| PR-SC | Scraping de Investing.com con HTML real | Infra | PASSED |
| PR-HC | Liveness y Readiness probes | API | PASSED |

---

# Anexos

## A. Variables de entorno requeridas

```env
# Requeridas
OPENROUTER_API_KEY=sk-xxx          # API key de OpenRouter
JWT_SECRET_KEY=xxx                  # Secreto para firmar JWT
REFRESH_API_KEY=xxx                 # API key para endpoint refresh

# Opcionales
APP_ENV=production                  # development, staging, production
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR
DATABASE_PATH=data/scalper_today.db
CORS_ORIGINS=https://miapp.com
```

## B. Comandos útiles

```bash
# Ejecutar localmente
cd src && python -m scalper_today

# Ejecutar con uvicorn
uvicorn scalper_today.api.app:app --reload

# Gestión de base de datos (Alembic)
alembic revision --autogenerate -m "Descripción"
alembic upgrade head

# Ejecutar tests
python -m pytest tests/ -v

# Ver documentación API
# http://localhost:8000/docs (Swagger)
# http://localhost:8000/redoc (ReDoc)
```

## C. URLs de producción

- **API Base**: `https://scalpertoday-ruben.azurewebsites.net/api/v1`
- **Swagger UI**: `https://scalpertoday-ruben.azurewebsites.net/docs`
- **ReDoc**: `https://scalpertoday-ruben.azurewebsites.net/redoc`
- **Health Check**: `https://scalpertoday-ruben.azurewebsites.net/api/v1/health`

---

*Documento generado para el Proyecto DAM - Scalper Today API*
*Rubén Carrasco, Curso 2024-2025*
