# ELVIR DESIGN.md

Este archivo es el contrato de diseño de ELVIR. Debe usarse al crear o ajustar pantallas frontend.

El producto no es un dashboard SaaS genérico. Es una plataforma de empleabilidad guiada, usada en un contexto sensible: prácticas de entrevista para jóvenes, seguimiento de tutores y supervisión administrativa. La interfaz debe sentirse calma, competente, cálida y estructurada.

Usa como base los tokens ya definidos en `code/frontend/src/styles.scss`. No crees un sistema paralelo salvo que el cambio reemplace explícitamente el actual.

## 1. Tema Visual y Atmósfera

### Tono del producto
- Calmo, cálido y preciso.
- Confiable, sin verse clínico ni burocrático.
- Digital y moderno, pero no como una app startup genérica.
- Acompañado en flujos de jóvenes.
- Más controlado y operativo en vistas de tutor y admin.

### Dirección visual
- El modo claro debe sentirse como papel suave y superficies limpias: blancos cálidos, paneles suaves, bordes sutiles.
- El modo oscuro debe sentirse deliberado y ordenado: superficies grafito, contraste moderado, jerarquía clara, sin caer en negro puro con acentos chillones.
- El rojo Teletón es un acento, no el fondo dominante del sistema.
- La personalidad visual debe venir de jerarquía, espaciado, tipografía y composición; no de meter gradientes o adornos en todas partes.

### Mezcla de referencias
- `elevenlabs`: superficies premium y limpias, formularios refinados, modo claro suave.
- `linear.app`: disciplina visual, dark mode sólido, jerarquía de paneles.
- `claude`: calidez, legibilidad y confianza.

No copiar literalmente una sola marca. Sintetizar esas cualidades para una identidad propia de ELVIR.

## 2. Paleta de Color y Roles

### Tokens existentes
Prioriza estos tokens antes de agregar otros:

#### Núcleo
- `--color-primary`
- `--color-primary-hover`
- `--color-primary-light`
- `--color-primary-soft-*`

#### Estados
- `--color-accent`
- `--color-success`
- `--color-warning`
- `--color-danger`
- `--color-info`
- `--color-purple`

#### Superficies
- `--color-bg`
- `--color-card`
- `--color-surface`
- `--color-surface-alt`
- `--color-sidebar`
- `--color-sidebar-deep`

#### Texto y bordes
- `--color-text`
- `--color-text-muted`
- `--color-border`
- `--color-input-border`
- `--color-input-bg`
- `--color-input-focus`

### Comportamiento del color
- `--color-bg`: fondo general de página.
- `--color-surface`: contenedor principal.
- `--color-surface-alt`: contenedor secundario, tabs, filtros, bloques auxiliares.
- `--color-border`: borde estándar; visible pero suave.
- `--color-primary`: acciones principales, estado activo, foco, selección.
- Los colores de estado deben usarse solo con sentido semántico real.

### Tono del modo claro
- Fondo marfil suave, cards blancas, superficies secundarias gris muy claro frío.
- El rojo debe leerse como un acento intencional, no como ruido visual.

### Tono del modo oscuro
- Fondo carbón oscuro, paneles levemente elevados, no negro puro.
- La jerarquía se construye con superficies y bordes, no solo con sombras.
- Los acentos activos deben seguir vivos, pero controlados.

### No hacer
- No llenar páginas completas de rojo.
- No usar blanco plano en todo.
- No usar púrpura como adorno arbitrario.
- No inventar colores locales que rompan el sistema.

## 3. Reglas Tipográficas

### Familias
- Títulos: `Space Grotesk`
- Texto e interfaz: `Source Sans 3`

Tokens existentes:
- `--font-display`
- `--font-body`

### Jerarquía
- Título de página: fuerte, compacto, seguro.
- Título de sección: menor que el título de página, pero claro.
- Eyebrow / kicker: mayúsculas, espaciado leve, bajo contraste.
- Texto base: fácil de escanear, no demasiado grande.
- Microcopy: corto y discreto.

