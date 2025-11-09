# Alejandría - Patreon Content Scraper
# Makefile para comandos comunes del proyecto

.PHONY: help scrape scrape-daily scrape-full test test-phase2 test-phase3 test-web test-connections setup setup-infra backup restore web web-dev clean-vtt reset-creator analyze-media install

# Colores para output
BLUE := \033[36m
RESET := \033[0m

help:  ## Muestra esta ayuda
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Alejandría - Patreon Content Scraper"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Comandos disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ═══════════════════════════════════════════════════════════════
# SCRAPING
# ═══════════════════════════════════════════════════════════════

scrape: scrape-daily  ## Ejecuta scraping diario (alias de scrape-daily)

scrape-daily:  ## Scraping diario incremental (Phase 1 + Phase 2)
	@echo "$(BLUE)Ejecutando scraping diario incremental...$(RESET)"
	@bash tools/automation/daily_scrape_v2.sh

scrape-full:  ## Scraping completo de todos los posts
	@echo "$(BLUE)Ejecutando scraping completo...$(RESET)"
	@bash tools/automation/daily_scrape_v2.sh --full

scrape-legacy:  ## Scraping con el sistema legacy (incremental_scraper.py)
	@echo "$(BLUE)Ejecutando scraping legacy...$(RESET)"
	@bash tools/automation/daily_scrape.sh

# ═══════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════

test: test-phase2 test-phase3 test-web  ## Ejecuta todos los tests

test-phase2:  ## Test de Phase 2 (detail extractor)
	@echo "$(BLUE)Testing Phase 2...$(RESET)"
	@python3 tools/testing/test_phase2_postgres.py

test-phase3:  ## Test de Phase 3 (collections)
	@echo "$(BLUE)Testing Phase 3...$(RESET)"
	@python3 tools/testing/test_phase3_postgres.py

test-web:  ## Test de Web Viewer
	@echo "$(BLUE)Testing Web Viewer...$(RESET)"
	@python3 tools/testing/test_web_viewer_postgres.py

test-connections:  ## Test de conexiones (PostgreSQL, Redis)
	@echo "$(BLUE)Testing conexiones a servicios...$(RESET)"
	@python3 tools/testing/test_connections.py

test-media:  ## Test de media downloader
	@echo "$(BLUE)Testing media downloader...$(RESET)"
	@python3 tools/testing/test_media_downloader.py

# ═══════════════════════════════════════════════════════════════
# SETUP & INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════

setup:  ## Setup inicial del proyecto (venv + dependencias)
	@echo "$(BLUE)Setup inicial del proyecto...$(RESET)"
	@bash tools/setup/setup.sh

setup-infra:  ## Setup de infraestructura (PostgreSQL, Redis, pgvector)
	@echo "$(BLUE)Setup de infraestructura...$(RESET)"
	@bash tools/setup/setup_phase0.sh

install:  ## Instala dependencias Python
	@echo "$(BLUE)Instalando dependencias...$(RESET)"
	@pip install -r requirements.txt

# ═══════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════

backup:  ## Backup de PostgreSQL
	@echo "$(BLUE)Creando backup de PostgreSQL...$(RESET)"
	@bash tools/system/backup_database.sh

restore:  ## Restaura último backup
	@echo "$(BLUE)Restaurando último backup...$(RESET)"
	@bash tools/system/restore_backup.sh

# ═══════════════════════════════════════════════════════════════
# WEB VIEWER
# ═══════════════════════════════════════════════════════════════

web:  ## Inicia web viewer (Gunicorn - producción)
	@echo "$(BLUE)Iniciando web viewer con Gunicorn...$(RESET)"
	@bash tools/system/start_web_viewer.sh

web-dev:  ## Inicia web viewer en modo desarrollo
	@echo "$(BLUE)Iniciando web viewer en modo desarrollo...$(RESET)"
	@cd web && python3 viewer.py

# ═══════════════════════════════════════════════════════════════
# MAINTENANCE
# ═══════════════════════════════════════════════════════════════

clean-vtt:  ## Limpia parámetros de archivos VTT
	@echo "$(BLUE)Limpiando archivos VTT...$(RESET)"
	@python3 tools/maintenance/clean_vtt_files.py

cleanup-mux:  ## Limpia thumbnails de Mux del campo videos
	@echo "$(BLUE)Limpiando thumbnails de Mux...$(RESET)"
	@python3 tools/maintenance/cleanup_mux_thumbnails.py

reset-creator:  ## Reset de un creator específico
	@echo "$(BLUE)Reset de creator (interactivo)...$(RESET)"
	@cd src && python3 reset_creator.py

reset-missing:  ## Reset posts faltantes a estado pending
	@echo "$(BLUE)Reseteando posts faltantes...$(RESET)"
	@python3 tools/maintenance/reset_missing_posts_to_pending.py

reset-processed:  ## Reset posts procesados a pending
	@echo "$(BLUE)Reseteando posts procesados...$(RESET)"
	@python3 tools/maintenance/reset_processed_posts.py

# ═══════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════

analyze-media:  ## Analiza estructura de media (tamaños, duplicados)
	@echo "$(BLUE)Analizando estructura de media...$(RESET)"
	@python3 tools/diagnostics/analyze_media_structure.py

# ═══════════════════════════════════════════════════════════════
# DEFAULT
# ═══════════════════════════════════════════════════════════════

.DEFAULT_GOAL := help
