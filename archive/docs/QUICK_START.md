# 🚀 Quick Start Guide - Patreon to Notion

**Fecha**: 2025-11-01
**Estado**: En desarrollo - Fase 1

---

## ⚡ Instalación Rápida

### 1. Instalar Dependencias

```bash
cd /home/javif/proyectos/astrologia/patreon

# Instalar requirements
pip install -r requirements.txt

# Instalar ChromeDriver (para Selenium)
pip install webdriver-manager
```

### 2. Configurar Credenciales

El archivo `config/credentials.json` ya está configurado con:
- ✅ Email de Patreon
- ✅ Password de Patreon
- ✅ URLs de los 3 creadores

---

## 🔐 Paso 1: Autenticación con Patreon

### Opción A: Modo Manual (Recomendado)

```bash
python3 src/patreon_auth_selenium.py
```

**Qué hará**:
1. Abre Chrome
2. Va a Patreon login
3. **TÚ** haces login manualmente
4. Presionas ENTER cuando estés logueado
5. Guarda las cookies en `config/patreon_cookies.json`

**Ventajas**:
- ✅ Evita detección de bots
- ✅ Maneja 2FA si lo tienes
- ✅ Más confiable

### Opción B: Modo Automático

Modificar `src/patreon_auth_selenium.py`:

```python
# Cambiar esta línea:
if auth.login(manual_mode=True):  # ← manual_mode=True

# Por:
if auth.login(manual_mode=False):  # ← manual_mode=False
```

**Ventajas**:
- Más rápido
- No requiere intervención

**Desventajas**:
- ⚠️ Puede ser detectado
- ⚠️ No maneja 2FA

---

## 📋 Paso 2: Verificar Autenticación

Después del login, verás:

```
✅ Login successful! Obtained X cookies
Cookies: session_id, __cf_bm, ...
💾 Cookies saved to config/patreon_cookies.json

🔑 Session ID: abc123xyz...
```

**Esto significa**:
- ✅ Estás autenticado
- ✅ Las cookies están guardadas
- ✅ Puedes empezar a scrapear

---

## 🎯 Próximos Pasos (En desarrollo)

### Paso 3: Scrapear Posts

```bash
# Scrapear un creador
python3 src/patreon_scraper.py --creator headonhistory

# Scrapear todos los creadores
python3 src/patreon_scraper.py --all

# Solo los últimos N posts
python3 src/patreon_scraper.py --creator astrobymax --limit 10
```

### Paso 4: Descargar Multimedia

```bash
# Descargar media de posts scrapeados
python3 src/media_downloader.py --all

# Solo imágenes
python3 src/media_downloader.py --images-only

# Solo un creador
python3 src/media_downloader.py --creator horoiproject
```

### Paso 5: Generar Tags

```bash
# Generar tags con IA
python3 src/tag_generator.py --all

# Ver tags generados
python3 src/tag_generator.py --show-tags
```

### Paso 6: Subir a Notion

```bash
# Configurar Notion API key primero
# Editar config/credentials.json → notion.api_key

# Crear bases de datos en Notion
python3 src/notion_integrator.py --setup

# Subir posts
python3 src/notion_integrator.py --upload-all
```

---

## 📂 Archivos Importantes

### Después del Scraping

```
data/
├── raw/
│   ├── headonhistory_posts.json      ← Posts sin procesar
│   ├── astrobymax_posts.json
│   └── horoiproject_posts.json
├── processed/
│   ├── headonhistory_tagged.json     ← Posts con tags
│   ├── astrobymax_tagged.json
│   └── horoiproject_tagged.json
└── media/
    ├── images/
    │   ├── headonhistory/
    │   ├── astrobymax/
    │   └── horoiproject/
    ├── videos/
    │   └── ...
    └── audio/
        └── ...
```

### Cookies y Sesión

```
config/
├── credentials.json           ← Credenciales (NO compartir)
├── patreon_cookies.json       ← Cookies de sesión (NO compartir)
└── session.json               ← Info de sesión (NO compartir)
```

**⚠️ IMPORTANTE**: Estos archivos contienen información sensible. No los subas a GitHub.

---

## 🔧 Troubleshooting

### Error: "Chrome driver not found"

```bash
# Instalar webdriver-manager
pip install webdriver-manager

# O descargar ChromeDriver manualmente:
# https://chromedriver.chromium.org/downloads
```

### Error: "Login failed - Still on login page"

**Soluciones**:
1. Usa modo manual: `auth.login(manual_mode=True)`
2. Verifica credenciales en `config/credentials.json`
3. Comprueba si Patreon requiere 2FA
4. Espera más tiempo antes de presionar ENTER

### Error: "Cookies expired"

```bash
# Simplemente ejecuta de nuevo y haz login manual
python3 src/patreon_auth_selenium.py
```

Las cookies duran ~1 mes, así que no necesitarás hacer esto frecuentemente.

### Error: "403 Forbidden" o "Cloudflare challenge"

Patreon usa Cloudflare para protección. Soluciones:
1. **Usa Selenium** (ya implementado) en lugar de requests
2. **Modo manual** para pasar desafíos de Cloudflare
3. Espera unos segundos después de cargar página

---

## 📊 Estado del Proyecto

### ✅ Completado:

- [x] Estructura de proyecto
- [x] Sistema de configuración
- [x] Autenticación con Selenium (modo manual y automático)
- [x] Guardado/carga de cookies
- [x] Verificación de sesión

### 🚧 En Desarrollo:

- [ ] Scraper de posts
- [ ] Descargador de multimedia
- [ ] Generador de tags con IA
- [ ] Integración con Notion

### 📅 Planificado:

- [ ] Sistema de retry automático
- [ ] Logging completo
- [ ] Tests unitarios
- [ ] Docker container
- [ ] Scheduler para scraping periódico

---

## 💡 Tips

### Para Desarrollo

```bash
# Ver logs detallados
python3 src/patreon_auth_selenium.py --verbose

# Modo headless (sin ventana)
# Editar patreon_auth_selenium.py: headless=True
```

### Para Producción

1. **Primera vez**: Usa modo manual para obtener cookies
2. **Después**: Las cookies se reutilizan automáticamente
3. **Scraping**: Añadir delays para no sobrecargar Patreon
4. **Backup**: Guardar posts scrapeados regularmente

---

## 🎬 Ejemplo Completo

```bash
# 1. Autenticarse (solo primera vez o si cookies expiran)
python3 src/patreon_auth_selenium.py

# 2. Scrapear todos los posts de todos los creadores
python3 src/patreon_scraper.py --all

# 3. Descargar todas las imágenes, videos, audios
python3 src/media_downloader.py --all

# 4. Generar tags automáticamente con IA
python3 src/tag_generator.py --all

# 5. Subir todo a Notion
python3 src/notion_integrator.py --upload-all
```

**Resultado**:
- 📦 Todos los posts guardados en JSON
- 🖼️ Todas las imágenes descargadas
- 🎥 Todos los videos descargados
- 🎵 Todos los audios descargados
- 🏷️ Tags generados automáticamente
- 📝 Todo organizado en Notion

---

**¿Listo para empezar?**

```bash
python3 src/patreon_auth_selenium.py
```

¡Y sigue las instrucciones en pantalla!
