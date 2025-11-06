# ⏰ Automatización Diaria - Patreon Scraper

**Guía completa para configurar scraping automático diario con scrapers incrementales**

---

## 🎯 Objetivo

Configurar el sistema para que automáticamente:
1. **Detecte** posts nuevos cada día
2. **Scrape** solo el contenido nuevo (10-100x más rápido)
3. **Descargue** media de posts nuevos
4. **Actualice** collections que cambiaron

---

## ⚡ Sistema de Scraping Incremental

### Cómo Funciona

El sistema tiene **3 fases** con versiones incrementales:

#### Phase 1 - Incremental: `daily_incremental_scrape.py`
- Scrapea solo las **primeras 3 páginas** (~45 posts)
- **Para** al encontrar **3 posts consecutivos conocidos**
- Guarda nuevos posts en Firebase con estado "pending"
- **10-100x más rápido** que scrape completo

#### Phase 2 - Ya es incremental: `phase2_detail_extractor.py`
- Solo procesa posts con estado **"pending"** en Firebase
- Salta posts que ya tienen estado "processed"
- Descarga media solo de posts nuevos

#### Phase 3 - Incremental: `incremental_collections_scraper.py` 🆕
- Carga metadata de **todas** las collections
- Compara con collections existentes
- Solo procesa collections **NUEVAS** o con **post_count diferente**
- Hace **merge** con datos existentes
- Mucho más rápido que scrape completo

### Ventajas

- ✅ **No reprocesa**: Solo scrape contenido nuevo
- ✅ **Súper rápido**: Segundos vs minutos
- ✅ **Seguro**: Mantiene contenido existente intacto
- ✅ **Merge automático**: Combina nuevos con existentes
- ✅ **Eficiente**: Ahorra ancho de banda

---

## 🚀 Uso Manual del Scraper Incremental

### Workflow Diario Completo

```bash
# Activar entorno virtual
cd /home/javif/proyectos/astrologia/patreon
source venv/bin/activate

# 1. Scrape solo posts NUEVOS (para en los conocidos)
python src/daily_incremental_scrape.py --all
# ⚡ Toma segundos
# ✅ Encuentra ~0-10 posts nuevos por día

# 2. Procesar detalles de posts pendientes
python src/phase2_detail_extractor.py --all --headless
# ⚡ Solo procesa posts "pending"
# ✅ Descarga media automáticamente

# 3. Actualizar collections (solo nuevas/actualizadas)
python src/incremental_collections_scraper.py --all --headless
# ⚡ Solo scrapea collections que cambiaron
# ✅ Hace merge con existentes
```

### Ejemplo de Salida

```
============================================================
🔄 Incremental scrape: astrobymax
============================================================

📂 Found 234 existing posts in Firebase

🔍 Scraping page 1...
  ✨ NEW: Understanding Mercury Retrograde
  ✨ NEW: Full Moon Ritual Guide
  ✓ KNOWN: Jupiter in Taurus (stopping soon...)

🔍 Scraping page 2...
  ✓ KNOWN: Mars Transit
  ✓ KNOWN: Venus in Leo
  ✓ KNOWN: Saturn Update

⏹️  Found 3 consecutive known posts - stopping early

📊 RESULTS:
  🆕 New posts: 2
  ✓ Existing posts: 234
  📄 Total posts: 236
  ⚡ Saved ~15 minutes compared to full scrape!

✅ Incremental scrape complete!
```

---

## 🤖 Script de Automatización Diaria

### El Script: `daily_incremental_update.sh`

Crea un script bash que ejecute el pipeline completo:

