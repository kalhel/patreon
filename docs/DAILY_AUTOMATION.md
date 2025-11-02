# ⏰ Automatización Diaria - Patreon Scraper

**Guía completa para configurar scraping automático diario**

---

## 🎯 Objetivo

Configurar el sistema para que automáticamente:
1. **Detecte** posts nuevos cada día
2. **Scrape** solo el contenido nuevo (no reprocesa existentes)
3. **Descargue** media de posts nuevos
4. **Genere** tags con IA
5. **Suba** a Notion automáticamente

---

## ✨ Sistema de Scraping Incremental

### Cómo Funciona

El sistema mantiene un **archivo de estado** (`data/state/{creator}_state.json`) para cada creador que incluye:

```json
{
  "creator_id": "headonhistory",
  "last_scrape": "2025-11-01T10:30:00",
  "processed_post_ids": ["123456", "123455", "123454", ...],
  "total_posts": 150,
  "last_post_date": "2024-10-30"
}
```

### Ventajas

- ✅ **No reprocesa**: Solo scrape posts nuevos
- ✅ **Rápido**: No necesita scrollear todo el histórico
- ✅ **Seguro**: Mantiene posts existentes intactos
- ✅ **Merge automático**: Combina nuevos con existentes
- ✅ **Estadísticas**: Tracking de última ejecución

---

## 🚀 Uso Manual del Scraper Incremental

### Comandos Básicos

```bash
# Ver estadísticas (cuándo fue último scrape)
python src/incremental_scraper.py --stats

# Scrape incremental de todos los creadores (solo nuevos)
python src/incremental_scraper.py --scrape-all

# Scrape incremental con detalles completos
python src/incremental_scraper.py --scrape-all --full-details

# Scrape incremental de un solo creador
python src/incremental_scraper.py --creator headonhistory --full-details

# Reset state (forzar rescrape completo)
python src/incremental_scraper.py --reset headonhistory
```

### Ejemplo de Salida

```
============================================================
INCREMENTAL SCRAPE: headonhistory
============================================================

📊 Previously processed: 150 posts
🕐 Last scrape: 2025-11-01T10:30:00

🔍 Scanning for new posts...
  ✨ NEW: New Post Title Here
  ✨ NEW: Another New Post

📈 Found 2 new posts
📋 Kept 150 existing posts

📄 Scraping full details for 2 new posts...
  [1/2] New Post Title Here...
  [2/2] Another New Post...

💾 Saved state: 152 posts tracked

✅ Incremental scrape complete:
   ✨ New posts: 2
   📋 Existing posts: 150
   📊 Total posts: 152
```

---

## 🤖 Script de Automatización Diaria

### El Script: `daily_scrape.sh`

Script bash que ejecuta el pipeline completo:

```bash
./daily_scrape.sh [opciones]
```

### Opciones Disponibles

| Opción | Descripción |
|--------|-------------|
| `--full-details` | Scrape detalles completos de posts nuevos |
| `--with-media` | Descargar media después de scrapear |
| `--with-tags` | Generar tags con IA |
| `--with-notion` | Subir a Notion |
| `--all` | Hacer todo (equivale a todas las opciones anteriores) |

### Ejemplos de Uso

```bash
# Solo scrape rápido (metadata básica)
./daily_scrape.sh

# Scrape completo con detalles
./daily_scrape.sh --full-details

# Pipeline completo
./daily_scrape.sh --all

# Solo scrape y media (sin tags ni notion)
./daily_scrape.sh --full-details --with-media
```

### Variables de Entorno Necesarias

```bash
# Para generación de tags
export GEMINI_API_KEY="tu-gemini-api-key"

# Para subida a Notion
export NOTION_API_KEY="tu-notion-api-key"
```

---

## ⏰ Configuración de Cron (Ejecución Diaria Automática)

### Paso 1: Crear Script de Entorno

Primero crea un script que configure las variables de entorno:

```bash
# Crear archivo de entorno
nano /home/javif/proyectos/astrologia/patreon/.env
```

Contenido del archivo `.env`:

```bash
#!/bin/bash
# Environment variables for Patreon Scraper

export GEMINI_API_KEY="tu-gemini-api-key-aqui"
export NOTION_API_KEY="tu-notion-api-key-aqui"
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
```

```bash
# Hacer ejecutable
chmod +x /home/javif/proyectos/astrologia/patreon/.env
```

### Paso 2: Crear Script Wrapper para Cron

Cron necesita rutas absolutas y entorno configurado:

```bash
# Crear wrapper
nano /home/javif/proyectos/astrologia/patreon/cron_daily_scrape.sh
```