### Tono del copy
- Usar español simple.
- Preferir frases cortas y directas.
- Evitar lenguaje corporativo vacío o tono de asistente IA.
- Los botones deben ser decisivos:
  - `Crear joven`
  - `Iniciar entrevista supervisada`
  - `Registrar retroalimentación`
- Los textos de ayuda idealmente deben ocupar una línea.

### Comportamiento tipográfico
- Los títulos usan tipografía display.
- Controles, tablas, labels y ayuda usan la tipografía de cuerpo.
- No abusar de mayúsculas; reservarlas para metadata y categorías.

## 4. Estilo de Componentes

### Sidebar
- La sidebar es navegación, no un elemento hero.
- Debe sentirse compacta, calma y estable.
- La tarjeta del usuario puede existir, pero no debe dominar el primer viewport.
- El control de colapsar/expandir debe estar en un lugar predecible y nunca montarse sobre el contenido.
- El estado activo debe ser claro y elegante: relleno suave + acento sutil, no un bloque pesado o estridente.

### Header superior / cabecera de página
- Las cabeceras deben ser compactas y útiles.
- Evitar desperdiciar altura con topbars infladas.
- Un título fuerte, una línea de apoyo corta y acciones alineadas.
- No apilar contenedores decorativos si no aportan información real.

### Cards
- Son el bloque principal del layout.
- Bordes suaves y sombras moderadas.
- Priorizar un contenedor claro antes que cajas dentro de cajas sin jerarquía.
- El espaciado interno debe ser consistente.

### Botones
- Primario: sólido y claro.
- Secundario: superficie + borde.
- Ghost: solo para acciones terciarias.
- Altura consistente entre botones.
- Evitar pills gigantes salvo en acciones principales muy justificadas.

### Inputs
- Deben sentirse neutrales y estables.
- Fondo de superficie, borde claro y foco visible.
- Labels sobre el input, no placeholder como label.
- Las barras de búsqueda y filtros deben verse más sobrias que un CTA.

### Chips y badges
- Pequeños y legibles.
- Los chips de estado deben ser realmente semánticos.
- Los filtros pueden usar fondos suaves con estado activo claro.

### Tabs
- No deben generar saltos de layout.
- El rail de tabs debe permanecer fijo al cambiar.
- El estado activo puede resolverse con superficie destacada o acento sutil, no con un rediseño completo que desplace la pantalla.

### Tablas y listas
- Las vistas de tutor/admin pueden ser densas, pero ordenadas.
- Encabezados sobrios, filas legibles, acciones alineadas.
- Preferir agrupación y aire antes que líneas duras por todas partes.
- Evitar scroll horizontal en flujos principales.

### Stepper / flujos guiados
- El progreso debe sentirse corto y claro.
- No agregar pasos artificiales.
- Autoavanzar cuando la intención ya quedó resuelta.
- Mostrar siempre el contexto elegido después de seleccionarlo.

### Empty states
- Calmos, factuales y de bajo dramatismo.
- Una frase breve.
- Una acción siguiente clara, si corresponde.

### Alertas y feedback
- Usarlas con moderación.
- Los errores deben ser explícitos y simples.
- El éxito no debe ser celebratorio; debe sentirse claro y resuelto.

## 5. Principios de Layout

### Ancho y ritmo
- Mantener el ancho máximo actual:
  - `--content-max-width: 1200px`
- Contenido centrado, con fuerte alineación a la izquierda internamente.
- Mantener padding consistente:
  - `--content-padding`
  - `--content-padding-desktop`
- Usar sobre todo:
  - `--space-4`
  - `--space-6`
  - `--space-8`

### Comportamiento del layout
- Cada página debe tener un propósito dominante claro.
- Agrupar contenido relacionado en secciones reconocibles.
- Evitar apilar demasiadas cards visualmente iguales sin jerarquía.
- La asimetría se puede usar, pero la estructura general debe sentirse estable.

### Composición según el área
- Jóvenes: más simple, más guiado, más aire.
- Tutor: más operativo y denso, pero limpio.
- Admin: el más denso, pero extremadamente ordenado.

## 6. Profundidad y Elevación

### Modelo de elevación
- Primero bordes, después sombras.
- Modo claro:
  - sombras bajas o medias
  - las cards deben sentirse levemente elevadas, no flotando