```bash
#!/bin/bash
# daily_incremental_update.sh
# Actualización diaria incremental de Patreon

PROJECT_DIR="/home/javif/proyectos/astrologia/patreon"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/daily_update_${TIMESTAMP}.log"

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

# Función de logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "============================================================"
log "🚀 Starting daily incremental update"
log "============================================================"

# Cambiar al directorio del proyecto
cd "$PROJECT_DIR" || exit 1

# Activar entorno virtual
log "📦 Activating virtual environment..."
source "$VENV_DIR/bin/activate" || exit 1

# Phase 1: Scrape solo posts nuevos
log "⚡ Phase 1: Incremental URL collection..."
python src/daily_incremental_scrape.py --all 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    log "✅ Phase 1 completed successfully"
else
    log "❌ Phase 1 failed!"
    exit 1
fi

# Phase 2: Procesar detalles de posts pendientes
log "📝 Phase 2: Processing pending posts..."
python src/phase2_detail_extractor.py --all --headless 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    log "✅ Phase 2 completed successfully"
else
    log "❌ Phase 2 failed!"
    exit 1
fi

# Phase 3: Actualizar collections incrementalmente
log "📚 Phase 3: Incremental collections update..."
python src/incremental_collections_scraper.py --all --headless 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    log "✅ Phase 3 completed successfully"
else
    log "❌ Phase 3 failed!"
    exit 1
fi

log "============================================================"
log "✅ Daily incremental update completed!"
log "============================================================"

# Desactivar entorno virtual
deactivate

exit 0
```

Hacer el script ejecutable:

```bash
chmod +x daily_incremental_update.sh
```

---

## ⏰ Configuración de Cron (Ejecución Diaria Automática)

### Paso 1: Probar el Script Manualmente

Primero verifica que funciona:

```bash
./daily_incremental_update.sh
```

Revisa el log:

```bash
tail -f logs/daily_update_*.log
```

### Paso 2: Configurar Cron

```bash
# Editar crontab
crontab -e
```

Añade una de estas líneas:

```bash
# Opción 1: Diario a las 3 AM (recomendado - poco tráfico)
0 3 * * * /home/javif/proyectos/astrologia/patreon/daily_incremental_update.sh

# Opción 2: Diario a las 8 AM (antes de empezar el día)
0 8 * * * /home/javif/proyectos/astrologia/patreon/daily_incremental_update.sh

# Opción 3: Dos veces al día (8 AM y 8 PM)
0 8,20 * * * /home/javif/proyectos/astrologia/patreon/daily_incremental_update.sh

# Opción 4: Cada 12 horas
0 */12 * * * /home/javif/proyectos/astrologia/patreon/daily_incremental_update.sh
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
- `0 */12 * * *` - Cada 12 horas
- `0 8,20 * * *` - A las 8 AM y 8 PM
- `0 9 * * 1` - Lunes a las 9 AM

### Paso 3: Verificar Cron

```bash
# Ver crontab actual
crontab -l

# Ver log del sistema de cron
grep CRON /var/log/syslog | tail -20

# Ver logs de tu script
ls -lt logs/daily_update_*.log | head -5
tail -f logs/daily_update_*.log
```

---

## 📊 Monitoreo y Logs

### Archivos de Log

El sistema genera logs organizados:

```
logs/
├── daily_update_20251106_030000.log  ← Log de cada ejecución
├── phase1_url_collector.log          ← Log de Phase 1
├── phase2_detail_extractor.log       ← Log de Phase 2
├── incremental_collections_scraper.log ← Log de Phase 3
└── cron.log                          ← Log general de cron
```

### Ver Logs en Tiempo Real

```bash
# Log de última ejecución diaria
tail -f logs/daily_update_*.log

# Log de Phase 1 (incremental)
tail -f logs/phase1_url_collector.log

# Log de Phase 3 (collections)
tail -f logs/incremental_collections_scraper.log

