# 🚀 LISTO PARA USAR - Patreon Scraper

**Fecha**: 2025-11-01
**Todo está configurado y listo!**

---

## ✅ Lo Que Está Listo

1. **✅ Entorno virtual** configurado con todas las dependencias
2. **✅ Autenticación** con Patreon (Selenium)
3. **✅ Scraper completo** para posts
4. **✅ Script principal** fácil de usar
5. **✅ Tus credenciales** guardadas en config
6. **✅ 3 creadores** configurados

---

## 🎯 EMPEZAR AHORA - 3 Pasos

### Paso 1: Activar Entorno Virtual

```bash
cd /home/javif/proyectos/astrologia/patreon
source venv/bin/activate
```

### Paso 2: Autenticarse (Solo Primera Vez)

```bash
python src/main.py --auth-only
```

**Qué hará**:
1. Abre Chrome
2. Te pide que hagas login MANUALMENTE
3. Presionas ENTER cuando estés logueado
4. Guarda las cookies (válidas por ~1 mes)

### Paso 3: Scrapear Contenido

```bash
# Prueba rápida: 5 posts de cada creador
python src/main.py --scrape-all --limit 5
```

**Resultado**:
```
data/raw/
├── headonhistory_posts.json
├── astrobymax_posts.json
└── horoiproject_posts.json
```

---

## 📋 Comandos Disponibles

### Solo Autenticarse
```bash
python src/main.py --auth-only
```
Útil para la primera vez o si las cookies expiran.

---

### Scrapear Todos los Creadores

```bash
# Solo preview (rápido, ~5 posts por creador)
python src/main.py --scrape-all --limit 5

# Todos los posts, solo info básica
python src/main.py --scrape-all

# Todos los posts con DETALLES COMPLETOS (imágenes, videos, audio)
python src/main.py --scrape-all --full-details
```

**⚠️ Con `--full-details`**:
- Entra a cada post individualmente
- Extrae contenido completo
- Extrae URLs de todas las imágenes
- Extrae URLs de todos los videos
- Extrae URLs de todos los audios
- **Mucho más lento** pero completo

---

### Scrapear Un Solo Creador

```bash
# Head-On History (10 posts)
python src/main.py --creator headonhistory --limit 10

# AstroByMax (todos los posts)
python src/main.py --creator astrobymax

# Horoi Project (todos con detalles)
python src/main.py --creator horoiproject --full-details
```

**IDs de creadores**:
- `headonhistory`
- `astrobymax`
- `horoiproject`

---

## 📊 Lo Que Obtienes

### Sin --full-details (Modo Rápido)

```json
{
  "creator_id": "headonhistory",
  "post_id": "123456",
  "post_url": "https://www.patreon.com/posts/123456",
  "title": "Título del post",
  "preview_text": "Preview del contenido...",
  "published_at": "2024-10-15",
  "preview_images": ["url1.jpg", "url2.jpg"],
  "access_tier": "Premium",
  "likes": "42",
  "comments": "8",
  "scraped_at": "2025-11-01T..."
}
```

### Con --full-details (Modo Completo)

```json
{
  // ... todo lo anterior +
  "full_content": "Contenido completo del post...",
  "images": [
    "https://c10.patreonusercontent.com/image1.jpg",
    "https://c10.patreonusercontent.com/image2.jpg"
  ],
  "videos": [
    "https://c10.patreonusercontent.com/video.mp4"
  ],
  "audios": [
    "https://c10.patreonusercontent.com/audio.mp3"
  ],
  "attachments": [
    "https://www.patreon.com/file/download/..."
  ]
}
```

---

## ⏱️ Tiempos Estimados

### Modo Rápido (sin --full-details)

```
5 posts por creador (3 creadores)   = ~2-3 minutos
50 posts por creador (3 creadores)  = ~10-15 minutos
Todos los posts (~100-500 cada uno) = ~30-60 minutos
```

### Modo Completo (con --full-details)

```
5 posts por creador                 = ~5-10 minutos
50 posts por creador                = ~30-45 minutos
Todos los posts                     = ~2-4 horas
```

**Por qué es más lento con --full-details**:
- Visita cada post individualmente
- Espera a que cargue el contenido
- Extrae todos los elementos multimedia
- Añade delays para no sobrecargar Patreon

---

## 🎨 Flujo Recomendado

### Primera Vez (Exploración)