- Modo oscuro:
  - usar contraste entre superficies y bordes más que sombras dramáticas

### Tokens existentes
- `--shadow-sm`
- `--shadow-md`
- `--shadow-lg`

Usarlos consistentemente. No meter sombras improvisadas sin necesidad real.

## 7. Lo que Sí y lo que No

### Sí
- Reusar el sistema de tokens actual.
- Mantener títulos compactos y con intención.
- Hacer visible el estado activo sin ruido.
- Reducir contenedores y acciones redundantes.
- Usar microcopy corto.
- Hacer visible la accesibilidad y comprensión desde la estructura.
- Diseñar dark mode como un sistema real, no como inversión de colores.

### No
- No volver a un dashboard genérico blanco.
- No abusar de rojos, pills gigantes o bordes pesados.
- No superponer controles de navegación sobre la identidad del usuario o el contenido.
- No permitir cambios de layout laterales al cambiar tabs o subpantallas.
- No inflar padding en todas las secciones.
- No usar copy “amable” que termine siendo vago o infantil.
- No usar gradientes decorativos como sustituto de estructura.

## 8. Comportamiento Responsive

### General
- En mobile debe sentirse diseñado, no comprimido.
- Colapsar complejidad, no significado.
- Mantener prioridad clara de tareas en todos los breakpoints.

### Reglas mobile
- La sidebar colapsada debe seguir siendo entendible.
- La identidad del usuario debe permanecer visible, pero reducida.
- Los filtros deben apilar bien.
- Las acciones pueden wrappear, pero con jerarquía clara.
- Evitar scroll horizontal en flujos principales.

### Reglas tablet / desktop
- Usar grid cuando mejore escaneo.
- Mantener estable la columna principal entre tabs o pantallas hermanas.
- Evitar que un componente cambie tanto de ancho que parezca mover toda la página.

### Touch targets
- Respetar `--touch-target-min`.
- Los iconos pequeños deben seguir siendo cómodos de tocar.

## 9. Guía para Agentes

Cuando se cree o ajuste UI de ELVIR:

- Reusar los tokens ya definidos en `code/frontend/src/styles.scss`.
- Usar `Space Grotesk` para títulos y `Source Sans 3` para texto de interfaz.
- Mantener páginas calmas, estructuradas y ligeramente premium.
- Tratar el rojo Teletón como acento controlado.
- Preferir superficies claras cálidas y paneles oscuros disciplinados.
- Reducir patrones de dashboard genérico.
- Eliminar pasos redundantes cuando la intención del usuario ya está clara.
- No dejar que la navegación o el chrome consuman altura innecesaria.
- Hacer las interfaces de tutor/admin más densas que las de jóvenes, pero nunca confusas.
- Mantener coherencia entre light y dark mode en jerarquía, no solo en color.
- Si una pantalla se siente como plantilla, detenerse y tomar una decisión visual más fuerte: mejor agrupación, mejor jerarquía, acciones mejor ubicadas o espaciado más intencional.

### Guía por tipo de pantalla

#### Dashboard
- Título fuerte, apoyo breve, fila de KPIs compacta.
- Uno o dos anclajes visuales claros; no una muralla de cards iguales.

#### Entrevistas / historial
- Priorizar velocidad de lectura.
- Fecha, estado y acción deben poder leerse en una pasada.

#### Perfiles
- El resumen superior y la barra de tabs deben mantenerse estables.
- Cambiar de tab no debe mover lateralmente la página.

#### Simulación / sala previa
- Dar sensación de avance claro y breve.
- Reducir confirmaciones redundantes.
- Mostrar cargo y escenario elegidos después de seleccionarlos.

#### Formularios
- Ayuda breve.
- Agrupar campos por tarea, no por forma de la base de datos.

## Nota de implementación

Este archivo no reemplaza los tokens actuales. Es un marco de decisión.

Al implementar cambios:

1. Priorizar ajustes sobre el sistema existente.
2. Mantener consistencia entre áreas de joven, tutor y admin.
3. Si una decisión nueva mejora claridad pero choca con el código actual, cambiar el código de forma deliberada; no apilar excepciones incoherentes.