# Todos los logs
tail -f logs/*.log
```

### Estadísticas

```bash
# Ver posts en Firebase
# (requiere Firebase CLI o web console)

# Ver archivos generados
ls -lh data/processed/

# Ver collections
cat data/processed/astrobymax_collections.json | jq '.collections | length'
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

3. Verificar permisos del script:
   ```bash
   ls -l daily_incremental_update.sh
   chmod +x daily_incremental_update.sh
   ```

### Browser no se inicia (headless)

**Problema**: ChromeDriver falla en modo headless

**Solución**: Verificar que Chrome está instalado:

```bash
google-chrome --version
chromedriver --version
```

### Cookies expiran

**Problema**: Las cookies de Patreon expiran

**Solución**: Las cookies se renuevan automáticamente en cada scrape. Si fallan:

```bash
# Autenticar manualmente
python src/phase1_url_collector.py --creator astrobymax
# Esto renovará las cookies
```

### No encuentra posts nuevos

**Problema**: El incremental no encuentra posts nuevos pero hay posts publicados

**Solución**: Verifica que Firebase tiene los posts existentes correctamente:

```bash
# Hacer un scrape completo para resetear
python src/phase1_url_collector.py --all
```

---

## 📈 Flujo de Trabajo Recomendado

### Configuración Inicial (Una Vez)

```bash
# 1. Scrape completo inicial (primera vez)
python src/phase1_url_collector.py --all
python src/phase2_detail_extractor.py --all --headless
python src/phase3_collections_scraper.py --all --headless

# 2. Crear script de automatización
nano daily_incremental_update.sh
# (Copiar el script de arriba)
chmod +x daily_incremental_update.sh

# 3. Probar script manualmente
./daily_incremental_update.sh

# 4. Configurar cron
crontab -e
# (Añadir línea de cron)
```

### Ejecución Diaria Automática

El cron ejecutará:

```bash
./daily_incremental_update.sh
```

Que hará:
1. ✅ Scrape incremental Phase 1 (solo nuevos posts)
2. ✅ Procesar detalles Phase 2 (solo pendientes)
3. ✅ Actualizar collections Phase 3 (solo actualizadas)

**Tiempo total**: ~30 segundos - 5 minutos (vs 30-60 minutos del scrape completo)

### Mantenimiento Mensual

```bash
# Verificar logs
tail -100 logs/daily_update_*.log

# Verificar espacio en disco
du -sh data/

# Limpiar logs antiguos (opcional)
find logs/ -name "*.log" -mtime +30 -delete
```

---

## 💡 Tips y Mejores Prácticas

### 1. Horario Óptimo

- **3 AM** - Ideal, poco tráfico en Patreon
- **8 AM** - Antes de empezar el día
- **Evitar** - Horas pico (12-2 PM, 7-9 PM)

### 2. Frecuencia Recomendada

- **Diario**: Si quieres contenido siempre actualizado
- **2-3 veces por semana**: Para uso más relajado
- **Semanal**: Mínimo recomendado

### 3. Backup Regular

```bash
# Añadir al crontab - backup semanal (domingos a las 2 AM)
0 2 * * 0 tar -czf /backups/patreon_$(date +\%Y\%m\%d).tar.gz /home/javif/proyectos/astrologia/patreon/data
```

### 4. Monitorear Espacio en Disco

```bash
# Verificar espacio usado
du -sh data/*

# Ver archivos más grandes
du -ah data/ | sort -rh | head -20
```

### 5. Notificaciones (Opcional)

Añade al final del script:

```bash
# Enviar notificación al terminar (Linux desktop)
notify-send "Patreon Scraper" "Daily update completed! ✅"

# O enviar email (si tienes mail configurado)
echo "Daily Patreon update completed" | mail -s "Patreon Update" tu@email.com
```

---

## ✅ Checklist de Configuración

- [ ] Scripts de 3 fases funcionan correctamente
- [ ] Script `daily_incremental_update.sh` creado y ejecutable
- [ ] Test manual del script exitoso
- [ ] Crontab configurado con horario deseado
- [ ] Logs directory tiene permisos correctos
- [ ] Primera ejecución automática verificada (esperar al horario del cron)
- [ ] Logs se generan correctamente

---

## 🎉 Resultado Final

**¡Con esto tendrás un sistema completamente automatizado!**

✅ **Se ejecuta automáticamente** cada día
✅ **Solo procesa contenido nuevo** (súper rápido)
✅ **Descarga media automáticamente**
✅ **Actualiza collections**
✅ **Logs detallados** para monitorear
✅ **Sin intervención manual** necesaria

**Tiempo de ejecución diaria**: ~30 segundos - 5 minutos
**vs scrape completo**: 30-60 minutos

**¡10-100x más eficiente!** ⚡🚀
