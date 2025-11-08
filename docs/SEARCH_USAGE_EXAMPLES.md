# 🔍 Guía de Uso Avanzado de Búsquedas

**Fecha:** 2025-11-08
**Sistema actual:** SQLite FTS5 + PostgreSQL Full-Text Search

---

## 📚 Tabla de Contenidos

1. [Búsquedas Básicas](#búsquedas-básicas)
2. [Búsquedas Múltiples Términos](#búsquedas-múltiples-términos)
3. [Búsquedas Booleanas (AND, OR, NOT)](#búsquedas-booleanas)
4. [Búsquedas por Frases Exactas](#búsquedas-por-frases-exactas)
5. [Búsquedas con Prefijos (Wildcards)](#búsquedas-con-prefijos)
6. [Búsquedas Combinadas con Filtros](#búsquedas-combinadas-con-filtros)
7. [Búsquedas por Campo Específico](#búsquedas-por-campo-específico)
8. [Trucos Avanzados](#trucos-avanzados)

---

## 1. Búsquedas Básicas

### Buscar una palabra simple
```
astrology
```
**Resultado:** Encuentra todos los posts que contienen la palabra "astrology"

### Búsqueda case-insensitive
```
ASTROLOGY
Astrology
astrology
```
**Resultado:** Todas son equivalentes, la búsqueda no distingue mayúsculas/minúsculas

---

## 2. Búsquedas Múltiples Términos

### Buscar varias palabras (AND implícito)
```
moon phases astrology
```
**Resultado:** Encuentra posts que contienen **todas** las palabras: "moon" **Y** "phases" **Y** "astrology"

**Ejemplo de uso:**
- Quieres encontrar posts sobre fases lunares en astrología
- Todos los posts deben mencionar las tres palabras

### Buscar sinónimos o alternativas (OR)
```
moon OR luna
```
**Resultado:** Encuentra posts que contienen "moon" **O** "luna" (o ambas)

**Ejemplo de uso:**
- Buscar contenido en inglés y español
- "astrology OR astrología"

---

## 3. Búsquedas Booleanas

### AND - Todas las palabras deben aparecer
```
eclipse AND solar
```
**Resultado:** Solo posts que contienen **ambas** palabras

**Sistema actual (SQLite FTS5):**
```
eclipse solar     (espacio = AND implícito)
```

**Sistema PostgreSQL (futuro):**
```
eclipse & solar
```

### OR - Al menos una palabra debe aparecer
```
mars OR jupiter
```
**Resultado:** Posts que mencionan Marte **o** Júpiter (o ambos)

**Ejemplo de uso:**
- Buscar posts sobre cualquier planeta exterior
- "jupiter OR saturn OR uranus OR neptune"

### NOT - Excluir palabras
```
astrology NOT horoscope
```
**Resultado:** Posts que contienen "astrology" pero **NO** contienen "horoscope"

**Sistema actual (SQLite FTS5):**
```
astrology -horoscope
```

**Sistema PostgreSQL (futuro):**
```
astrology & !horoscope
```

**Ejemplo de uso:**
- Buscar astrología académica excluyendo horóscopos populares
- "mundane astrology NOT daily horoscope"

### Combinaciones complejas
```
(astrology OR astronomy) AND (planets NOT earth)
```
**Resultado:** Posts sobre astrología o astronomía que mencionan planetas pero no la Tierra

---

## 4. Búsquedas por Frases Exactas

### Frase exacta con comillas
```
"lunar eclipse"
```
**Resultado:** Solo posts que contienen exactamente "lunar eclipse" (palabras consecutivas)

**Diferencia:**
- `lunar eclipse` → Encuentra posts con "lunar" Y "eclipse" en cualquier parte
- `"lunar eclipse"` → Solo encuentra "lunar eclipse" como frase exacta

**Ejemplos de uso:**
```
"birth chart"
"retrograde mercury"
"full moon ritual"
"houses in astrology"
```

### Combinar frases exactas con palabras sueltas
```
"mundane astrology" predictions 2024
```
**Resultado:** Posts que contienen la frase exacta "mundane astrology" **Y** también "predictions" y "2024"

---

## 5. Búsquedas con Prefijos (Wildcards)

### Buscar por prefijo
```
astrol*
```
**Resultado:** Encuentra:
- astrology
- astrological
- astrologer
- astrolabe
- etc.

**Ejemplo de uso:**
- `merc*` → mercury, mercurial, merchant (ojo: puede dar falsos positivos)
- `plan*` → planet, planets, planetary, planning (ojo también)

### Mejores prácticas con prefijos
```
# ✅ BUENO - Específico
retrograd*   → retrograde, retrogrades, retrogradation

# ⚠️ CUIDADO - Muy amplio
ret*         → retrograde, return, retribution, etc.
```

---

## 6. Búsquedas Combinadas con Filtros

### Búsqueda + Filtro de Creador

**En el visor web:**
1. Haz clic en el creador "AstroByMax" (se marca con fondo morado)
2. Escribe en el buscador: `eclipse`
3. **Resultado:** Solo posts de AstroByMax que mencionen "eclipse"

**Equivalente en API:**
```bash
curl "http://localhost:5001/api/search?q=eclipse&creator=astrobymax"
```

### Búsqueda + Filtro de Tipo de Contenido

**En el visor web:**
1. Haz clic en "With Videos" (icono de cámara)
2. Escribe: `tutorial`
3. **Resultado:** Solo posts con videos que mencionen "tutorial"

**Combinar múltiples filtros:**
1. Selecciona creador: "HOROI Project"
2. Activa "With Images"
3. Busca: `ancient astrology`
4. **Resultado:** Posts de HOROI Project con imágenes sobre astrología antigua

---

## 7. Búsquedas por Campo Específico

### Buscar solo en títulos

**Sistema futuro (PostgreSQL):**
```sql
-- Búsqueda solo en títulos
WHERE to_tsvector('english', title) @@ to_tsquery('english', 'eclipse')
```

**Workaround actual:**
- El sistema busca en todos los campos
- Fíjate en los badges para ver dónde coincidió
- Badge verde "📌 Title" = coincidió en el título

### Buscar solo en comentarios

**Sistema futuro:**
```sql
-- Búsqueda solo en comentarios
WHERE to_tsvector('english', comments_text) @@ to_tsquery('english', 'thanks')
```

**Ejemplo de uso:**
- Buscar posts donde los usuarios agradecen en comentarios
- "thank* OR great OR excellent" → Encuentra posts con comentarios positivos

### Buscar solo en subtítulos de videos

**Sistema futuro:**
```sql
-- Búsqueda solo en subtítulos
WHERE to_tsvector('english', subtitles_text) @@ to_tsquery('english', 'introduction')
```

**Ejemplo de uso:**
- Buscar videos donde se menciona algo específico en el audio
- "welcome back" → Encuentra videos que dicen "welcome back" en subtítulos

---

## 8. Trucos Avanzados

### 🎯 Buscar posts con máximo contenido sobre un tema
```
eclipse solar lunar total partial
```
**Truco:** Cuantas más palabras relacionadas, más alto el ranking
**Resultado:** Posts que mencionen muchos tipos de eclipses aparecen primero

### 🎯 Buscar errores tipográficos comunes
```
astrology OR astology OR astrologie
```
**Resultado:** Captura variaciones y errores de escritura

### 🎯 Buscar números y años
```
2024
```
**Resultado:** Posts que mencionen "2024"

**Combinar:**
```
predictions 2024 OR forecast 2024
```

### 🎯 Buscar símbolos astrológicos (si están como texto)
```
mars OR "♂" OR aries OR "♈"
```

### 🎯 Buscar grados y aspectos
```
"29 degrees" OR "0 degrees"
```

```
conjunction OR opposition OR trine OR square OR sextile
```

---

## 📋 Ejemplos Prácticos por Caso de Uso

### Caso 1: Investigación sobre eclipses
```
# Búsqueda completa
(eclipse OR eclipses) AND (solar OR lunar) NOT horoscope

# Filtra por creador académico
→ Selecciona "Ali A Olomi" o "HOROI Project"

# Refina por contenido con imágenes
→ Activa filtro "With Images"
```

### Caso 2: Encontrar tutoriales para principiantes
```
# Palabras clave
beginner* OR introduct* OR "getting started" OR basics OR fundamental*

# Filtra por videos
→ Activa filtro "With Videos"

# Ordena por creador preferido
→ Selecciona "AstroByMax" (más tutoriales)
```

### Caso 3: Buscar referencias históricas
```
# Términos históricos
ancient OR medieval OR renaissance OR historical OR "in antiquity"

# Filtra por creador especializado
→ Selecciona "HOROI Project" (especializado en historia)

# Refina con período específico
ancient AND (greek OR roman OR mesopotamia* OR babylon*)
```

### Caso 4: Encontrar contenido sobre un planeta específico
```
# Buscar Saturno
saturn* OR "♄" OR cronos

# Excluir contenido básico
saturn* NOT "saturn return" -basics

# Solo contenido avanzado
saturn* AND (advanced OR deep OR esoteric OR traditional)
```

### Caso 5: Buscar posts con alto engagement
```
# Busca tema popular
mercury retrograde

# Fíjate en el badge "💬 Comments"
→ Posts con muchos comentarios probablemente generaron discusión

# Usa tag filter
→ Muestra tags, selecciona los más populares
```

---

## 🚀 Próximas Funcionalidades (Post-Migración PostgreSQL)

### Búsqueda fuzzy (tolerancia a errores)
```
# Sistema futuro con pg_trgm
astrology  → También encuentra: astology, astrologgy, astrologiy
```

### Búsqueda ponderada por relevancia
```sql
-- Título pesa más que contenido
setweight(to_tsvector('english', title), 'A')  -- Peso máximo
setweight(to_tsvector('english', content), 'B')  -- Peso medio
setweight(to_tsvector('english', comments), 'D')  -- Peso mínimo
```

### Búsqueda de sinónimos automática
```
# Sistema futuro con thesaurus
planets → Expande automáticamente a: planets, planetary, celestial bodies
```

### Búsqueda de proximidad
```
# PostgreSQL con pg_trgm
"moon" NEAR "ritual"  → Encuentra "moon" cerca de "ritual" en el texto
```

---

## 📊 Entendiendo los Resultados

### Badges de Coincidencia

Cuando haces una búsqueda, cada resultado muestra badges de color:

| Badge | Significado | Color |
|-------|-------------|-------|
| 📌 Title | Encontrado en el título | Verde |
| 📄 Text | Encontrado en el contenido | Azul |
| 🏷️ Tags | Encontrado en los tags | Rojo |
| 💬 Comments | Encontrado en comentarios | Naranja |
| 🎬 Video | Encontrado en subtítulos | Púrpura |

**Truco:** Los resultados con badge "📌 Title" suelen ser más relevantes

### Ranking de Resultados

Los resultados se ordenan por **relevancia** usando BM25:

**Factores que aumentan relevancia:**
1. ✅ Palabra aparece en el **título**
2. ✅ Palabra aparece **múltiples veces**
3. ✅ Palabra es **rara** en el corpus (no común)
4. ✅ Post es más **corto** (concentración de término)

**Ejemplo:**
- Post A: "Eclipse" aparece 1 vez en un post de 5000 palabras
- Post B: "Eclipse" aparece 5 veces en un post de 500 palabras
- **Post B** tendrá mayor ranking

---

## 🛠️ Depuración de Búsquedas

### No encuentras nada? Prueba:

1. **Simplifica la búsqueda**
   ```
   # En vez de:
   "lunar eclipse in ancient mesopotamia"

   # Prueba:
   lunar eclipse mesopotamia
   ```

2. **Usa prefijos**
   ```
   # En vez de:
   astrology

   # Prueba:
   astrol*  → Captura astrology, astrological, astrologer
   ```

3. **Quita palabras vacías (stop words)**
   ```
   # En vez de:
   the moon in astrology

   # Prueba:
   moon astrology
   ```

   Las palabras "the", "in", "a", "an", etc. se ignoran automáticamente.

4. **Usa sinónimos**
   ```
   # En vez de solo:
   planet

   # Prueba:
   planet* OR celestial OR "heavenly body"
   ```

---

## 💡 Tips Pro

### 1. Construye queries incrementalmente
```
# Paso 1: Tema general
astrology

# Paso 2: Refina
astrology natal

# Paso 3: Especializa
astrology natal chart interpretation

# Paso 4: Excluye ruido
astrology natal chart interpretation -horoscope
```

### 2. Usa el contador de resultados
```
# Si obtienes demasiados resultados (500+)
→ Agrega más términos específicos

# Si obtienes muy pocos resultados (< 5)
→ Simplifica o usa prefijos (astrol*)
```

### 3. Combina búsqueda con navegación
```
1. Busca tema general: "eclipse"
2. Mira los tags que aparecen en resultados
3. Click en tag relevante para filtrar más
4. Refina búsqueda: "eclipse solar"
```

### 4. Usa filtros de creador para descubrir contenido
```
1. No estás seguro qué buscar en HOROI Project?
2. Click en "HOROI Project" (sin búsqueda)
3. Explora los tags más comunes
4. Busca por esos tags
```

---

## 📖 Glosario de Operadores

| Operador | SQLite FTS5 | PostgreSQL FTS | Descripción |
|----------|-------------|----------------|-------------|
| AND | (espacio) | `&` | Todas las palabras |
| OR | `OR` | `\|` | Al menos una palabra |
| NOT | `-palabra` | `!palabra` | Excluir palabra |
| Phrase | `"frase exacta"` | `"frase exacta"` | Frase exacta |
| Prefix | `palabra*` | `palabra:*` | Buscar por prefijo |
| Proximity | ❌ | `palabra <-> palabra` | Palabras cercanas |
| Parenthesis | `(a OR b)` | `(a \| b)` | Agrupar operadores |

---

## 🎓 Ejercicios Prácticos

### Ejercicio 1: Busca posts sobre retrogradación
```
# Tu respuesta:
retrograd*

# Mejora:
retrograd* AND (mercury OR venus OR mars)

# Pro:
retrograd* AND planet* NOT horoscope
```

### Ejercicio 2: Posts sobre rituales lunares
```
# Tu respuesta:
moon ritual

# Mejora:
(moon OR lunar) AND (ritual OR ceremony OR practice)

# Pro:
"moon ritual" OR "lunar ritual" OR "full moon ceremony"
```

### Ejercicio 3: Contenido avanzado sobre casas
```
# Tu respuesta:
houses astrology

# Mejora:
houses AND astrology AND (advanced OR deep OR traditional)

# Pro:
(houses OR "house system*") AND astrology NOT beginner* -introduction
```

---

## 📚 Recursos Adicionales

- **SQLite FTS5**: https://www.sqlite.org/fts5.html
- **PostgreSQL Full-Text Search**: https://www.postgresql.org/docs/current/textsearch.html
- **BM25 Algorithm**: https://en.wikipedia.org/wiki/Okapi_BM25

---

**Última actualización**: 2025-11-08
**Autor**: Javi + Claude
**Versión**: 1.0