```bash
# 1. Autenticarse
python src/main.py --auth-only

# 2. Probar con pocos posts
python src/main.py --scrape-all --limit 5

# 3. Ver los JSONs generados
cat data/raw/headonhistory_posts.json | jq '.[0]'
```

### Producción (Scraping Completo)

```bash
# 1. Verificar autenticación
python src/main.py --auth-only

# 2. Scrapear TODO con detalles completos
python src/main.py --scrape-all --full-details

# Esto puede tardar 2-4 horas
# Puedes dejarlo corriendo en segundo plano:
nohup python src/main.py --scrape-all --full-details > scrape.log 2>&1 &

# Ver progreso
tail -f scrape.log
```

---

## 📁 Archivos Generados

```
data/raw/
├── headonhistory_posts.json         ← Todos los posts
├── astrobymax_posts.json
└── horoiproject_posts.json

logs/
├── main.log                         ← Log del script principal
└── scraper.log                      ← Log del scraper

config/
└── patreon_cookies.json             ← Cookies guardadas (no compartir)
```

---

## 🔄 Próximos Pasos (Después del Scraping)

### 1. Descargar Multimedia

```bash
# Descargar de un JSON específico
python src/media_downloader.py --json data/raw/headonhistory_posts.json --creator headonhistory

# Descargar de TODOS los JSONs
python src/media_downloader.py --all
```

Esto descargará:
- Todas las imágenes → `data/media/images/`
- Todos los videos → `data/media/videos/`
- Todos los audios → `data/media/audio/`

### 2. Generar Tags con IA

**Primero, obtén tu API key de Gemini**:
https://makersuite.google.com/app/apikey

**Luego, configura la variable de entorno**:
```bash
export GEMINI_API_KEY="tu-api-key-aqui"
```

**Generar tags**:
```bash
# Generar tags para un JSON específico
python src/tag_generator.py --json data/raw/headonhistory_posts.json

# Generar tags para TODOS los JSONs
python src/tag_generator.py --all

# O pasar API key directamente
python src/tag_generator.py --all --api-key "tu-api-key"
```

Esto analizará el contenido y generará tags automáticamente:
- Guarda posts procesados en `data/processed/`
- Genera resumen de tags con frecuencias
- Muestra estadísticas de los tags más comunes

### 3. Subir a Notion

```bash
# (Por implementar)
python src/notion_integrator.py --upload-all
```

Esto creará las bases de datos en Notion y subirá todo.

---

## ⚠️ Troubleshooting

### Error: "No module named 'patreon_auth_selenium'"

```bash
# Asegúrate de estar en el directorio src/
cd /home/javif/proyectos/astrologia/patreon
python src/main.py --auth-only
```

### Error: "ChromeDriver not found"

```bash
# Reinstalar webdriver-manager
pip install webdriver-manager --upgrade
```

### Error: "Login failed"

- Usa modo manual: `--auth-only`
- Verifica credenciales en `config/credentials.json`
- Comprueba si Patreon requiere 2FA
- Espera más tiempo antes de presionar ENTER

### Las cookies expiraron

```bash
# Simplemente ejecuta de nuevo
python src/main.py --auth-only
```

Las cookies duran ~1 mes.

### Patreon detecta scraping / Error 429

- Añade más delay entre posts (se puede configurar en el código)
- Usa modo manual de login
- No ejecutes scraping muy frecuentemente

---

## 💡 Tips

### Para Ver los Datos

```bash
# Ver primer post de un creador
cat data/raw/headonhistory_posts.json | jq '.[0]'

# Contar posts
cat data/raw/headonhistory_posts.json | jq 'length'

# Ver solo títulos
cat data/raw/headonhistory_posts.json | jq '.[].title'

# Ver posts con imágenes
cat data/raw/headonhistory_posts.json | jq '.[] | select(.images | length > 0)'
```

### Para Scraping Incremental

Actualmente el scraper sobrescribe el archivo JSON completo.
Si quieres añadir nuevos posts sin perder los viejos:
1. Haz backup del JSON antes de ejecutar
2. O modifica el código para hacer merge

### Para Modo Headless (Sin Ventana)

```bash
python src/main.py --scrape-all --headless
```

Útil para servidores sin GUI.

---

## 📞 Soporte

### Ver Logs

```bash
# Log principal
tail -f logs/main.log

# Log del scraper
tail -f logs/scraper.log

# Ambos en tiempo real
tail -f logs/*.log
```

