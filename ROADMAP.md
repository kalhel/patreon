# 🗺️ Roadmap - Patreon Scraper

**Última actualización**: 2025-11-07
**Estado**: Planificación de mejoras y nuevas funcionalidades

> **📐 Nota importante**: Este roadmap describe las funcionalidades y mejoras planeadas. Para ver cómo todos estos componentes se integran en una **arquitectura técnica coherente y escalable**, consulta el documento [**ARCHITECTURE.md**](docs/ARCHITECTURE.md), que incluye diseño del sistema, stack tecnológico, plan de migración por fases y diagramas detallados.

---

## 📋 Índice

1. [Optimización de Scraping](#1-optimización-de-scraping)
2. [Mejoras en Almacenamiento](#2-mejoras-en-almacenamiento)
3. [Búsqueda y Transcripciones](#3-búsqueda-y-transcripciones)
4. [Rendimiento Web](#4-rendimiento-web)
5. [Sistema de Usuarios y Autenticación](#5-sistema-de-usuarios-y-autenticación)
6. [Panel de Administración](#6-panel-de-administración)
7. [Despliegue y Containerización](#7-despliegue-y-containerización)
8. [Extensión a Otras Fuentes](#8-extensión-a-otras-fuentes)
9. [Calidad del Código](#9-calidad-del-código)
10. [Funcionalidades de Usuario](#10-funcionalidades-de-usuario)
11. [Optimización de Almacenamiento](#11-optimización-de-almacenamiento)

---

## 1. 🔄 Optimización de Scraping

### 1.1 Fase 2: Optimización de Descarga de Imágenes

**Problema actual:**
- En `data/media/images/` hay muchas imágenes repetidas
- Posible causa: Re-escaneo de posts descarga la misma imagen con otro nombre
- Se descargan imágenes innecesarias (ej: avatares de creadores)

**Mejoras propuestas:**

- [ ] **Detección de duplicados**
  - Implementar hash de imágenes (MD5/SHA256) antes de guardar
  - Comparar hash con imágenes existentes
  - Si existe, crear link simbólico o referencia en lugar de duplicar

- [ ] **Filtrado inteligente de imágenes**
  - Detectar y excluir avatares de creadores
  - Implementar lista de exclusión por patrón de URL
  - Clasificar imágenes por tipo (contenido vs. metadata)

- [ ] **Gestión de re-escaneo**
  - Mantener base de datos de imágenes descargadas por post_id
  - Verificar existencia antes de descargar
  - Actualizar referencias sin re-descargar

**Impacto esperado:**
- 📉 Reducción del 50-70% en espacio de almacenamiento
- ⚡ Scraping más rápido al evitar descargas innecesarias
- 🔧 Facilita mantenimiento de la carpeta media

---

### 1.2 Fase 2: Mejora en Descarga de Videos de YouTube

**Problema actual:**
- A veces no se descargan ambos subtítulos (español e inglés)
- YouTube puede devolver errores por exceso de peticiones
- No hay sistema de reintentos o cola de procesamiento

**Mejoras propuestas:**

- [ ] **Sistema de colas para videos**
  - Implementar cola persistente (Redis, RabbitMQ, o SQLite simple)
  - Encolar videos fallidos para procesamiento posterior
  - Priorizar según antigüedad del post

- [ ] **Gestión de errores de YouTube**
  - Detectar error de rate limiting específicamente
  - Implementar backoff exponencial (1min, 5min, 15min, 1h)
  - Registrar intentos y timestamp del último intento

- [ ] **Descarga robusta de subtítulos**
  - Intentar descargar español primero, luego inglés
  - Si falla uno, no cancelar el otro
  - Registrar idiomas disponibles vs. descargados
  - Opción de re-intentar solo subtítulos faltantes

- [ ] **Monitoreo y estadísticas**
  - Dashboard de estado de cola de videos
  - Reportes de videos pendientes/fallidos
  - Alertas cuando la cola crece demasiado

**Impacto esperado:**
- ✅ 100% de videos con subtítulos cuando estén disponibles
- 🔄 Sistema resiliente ante errores temporales
- 📊 Visibilidad del estado de procesamiento

---

### 1.3 Automatización del Proceso de Escaneo Diario

**Problema actual:**
- Proceso manual para detectar nuevos creadores, posts, o collections
- Falta de herramientas visuales para monitoreo
- Scripts separados sin integración

**Mejoras propuestas:**

- [ ] **Dashboard de monitoreo**
  - Interfaz web para ver estado de escaneos
  - Gráficos de posts nuevos por día/semana
  - Alertas cuando hay nuevos creadores detectados
  - Timeline de actividad por creador

- [ ] **Detección automática de nuevos elementos**
  - Script que busca nuevos creadores en páginas seguidas
  - Detección automática de nuevas collections
  - Comparación con datos existentes para identificar posts nuevos
  - Notificaciones (email, Telegram, Discord) cuando hay novedades

- [ ] **Orquestación de scripts mejorada**
  - Script maestro que coordina fase 1, 2 y 3
  - Manejo inteligente de dependencias entre fases
  - Paralelización cuando sea posible
  - Logs centralizados y estructurados

- [ ] **Configuración de horarios personalizados**
  - UI para configurar cuándo escanear cada creador
  - Diferentes frecuencias según actividad del creador
  - Modo "burst" para creadores muy activos

**Impacto esperado:**
- 🤖 Automatización completa del proceso
- 👁️ Visibilidad en tiempo real
- ⚡ Respuesta rápida a nuevo contenido

---

## 2. 💾 Mejoras en Almacenamiento

### 2.1 Evaluación: JSON vs. Base de Datos

**Consideraciones actuales:**
- JSONs han fallado ocasionalmente (corrupción)
- Búsquedas pueden ser lentas con mucho contenido
- Escalabilidad limitada

**Opciones a evaluar:**

- [ ] **SQLite**
  - ✅ Pros: Simple, sin servidor, portable, rápido para reads
  - ❌ Cons: Limitaciones en concurrencia de writes
  - 💡 Uso recomendado: Datos estructurados, búsquedas frecuentes

- [ ] **PostgreSQL**
  - ✅ Pros: Robusto, soporte completo, excelente para búsqueda full-text
  - ❌ Cons: Requiere servidor, más complejo
  - 💡 Uso recomendado: Si se escala mucho o multi-usuario

- [ ] **Bases de datos vectoriales para búsqueda semántica**

  **Pinecone**
  - ✅ Pros: Managed service, muy rápido, escalable
  - ❌ Cons: Costo (no gratuito a escala)
  - 💡 Uso: Búsqueda semántica de contenido

  **Qdrant**
  - ✅ Pros: Open source, self-hosted, muy completo
  - ❌ Cons: Requiere setup de servidor
  - 💡 Uso: Búsqueda vectorial local

  **ChromaDB**
  - ✅ Pros: Simple, embeddable, perfecto para proyectos pequeños
  - ❌ Cons: Menos features que Qdrant/Pinecone
  - 💡 Uso: Prototipado rápido de búsqueda semántica

**Plan de migración:**

- [ ] Fase 1: Mantener JSONs como backup
- [ ] Fase 2: Implementar SQLite para datos estructurados
- [ ] Fase 3: Evaluar ChromaDB para búsqueda semántica
- [ ] Fase 4: Si funciona bien, considerar Qdrant para producción

**Impacto esperado:**
- 🚀 Búsquedas 10-100x más rápidas
- 💪 Mayor robustez ante fallos
- 🔍 Búsqueda semántica ("encuentra posts sobre astrología natal")

---

## 3. 🎙️ Búsqueda y Transcripciones

### 3.1 Transcripción de Audios

**Objetivo:**
Transcribir automáticamente archivos de audio para permitir búsqueda en contenido hablado

**Herramientas a evaluar:**

- [ ] **Whisper (OpenAI)**
  - ✅ Pros: Gratis, local, muy preciso, multiidioma
  - ❌ Cons: Requiere GPU para velocidad (o muy lento en CPU)
  - 💡 Mejor opción para transcripción offline de calidad

- [ ] **Vosk**
  - ✅ Pros: Gratuito, offline, modelos ligeros
  - ❌ Cons: Menos preciso que Whisper
  - 💡 Opción para transcripción rápida y básica

- [ ] **Google Speech-to-Text API**
  - ✅ Pros: Muy preciso, rápido
  - ❌ Cons: No gratuito (60min gratis/mes)
  - 💡 Opción si hay presupuesto

**Implementación propuesta:**

- [ ] Pipeline de transcripción
  - Detectar archivos de audio nuevos
  - Encolar para transcripción
  - Procesar con Whisper (modelo medium o large)
  - Guardar transcripciones en formato VTT/SRT
  - Indexar texto en base de datos de búsqueda

- [ ] Integración con búsqueda
  - Añadir campo "audio_transcript" a posts
  - Incluir en índice de búsqueda full-text
  - Mostrar fragmentos relevantes en resultados
  - Enlace directo al timestamp del audio

**Impacto esperado:**
- 📝 Contenido de audio completamente buscable
- 🔍 Encontrar información en podcasts/conferencias
- ♿ Accesibilidad mejorada

---

## 4. ⚡ Rendimiento Web

### 4.1 Optimización de Velocidad

**Problemas actuales:**
- Previews de posts cargan lento
- Al hacer clic en un post, tarda en cargar
- Experiencia no fluida

**Mejoras propuestas:**

- [ ] **Optimización de imágenes**
  - Generar thumbnails automáticamente (150x150, 300x300, 600x600)
  - Servir tamaño apropiado según dispositivo
  - Lazy loading de imágenes
  - WebP en lugar de JPEG/PNG
  - CDN local o servicio como Cloudflare

- [ ] **Caché agresivo**
  - Redis para caché de queries frecuentes
  - Caché de resultados de búsqueda
  - Service Workers para PWA offline
  - Caché de contenido estático (CSS, JS, fuentes)

- [ ] **Optimización de carga de posts**
  - Paginación o scroll infinito en lugar de cargar todo
  - Cargar contenido bajo demanda (imágenes full-res solo al hacer clic)
  - Pre-cargar siguiente/anterior post
  - Comprimir respuestas JSON con gzip

- [ ] **Frontend optimizado**
  - Minificar CSS/JS
  - Code splitting (cargar solo lo necesario)
  - Usar un framework ligero (Alpine.js, Petite Vue) o vanilla JS
  - Eliminar dependencias pesadas innecesarias

- [ ] **Herramientas de análisis**
  - Google Lighthouse para auditoría
  - WebPageTest para métricas detalladas
  - Profiling con Chrome DevTools
  - Monitoreo de tiempos de respuesta

**Métricas objetivo:**
- ⚡ First Contentful Paint: < 1s
- ⚡ Time to Interactive: < 2s
- ⚡ Carga de post individual: < 500ms
- ⚡ Búsqueda: < 200ms

**Impacto esperado:**
- 🚀 Experiencia 5-10x más rápida
- 📱 Mejor experiencia en móviles
- 😊 Mayor satisfacción de usuario

---

## 5. 🔐 Sistema de Usuarios y Autenticación

### 5.1 Gestión de Usuarios

**Objetivo:**
Implementar sistema multi-usuario con autenticación segura

**Funcionalidades:**

- [ ] **Administración de usuarios**
  - Panel de admin para crear/editar/eliminar usuarios
  - Roles: Admin, Usuario estándar, Usuario de solo lectura
  - Gestión de permisos granulares

- [ ] **Autenticación segura**
  - Sistema de login con hashing de contraseñas (bcrypt/argon2)
  - Sesiones seguras con tokens JWT
  - Opción de "recordarme" con tokens de larga duración
  - Logout en todos los dispositivos

- [ ] **Autenticación de dos factores (2FA)**
  - TOTP (Google Authenticator, Authy)
  - Códigos de backup
  - Opcional pero recomendado para admin

- [ ] **Recuperación de contraseña**
  - Reset por email (si está configurado)
  - Preguntas de seguridad
  - Códigos de recuperación de un solo uso

**Tecnologías recomendadas:**

- [ ] **Flask-Login** - Gestión de sesiones
- [ ] **Flask-Security-Too** - Suite completa de seguridad
- [ ] **PyOTP** - Autenticación 2FA
- [ ] **PassLib** - Hashing de contraseñas

**Impacto esperado:**
- 🔒 Sistema seguro y protegido
- 👥 Soporte multi-usuario
- 🛡️ Protección contra accesos no autorizados

---

## 6. 👨‍💼 Panel de Administración

### 6.1 Funcionalidades de Admin

**Objetivo:**
Panel completo para gestionar todos los aspectos del sistema

**Secciones del panel:**

- [ ] **Dashboard principal**
  - Estadísticas generales (posts, creadores, media)
  - Actividad reciente
  - Estado de escaneos
  - Alertas y notificaciones

- [ ] **Gestión de creadores**
  - Añadir nuevos creadores
  - Editar información de creadores existentes
  - Ver estadísticas por creador
  - Activar/desactivar escaneo automático
  - Eliminar creador (con confirmación)

- [ ] **Gestión de usuarios**
  - Crear usuarios
  - Editar roles y permisos
  - Ver actividad de usuarios
  - Desactivar/activar cuentas
  - Reset de contraseñas

- [ ] **Monitoreo de escaneos**
  - Ver chequeos diarios y su estado
  - Logs de ejecución
  - Estadísticas de éxito/error
  - Re-ejecutar escaneos manualmente
  - Ver cola de procesamiento

- [ ] **Gestión de fuentes de datos**
  - Activar/desactivar scrapers específicos
  - Configurar parámetros de cada scraper
  - Ver estado de cada fuente
  - Estadísticas de contenido por fuente

**Impacto esperado:**
- 🎛️ Control total del sistema desde UI
- 📊 Visibilidad completa de operaciones
- ⚡ Gestión rápida sin necesidad de terminal

---

## 7. 🐳 Despliegue y Containerización

### 7.1 Dockerización

**Objetivo:**
Permitir despliegue fácil en cualquier entorno

**Componentes a dockerizar:**

- [ ] **Contenedor principal de aplicación**
  - Flask web server
  - Scripts de scraping
  - Dependencias Python

- [ ] **Contenedor de base de datos**
  - PostgreSQL (si se elige) o SQLite montado como volumen

- [ ] **Contenedor de caché**
  - Redis para caché y colas

- [ ] **Contenedor de búsqueda vectorial**
  - Qdrant o ChromaDB (si se implementa)

**Docker Compose:**

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:alpine

  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
```

**Tareas:**

- [ ] Crear Dockerfile optimizado
- [ ] Crear docker-compose.yml
- [ ] Scripts de backup de volúmenes
- [ ] Documentación de despliegue Docker
- [ ] Testing en entorno Docker

---

### 7.2 Despliegue en NAS Synology

**Objetivo:**
Ejecutar en Synology NAS con Docker

**Pasos:**

- [ ] Adaptar docker-compose para Synology
- [ ] Configurar volúmenes en almacenamiento NAS
- [ ] Setup de reverse proxy (si es necesario)
- [ ] Configurar backups automáticos
- [ ] Documentación específica para Synology

---

### 7.3 Despliegue en Servidor Externo

**Opciones:**

- [ ] **VPS (DigitalOcean, Linode, Hetzner)**
  - Más control, precio razonable
  - Requiere mantenimiento manual

- [ ] **Cloud Managed (Railway, Render, Fly.io)**
  - Deploy automático desde Git
  - Menos configuración
  - Puede ser más caro

- [ ] **Self-hosted en servidor propio**
  - Control total
  - Requiere gestión de seguridad y updates

**Tareas comunes:**

- [ ] SSL/TLS con Let's Encrypt
- [ ] Configuración de firewall
- [ ] Backups automáticos a S3/Backblaze
- [ ] Monitoreo con Uptime Robot / Healthchecks.io
- [ ] Logs centralizados

---

## 8. 📚 Extensión a Otras Fuentes

### 8.1 Soporte Multi-Fuente

**Objetivo:**
No limitarse solo a Patreon, incluir otras fuentes de contenido

**Fuentes propuestas:**

- [ ] **Libros (PDFs)**
  - Extracción de texto con PyPDF2 / pdfplumber
  - OCR para PDFs escaneados (Tesseract)
  - Indexación de contenido
  - Búsqueda dentro de libros

- [ ] **Libros (imágenes)**
  - OCR con Tesseract o EasyOCR
  - Procesamiento de lotes
  - Almacenamiento de páginas + texto extraído

- [ ] **Otras plataformas similares**
  - Gumroad
  - Ko-fi
  - Buy Me a Coffee
  - Substack
  - Medium (artículos salvados)

**Arquitectura modular:**

- [ ] Sistema de plugins/scrapers
  - Interfaz común para todos los scrapers
  - Cada fuente implementa su lógica específica
  - Configuración independiente por fuente

- [ ] Gestión desde admin
  - Ver fuentes disponibles
  - Activar/desactivar cada fuente
  - Configurar parámetros específicos
  - Ver estadísticas por fuente

- [ ] Integración en búsqueda y UI
  - Filtro por fuente en búsqueda
  - Iconos/etiquetas que identifiquen la fuente
  - Estadísticas agregadas por fuente

**Impacto esperado:**
- 📖 Sistema unificado de gestión de conocimiento
- 🔍 Búsqueda en TODO tu contenido desde un lugar
- 🧩 Extensible para nuevas fuentes fácilmente

---

## 9. 🧹 Calidad del Código

### 9.1 Validación y Depuración

**Objetivo:**
Código limpio, consistente y bien documentado

**Tareas:**

- [ ] **Auditoría de código**
  - Revisar todo el código existente
  - Identificar código duplicado
  - Refactorizar funciones muy largas
  - Eliminar código muerto

- [ ] **Documentación**
  - Docstrings en todas las funciones
  - Type hints (Python 3.10+)
  - Comentarios para lógica compleja
  - README actualizado
  - Documentación de API (si se crea)

- [ ] **Estándares de código**
  - PEP 8 compliance (black, flake8)
  - Imports organizados (isort)
  - Naming conventions consistentes
  - Estructura de proyecto estandarizada

- [ ] **Testing**
  - Tests unitarios (pytest)
  - Tests de integración
  - Coverage > 80%
  - CI/CD para ejecutar tests automáticamente

---

### 9.2 Optimización

**Tareas:**

- [ ] **Profiling**
  - Identificar bottlenecks con cProfile
  - Optimizar queries lentas
  - Mejorar algoritmos ineficientes

- [ ] **Gestión de memoria**
  - Evitar cargar archivos grandes completos en memoria
  - Streaming para archivos multimedia
  - Garbage collection explícito cuando sea necesario

- [ ] **Logging mejorado**
  - Niveles apropiados (DEBUG, INFO, WARNING, ERROR)
  - Rotación de logs
  - Logs estructurados (JSON) para análisis
  - Integración con herramientas de monitoreo

---

### 9.3 Trabajo con IA

**Objetivo:**
Facilitar colaboración futura con IA de forma ordenada

**Mejores prácticas:**

- [ ] **Estructura consistente**
  - Convenciones de nombres claras
  - Organización de archivos predecible
  - Patrones de diseño reconocibles

- [ ] **Documentación para IA**
  - README.md completo con overview del proyecto
  - ARCHITECTURE.md explicando diseño
  - CONTRIBUTING.md con guías de desarrollo
  - Comentarios en código que expliquen "por qué" no solo "qué"

- [ ] **Prompts y configuración**
  - Archivo .ai/prompts.md con prompts útiles
  - Configuración de herramientas IA (Cursor, Copilot)
  - Ejemplos de tareas comunes

**Impacto esperado:**
- 🤖 IA puede entender y modificar código más fácilmente
- 🚀 Desarrollo más rápido
- 🐛 Menos errores por malentendidos

---

## 10. 👤 Funcionalidades de Usuario

### 10.1 Configuración Personal

**Objetivo:**
Cada usuario puede personalizar su experiencia

**Funcionalidades:**

- [ ] **Perfil de usuario**
  - Cambiar contraseña
  - Subir imagen de perfil
  - Configurar preferencias de notificaciones
  - Elegir tema (oscuro/claro)
  - Idioma preferido

- [ ] **Listas personalizadas**
  - Crear listas tipo "Para leer", "Favoritos", "Archivo"
  - Asignar posts a listas
  - Listas privadas (solo visibles para el usuario)
  - Compartir listas (opcional)

- [ ] **Estados personalizados**
  - Sistema tipo Notion: No leído, En proceso, Finalizado
  - Estados personalizables (nombres editables)
  - Colores personalizados por estado
  - Filtros por estado en búsqueda

- [ ] **Notas personales**
  - Añadir notas privadas a posts
  - Notas a listas enteras
  - Editor de texto rico (Markdown)
  - Solo visible para el usuario que las creó
  - Búsqueda incluye notas personales

- [ ] **Marcadores y highlights**
  - Destacar fragmentos de texto
  - Añadir bookmarks a posiciones específicas
  - Exportar highlights y notas

**Modelo de datos:**

```python
user_post_data = {
    "user_id": "123",
    "post_id": "456",
    "lists": ["to-read", "favorites"],
    "status": "in-progress",
    "notes": "Información interesante sobre...",
    "highlights": [...],
    "created_at": "2025-11-07",
    "updated_at": "2025-11-07"
}
```

**Impacto esperado:**
- 📝 Experiencia personalizada por usuario
- 🗂️ Mejor organización personal
- 💡 Contexto adicional con notas

---

## 11. 💿 Optimización de Almacenamiento

### 11.1 Deduplicación de Archivos

**Problema:**
Archivos duplicados consumen espacio innecesariamente

**Soluciones en Linux:**

- [ ] **Herramientas de deduplicación**

  **fdupes**
  - Encuentra duplicados por hash
  - Puede eliminar o crear hardlinks
  - Simple y efectivo

  **rdfind**
  - Similar a fdupes
  - Puede reemplazar duplicados con hardlinks

  **jdupes**
  - Fork mejorado de fdupes
  - Más rápido y eficiente

- [ ] **Filesystems con deduplicación nativa**

  **Btrfs**
  - Deduplicación a nivel de filesystem
  - Compresión transparente
  - Snapshots

  **ZFS**
  - Deduplicación más robusta
  - Requiere mucha RAM
  - Mejor para NAS/servidores

**Implementación propuesta:**

- [ ] Script de deduplicación periódico
  - Escanear carpeta media/
  - Generar hash de cada archivo
  - Crear hardlinks para duplicados
  - Reporte de espacio ahorrado

- [ ] Integración en pipeline de descarga
  - Verificar hash antes de guardar
  - Si existe, crear referencia
  - Mantener base de datos de hashes

**Impacto esperado:**
- 💾 Ahorro de 30-60% de espacio en media
- 🚀 Búsquedas más rápidas (menos archivos)
- 🧹 Librería más limpia

---

## 🎯 Priorización

### Alta Prioridad (Corto Plazo - 1-3 meses)

1. ✅ Optimización de descarga de imágenes (deduplicación)
2. ✅ Sistema de usuarios y autenticación básica
3. ✅ Mejora de rendimiento web (caché, lazy loading)
4. ✅ Panel de administración básico
5. ✅ Migración a SQLite para datos estructurados

### Media Prioridad (Medio Plazo - 3-6 meses)

6. ⏳ Sistema de colas para videos de YouTube
7. ⏳ Transcripción de audios con Whisper
8. ⏳ Dashboard de monitoreo de escaneos
9. ⏳ Dockerización completa
10. ⏳ Funcionalidades de usuario (listas, notas, estados)

### Baja Prioridad (Largo Plazo - 6-12 meses)

11. 🔮 Búsqueda semántica con ChromaDB/Qdrant
12. 🔮 Extensión a otras fuentes (libros PDF, otras plataformas)
13. 🔮 Despliegue en servidor externo
14. 🔮 Sistema de plugins modular
15. 🔮 Testing completo y CI/CD

---

## 📊 Métricas de Éxito

### Rendimiento
- ⚡ Tiempo de carga de página < 1s
- ⚡ Búsqueda < 200ms
- ⚡ Escaneo incremental < 2min

### Almacenamiento
- 💾 Reducción de 50%+ en espacio de imágenes
- 💾 0% de archivos corruptos (vs. JSONs actuales)

### Confiabilidad
- ✅ 99% de videos con subtítulos completos
- ✅ 0 escaneos fallidos sin reintentos
- ✅ Uptime > 99.5%

### Usabilidad
- 👥 Soporte para 5+ usuarios concurrentes
- 🔐 0 brechas de seguridad
- 📱 Experiencia móvil fluida

---

## 📝 Notas Finales

Este roadmap es un documento vivo que se actualizará según:
- Feedback de uso real
- Nuevas necesidades descubiertas
- Cambios en prioridades
- Evolución de tecnologías disponibles

Para proponer cambios o nuevas funcionalidades, actualizar este documento y documentar la razón del cambio.

---

**Mantenido por**: Administradores del proyecto
**Próxima revisión**: Trimestral