Contenido:

```bash
#!/bin/bash
# Wrapper for cron execution

# Load environment variables
source /home/javif/proyectos/astrologia/patreon/.env

# Change to project directory
cd /home/javif/proyectos/astrologia/patreon

# Run daily scrape
/home/javif/proyectos/astrologia/patreon/daily_scrape.sh --all

# Exit with status
exit $?
```

```bash
# Hacer ejecutable
chmod +x /home/javif/proyectos/astrologia/patreon/cron_daily_scrape.sh
```

### Paso 3: Configurar Cron

```bash
# Editar crontab
crontab -e
```

Añade una de estas líneas:

```bash
# Opción 1: Diario a las 3 AM (recomendado)
0 3 * * * /home/javif/proyectos/astrologia/patreon/cron_daily_scrape.sh >> /home/javif/proyectos/astrologia/patreon/logs/cron.log 2>&1

# Opción 2: Diario a las 8 AM
0 8 * * * /home/javif/proyectos/astrologia/patreon/cron_daily_scrape.sh >> /home/javif/proyectos/astrologia/patreon/logs/cron.log 2>&1

# Opción 3: Dos veces al día (8 AM y 8 PM)
0 8,20 * * * /home/javif/proyectos/astrologia/patreon/cron_daily_scrape.sh >> /home/javif/proyectos/astrologia/patreon/logs/cron.log 2>&1

# Opción 4: Cada 6 horas
0 */6 * * * /home/javif/proyectos/astrologia/patreon/cron_daily_scrape.sh >> /home/javif/proyectos/astrologia/patreon/logs/cron.log 2>&1
```

### Explicación del Formato Cron

```
┌───────────── minuto (0 - 59)
│ ┌───────────── hora (0 - 23)
│ │ ┌───────────── día del mes (1 - 31)
│ │ │ ┌───────────── mes (1 - 12)
│ │ │ │ ┌───────────── día de la semana (0 - 6) (Domingo=0)
│ │ │ │ │
│ │ │ │ │
* * * * * comando a ejecutar
```

Ejemplos:
- `0 3 * * *` - Diario a las 3:00 AM
- `0 */6 * * *` - Cada 6 horas
- `0 8,20 * * *` - A las 8 AM y 8 PM
- `0 9 * * 1` - Lunes a las 9 AM

### Paso 4: Verificar Cron

```bash
# Ver crontab actual
crontab -l

# Ver log del sistema de cron
grep CRON /var/log/syslog | tail -20

# Ver log de tu script
tail -f /home/javif/proyectos/astrologia/patreon/logs/cron.log
```

### Paso 5: Probar Manualmente

Antes de confiar en cron, prueba manualmente:

```bash
# Test del wrapper
/home/javif/proyectos/astrologia/patreon/cron_daily_scrape.sh

# Ver el log generado
cat /home/javif/proyectos/astrologia/patreon/logs/cron.log
```

---

## 📊 Monitoreo y Logs

### Archivos de Log

El sistema genera múltiples logs:

```
logs/
├── cron.log                           ← Log de ejecuciones cron
├── daily_scrape_20251101_030000.log  ← Log de cada ejecución diaria
├── incremental_scraper.log           ← Log del scraper incremental
├── main.log                          ← Log general
├── media_downloader.log              ← Log de descargas
├── tag_generator.log                 ← Log de generación de tags
└── notion_integrator.log             ← Log de subida a Notion
```

### Ver Logs en Tiempo Real

```bash
# Log del cron
tail -f logs/cron.log

# Log del scraper incremental
tail -f logs/incremental_scraper.log

# Todos los logs
tail -f logs/*.log
```

### Ver Estadísticas

```bash
# Ver estado de cada creador
python src/incremental_scraper.py --stats

# Ver resúmenes de scrapes
ls -lh data/state/scrape_summary_*.json
cat data/state/scrape_summary_latest.json
```

---

## 🔔 Notificaciones (Opcional)

### Opción 1: Notificaciones del Sistema (Linux Desktop)

Edita `daily_scrape.sh` y descomenta:

```bash
# Al final del script
notify-send "Patreon Scraper" "Found $NEW_POSTS new posts"
```

### Opción 2: Email

Añade al final de `cron_daily_scrape.sh`:

```bash
# Enviar email si hay posts nuevos
if [ "$NEW_POSTS" -gt 0 ]; then
    echo "Found $NEW_POSTS new Patreon posts" | mail -s "Patreon Update" tu@email.com
fi
```

### Opción 3: Telegram Bot (Avanzado)