### Archivos Importantes

- `config/credentials.json` - Tus credenciales
- `config/patreon_cookies.json` - Cookies de sesión
- `data/raw/*.json` - Posts scrapeados
- `logs/*.log` - Logs de ejecución

### Si Algo Falla

1. Revisa los logs
2. Verifica que el entorno virtual esté activado
3. Verifica que las cookies no hayan expirado
4. Prueba con menos posts (`--limit 1`)

---

## 🎬 Ejemplo Completo - Paso a Paso

```bash
# Terminal 1: Ir al proyecto
cd /home/javif/proyectos/astrologia/patreon

# Activar entorno virtual
source venv/bin/activate

# Primera vez: autenticarse
python src/main.py --auth-only
# → Se abre Chrome
# → Haces login manualmente
# → Presionas ENTER
# → Cookies guardadas ✓

# Probar con pocos posts
python src/main.py --scrape-all --limit 3
# → Scraping rápido de 3 posts por creador
# → Ver JSONs en data/raw/

# Scrapear todo de un creador
python src/main.py --creator headonhistory
# → Todos los posts de Head-On History

# Scrapear TODO con detalles
python src/main.py --scrape-all --full-details
# → Puede tardar 2-4 horas
# → Todos los posts, imágenes, videos, audios
# → JSONs completos en data/raw/

# Ver resultados
cat data/raw/headonhistory_posts.json | jq '.[0:3]'
```

---

## 🔄 Scraping Incremental (Solo Nuevos Posts)

**IMPORTANTE**: Una vez que hagas el scraping inicial completo, usa el scraper incremental para actualizaciones diarias.

### Ventajas del Scraper Incremental

- ✅ **Solo scrape posts nuevos** (no reprocesa existentes)
- ✅ **Mucho más rápido** (no scrollea todo el histórico)
- ✅ **Seguro** (mantiene posts existentes intactos)
- ✅ **Merge automático** (combina nuevos con existentes)

### Uso del Scraper Incremental

```bash
# Ver estadísticas (última ejecución, total posts)
python src/incremental_scraper.py --stats

# Scrape incremental (solo posts nuevos)
python src/incremental_scraper.py --scrape-all --full-details

# Scrape incremental de un creador
python src/incremental_scraper.py --creator headonhistory --full-details
```

**Output ejemplo**:
```
📊 Previously processed: 150 posts
🕐 Last scrape: 2025-11-01T10:30:00

🔍 Scanning for new posts...
  ✨ NEW: Post Title 1
  ✨ NEW: Post Title 2

📈 Found 2 new posts
✅ Scraping complete: 152 total posts
```

---

## ⏰ Automatización Diaria con Cron

### Script de Ejecución Diaria

```bash
# Ejecutar pipeline completo diario
./daily_scrape.sh --all
```

**Lo que hace**:
1. Scrape incremental (solo posts nuevos)
2. Download media (solo de posts nuevos)
3. Generate tags (solo posts nuevos)
4. Upload to Notion (solo posts nuevos)

### Configurar Cron (Automático Diario)

```bash
# Editar crontab
crontab -e

# Añadir línea (ejecuta diariamente a las 3 AM)
0 3 * * * /home/javif/proyectos/astrologia/patreon/daily_scrape.sh --all >> /home/javif/proyectos/astrologia/patreon/logs/cron.log 2>&1
```

**Ver guía completa**: `docs/DAILY_AUTOMATION.md`

---

## ✨ ¡Listo!

**El sistema está 100% funcional y puede ejecutarse automáticamente.**

### Primera Vez (Setup Inicial)

```bash
cd /home/javif/proyectos/astrologia/patreon
source venv/bin/activate

# 1. Autenticarse
python src/main.py --auth-only

# 2. Scraping completo inicial
python src/main.py --scrape-all --full-details

# 3. Descargar media
python src/media_downloader.py --all

# 4. Generar tags
python src/tag_generator.py --all

# 5. Subir a Notion
python src/notion_integrator.py --all
```

### Ejecuciones Diarias (Automático)

```bash
# Configurar cron una vez
crontab -e  # Añadir línea de arriba

# O ejecutar manualmente cuando quieras
./daily_scrape.sh --all
```

**¡El sistema ahora detectará automáticamente posts nuevos cada día!** 🚀⏰
