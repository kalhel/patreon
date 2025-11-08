#!/usr/bin/env python3
"""
SAFE ANALYSIS SCRIPT (READ-ONLY) - Post 141632966
Analyzes content block order to identify:
1. Where YouTube video is currently placed
2. Where it should be (after "3 min flash" text)
3. Missing Vimeo video
"""

import psycopg2
import os
from dotenv import load_dotenv

def main():
    load_dotenv()

    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'alejandria'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )

    cursor = conn.cursor()

    # Get all content blocks with their order
    cursor.execute("""
        SELECT content_blocks
        FROM posts
        WHERE post_id = '141632966'
    """)

    row = cursor.fetchone()
    if not row:
        print("❌ Post not found")
        conn.close()
        return

    content_blocks = row[0]

    print("=" * 100)
    print("ANÁLISIS DE ORDEN DE BLOQUES - POST 141632966")
    print("=" * 100)
    print()

    youtube_position = None
    youtube_order = None
    reference_text_position = None
    reference_text_order = None
    vimeo_found = []
    vimeo_in_html = []

    print("BLOQUES DE CONTENIDO EN ORDEN ACTUAL:")
    print("-" * 100)

    for i, block in enumerate(content_blocks):
        block_type = block.get('type', 'unknown')
        order = block.get('order', 'N/A')
        url = block.get('url', '')
        text = block.get('text', '')
        local_path = block.get('local_path', '')

        # Display block info
        marker = ""

        if url and 'youtu' in url.lower():
            youtube_position = i
            youtube_order = order
            marker = "🎥 YOUTUBE VIDEO AQUÍ"

        if text and '3 min flash' in text:
            reference_text_position = i
            reference_text_order = order
            marker = "⭐ TEXTO DE REFERENCIA - El video debería estar DESPUÉS de aquí"

        if url and 'vimeo' in url.lower():
            vimeo_found.append({'position': i, 'url': url, 'order': order})
            marker = "🎥 VIMEO VIDEO"

        if text and 'vimeo' in text.lower():
            # Extract vimeo reference from HTML
            import re
            vimeo_matches = re.findall(r'vimeo\.com/[^\s"<>]+', text, re.IGNORECASE)
            if vimeo_matches:
                vimeo_in_html.append({
                    'position': i,
                    'matches': vimeo_matches,
                    'order': order
                })

        print(f"\nPosición {i:3d} | Order: {str(order):4s} | Tipo: {block_type:20s} {marker}")

        if url:
            print(f"           URL: {url[:80]}...")
        if text and len(text) > 0:
            preview = text[:120].replace('\n', ' ')
            print(f"           Texto: {preview}...")
        if local_path:
            print(f"           Archivo local: {local_path}")

    print()
    print("=" * 100)
    print("DIAGNÓSTICO")
    print("=" * 100)
    print()

    # YouTube video placement
    if youtube_position is not None:
        print(f"✓ Video de YouTube encontrado en posición {youtube_position} (order: {youtube_order})")
    else:
        print("❌ No se encontró video de YouTube")

    # Reference text placement
    if reference_text_position is not None:
        print(f"✓ Texto de referencia '3 min flash' encontrado en posición {reference_text_position} (order: {reference_text_order})")
    else:
        print("❌ No se encontró el texto de referencia")

    print()

    # Check if order is correct
    if youtube_position is not None and reference_text_position is not None:
        if youtube_position < reference_text_position:
            print("❌ PROBLEMA DETECTADO:")
            print(f"   El video de YouTube está en posición {youtube_position}")
            print(f"   Pero el texto que lo menciona está en posición {reference_text_position}")
            print(f"   El video debería estar DESPUÉS del texto (posición {reference_text_position + 1} o mayor)")
            print()
            print(f"   Distancia: {reference_text_position - youtube_position} bloques de diferencia")
        else:
            print("✓ El video está correctamente posicionado DESPUÉS del texto de referencia")

    print()
    print("-" * 100)
    print("BÚSQUEDA DE VIDEO VIMEO")
    print("-" * 100)

    if vimeo_found:
        print(f"✓ Se encontraron {len(vimeo_found)} bloques con URL de Vimeo:")
        for v in vimeo_found:
            print(f"   Posición {v['position']} (order: {v['order']}): {v['url']}")
    else:
        print("❌ No se encontraron bloques con URL de Vimeo")

    print()

    if vimeo_in_html:
        print(f"⚠️  Se encontraron {len(vimeo_in_html)} referencias a Vimeo en HTML (no capturadas como bloques):")
        for v in vimeo_in_html:
            print(f"   Posición {v['position']} (order: {v['order']}): {v['matches']}")
            print("   ⚠️  ESTO INDICA QUE EL VIDEO DE VIMEO NO FUE EXTRAÍDO CORRECTAMENTE")
    else:
        print("ℹ️  No se encontraron referencias a Vimeo en el HTML")

    print()
    print("=" * 100)
    print("RECOMENDACIONES")
    print("=" * 100)
    print()

    if youtube_position is not None and reference_text_position is not None and youtube_position < reference_text_position:
        print("1. REORDENAR BLOQUES:")
        print(f"   - Mover el bloque de YouTube de la posición {youtube_position} a después de la posición {reference_text_position}")
        print()

    if vimeo_in_html:
        print("2. CAPTURAR VIDEO DE VIMEO:")
        print("   - Hay referencias a Vimeo en el HTML que no fueron extraídas")
        print("   - Necesitas actualizar el scraper para detectar estos embeds")
        print("   - URLs encontradas:")
        for v in vimeo_in_html:
            for match in v['matches']:
                print(f"     https://{match}")

    conn.close()

if __name__ == '__main__':
    main()