Crea un script separado:

```bash
# notify_telegram.sh
#!/bin/bash
BOT_TOKEN="tu-bot-token"
CHAT_ID="tu-chat-id"
MESSAGE="$1"

curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
    -d chat_id="$CHAT_ID" \
    -d text="$MESSAGE"
```

Llámalo desde `daily_scrape.sh`:

```bash
./notify_telegram.sh "Found $NEW_POSTS new Patreon posts!"
```

---

## 🔧 Troubleshooting

### Cron no se ejecuta

**Problema**: El cron no parece ejecutarse

**Soluciones**:
1. Verificar que el servicio cron está corriendo:
   ```bash
   sudo systemctl status cron
   ```

2. Verificar errores en syslog:
   ```bash
   grep CRON /var/log/syslog | tail
   ```

3. Verificar permisos:
   ```bash
   ls -l /home/javif/proyectos/astrologia/patreon/*.sh
   ```

### Variables de entorno no funcionan

**Problema**: El script no puede acceder a API keys

**Solución**: Verificar que `.env` se está cargando correctamente:

```bash
# Añadir debug al wrapper
echo "GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}..." >> /tmp/cron_debug.log
echo "NOTION_API_KEY: ${NOTION_API_KEY:0:10}..." >> /tmp/cron_debug.log
```

### Browser no se inicia (headless)

**Problema**: ChromeDriver falla en modo headless

**Solución**: Verificar que Chrome está instalado y es compatible:

```bash
google-chrome --version
chromedriver --version
```

### Cookies expiran

**Problema**: Las cookies expiran antes del scrape

**Solución**: Re-autenticarse manualmente:

```bash
cd /home/javif/proyectos/astrologia/patreon
source venv/bin/activate
python src/main.py --auth-only
```

---

## 📈 Flujo de Trabajo Recomendado

### Configuración Inicial (Una Vez)

```bash
# 1. Scrape completo inicial
python src/main.py --scrape-all --full-details

# 2. Descargar toda la media
python src/media_downloader.py --all

# 3. Generar tags
python src/tag_generator.py --all

# 4. Subir a Notion
python src/notion_integrator.py --all

# 5. Configurar cron para ejecuciones diarias
crontab -e  # Añadir línea de cron
```

### Ejecución Diaria Automática

El cron ejecutará:

```bash
./daily_scrape.sh --all
```

Que hará:
1. ✅ Scrape incremental (solo nuevos posts)
2. ✅ Download media (solo de posts nuevos)
3. ✅ Generate tags (solo posts nuevos)
4. ✅ Upload to Notion (solo posts nuevos)

### Mantenimiento Mensual

```bash
# Verificar estado
python src/incremental_scraper.py --stats

# Verificar logs
tail -100 logs/cron.log

# Re-autenticarse (cookies expiran ~1 mes)
python src/main.py --auth-only
```

---

## 💡 Tips y Mejores Prácticas

### 1. Empezar Conservador

Comienza con scraping simple y ve añadiendo funcionalidad:

```bash
# Semana 1: Solo scrape
0 3 * * * .../daily_scrape.sh

# Semana 2: Scrape + media
0 3 * * * .../daily_scrape.sh --with-media

# Semana 3: Pipeline completo
0 3 * * * .../daily_scrape.sh --all
```

### 2. Horario Óptimo

- **3 AM** - Ideal, poco tráfico en Patreon
- **8 AM** - Antes de empezar el día
- **Evitar** - Horas pico (12-2 PM, 7-9 PM)

### 3. Backup Regular

```bash
# Añadir al crontab
0 2 * * 0 tar -czf /backups/patreon_$(date +\%Y\%m\%d).tar.gz /home/javif/proyectos/astrologia/patreon/data
```

### 4. Monitorear Espacio en Disco

```bash
# Verificar espacio usado
du -sh /home/javif/proyectos/astrologia/patreon/data/*

# Limpiar logs antiguos (más de 30 días)
find logs/ -name "*.log" -mtime +30 -delete
```

---

## ✅ Checklist de Configuración

- [ ] Script `daily_scrape.sh` es ejecutable
- [ ] Archivo `.env` creado con API keys
- [ ] Script wrapper `cron_daily_scrape.sh` creado y ejecutable
- [ ] Crontab configurado
- [ ] Test manual del wrapper exitoso
- [ ] Logs directory tiene permisos correctos
- [ ] Variables de entorno funcionan
- [ ] Primera ejecución automática verificada

---

**¡Con esto tendrás un sistema completamente automatizado que scrape Patreon diariamente sin intervención manual!** 🚀⏰
