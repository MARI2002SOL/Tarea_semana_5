# # app_maestro.py
# import general
# import streamlit as st

# page = st.navigation({
#     "Dashboards": [
#         st.Page(general.show, title="Deserción", icon="📉"),
#         # ... otros pages
#     ]
# })
# page.run()
"""
app_maestro.py  ·  v2
Archivo principal de la aplicación Streamlit.
Gestiona la navegación entre dashboards desde el menú lateral.

Cada dashboard:
  - Expone una función show()
  - Llama a nav_bar() al inicio para renderizar el botón "← Inicio"
  - Maneja sus propios filtros internamente (sin usar st.sidebar)
"""

import streamlit as st

# ─────────────────────────────────────────────
#  CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Analítica Académica",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  IMPORTAR DASHBOARDS
#  Para agregar uno nuevo:
#    1. Crea el archivo con función show() y llama nav_bar() al inicio
#    2. Impórtalo aquí
#    3. Agrégalo al diccionario MENU
# ─────────────────────────────────────────────

import desercion_dashboard
import perfil360_dashboard
import cursos_dashboard
# import rendimiento_dashboard
# import pagos_dashboard
# import engagement_dashboard


# ─────────────────────────────────────────────
#  MENÚ: { "Categoría": [(icono, label, módulo)] }
# ─────────────────────────────────────────────

MENU = {
    "📊 Analítica Estudiantil": [
        ("📉", "Deserción Estudiantil",   desercion_dashboard),
        ("🧑‍🎓", "Perfil 360° del Estudiante", perfil360_dashboard),
        ("📈", "Cursos", cursos_dashboard),
    ],
    # "💳 Gestión Financiera": [
    #     ("💰", "Pagos y Morosidad", pagos_dashboard),
    # ],
    # "💻 Plataforma LMS": [
    #     ("🖥️", "Engagement Digital", engagement_dashboard),
    # ],
}

# Descripciones para las tarjetas de la pantalla de inicio
CARD_DESC = {
    "Deserción Estudiantil": (
        "Monitorea tasas de deserción, motivos académicos y financieros, "
        "alertas tempranas y engagement en el LMS.",
        "#E63946",
    ),
    "Perfil 360° del Estudiante": (
        "Vista integral por estudiante: notas, asistencia, pagos, "
        "actividad LMS y alertas de riesgo personalizadas.",
        "#9B5DE5",
    ),
    "Cursos dashboard": (
        "Enfocado en evaluar el desempeño general, la asistencia "
        "y la distribución de notas por asignatura mediante filtros interactivos.",
        "#9B5DE5",
    ),
    # "Rendimiento Académico": ("Análisis de notas y aprobación por curso.", "#457B9D"),
}

HOME_KEY = "🏠  Inicio"


# ─────────────────────────────────────────────
#  ESTILOS GLOBALES
# ─────────────────────────────────────────────

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0F0F1A; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1A1A2E 0%, #16213E 100%);
        border-right: 1px solid #2a2a4a;
    }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  ESTADO DE SESIÓN
# ─────────────────────────────────────────────

if "active_page" not in st.session_state:
    st.session_state.active_page = HOME_KEY


# ─────────────────────────────────────────────
#  SIDEBAR — menú de navegación principal
# ─────────────────────────────────────────────

with st.sidebar:

    # — Logo —
    st.markdown("""
    <div style="padding:16px 8px 20px 8px; text-align:center;">
        <div style="font-size:2.4rem;">🎓</div>
        <div style="font-size:1rem; font-weight:700; color:#EAEAEA; line-height:1.3;">
            Analítica<br>Académica
        </div>
        <div style="font-size:0.72rem; color:#6a7280; margin-top:4px;">
            Ingeniería de Software
        </div>
    </div>
    <hr style="border-color:#2a2a4a; margin:0 0 12px 0;">
    """, unsafe_allow_html=True)

    # — Botón Inicio —
    is_home = st.session_state.active_page == HOME_KEY
    if st.button(
        HOME_KEY,
        key="nav_home",
        use_container_width=True,
        type="primary" if is_home else "secondary",
    ):
        st.session_state.active_page = HOME_KEY
        st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # — Categorías y dashboards —
    for category, pages in MENU.items():
        st.markdown(
            f"<div style='font-size:0.68rem; color:#4a5568; text-transform:uppercase; "
            f"letter-spacing:0.1em; padding:12px 4px 4px 4px;'>{category}</div>",
            unsafe_allow_html=True,
        )
        for icon, label, _ in pages:
            full_label = f"{icon}  {label}"
            is_active  = st.session_state.active_page == full_label
            if st.button(
                full_label,
                key=f"nav_{label}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.active_page = full_label
                st.rerun()

    # — Footer sidebar —
    st.markdown("""
    <div style="position:absolute; bottom:16px; left:0; right:0;
                text-align:center; font-size:0.68rem; color:#4a5568; padding:0 12px;">
        v2.0 · Streamlit + MongoDB + Plotly
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  MAPA PLANO: full_label → módulo
# ─────────────────────────────────────────────

PAGE_MAP = {
    f"{icon}  {label}": module
    for pages in MENU.values()
    for icon, label, module in pages
}


# ─────────────────────────────────────────────
#  ENRUTADOR
# ─────────────────────────────────────────────

active = st.session_state.active_page

# ── PANTALLA DE INICIO ────────────────────────────────────────────────────────
if active == HOME_KEY:

    st.markdown("""
    <div style="background:linear-gradient(135deg,#1A1A2E 0%,#16213E 60%,#0F3460 100%);
                border-radius:16px; padding:40px 48px; margin-bottom:32px;
                border:1px solid #2a2a4a;">
        <h1 style="color:#EAEAEA; font-size:2.2rem; margin:0 0 8px 0;">
            👋 Bienvenido al Sistema de la Universidad Nuevo Horizonte
        </h1>
        <p style="color:#8892a4; font-size:1rem; margin:0;">
            Selecciona un dashboard en las tarjetas de acceso rápido.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # — Tarjetas de acceso rápido —
    st.markdown(
        "<h3 style='color:#EAEAEA; font-size:1rem; margin-bottom:16px;'>🚀 Acceso Rápido</h3>",
        unsafe_allow_html=True,
    )

    all_pages = [
        (icon, label, mod)
        for pages in MENU.values()
        for icon, label, mod in pages
    ]
    cols = st.columns(min(len(all_pages), 3))

    for col, (icon, label, _) in zip(cols, all_pages):
        desc, color = CARD_DESC.get(label, ("Dashboard disponible.", "#457B9D"))
        full_label  = f"{icon}  {label}"
        with col:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#16213E,#1a2744);
                        border-radius:12px; padding:24px;
                        border-top:3px solid {color};
                        border-left:1px solid #2a2a4a;
                        border-right:1px solid #2a2a4a;
                        border-bottom:1px solid #2a2a4a;
                        min-height:170px; margin-bottom:8px;">
                <div style="font-size:2rem; margin-bottom:8px;">{icon}</div>
                <div style="font-size:1rem; font-weight:600; color:#EAEAEA;
                            margin-bottom:8px;">{label}</div>
                <div style="font-size:0.82rem; color:#8892a4; line-height:1.5;">
                    {desc}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Abrir {label} →", key=f"home_open_{label}",
                         use_container_width=True):
                st.session_state.active_page = full_label
                st.rerun()

    # — Métricas del sistema —
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<h3 style='color:#EAEAEA; font-size:1rem; margin-bottom:12px;'>📋 Estado del Sistema</h3>",
        unsafe_allow_html=True,
    )
    i1, i3 = st.columns(2)
    with i1:
        st.metric("Dashboards activos",  sum(len(p) for p in MENU.values()))
    with i3:
        st.metric("Fuente de datos",     "MongoDB")

# ── DASHBOARD SELECCIONADO ────────────────────────────────────────────────────
elif active in PAGE_MAP:
    PAGE_MAP[active].show()

# ── FALLBACK ──────────────────────────────────────────────────────────────────
else:
    st.error(f"Página '{active}' no encontrada.")
    if st.button("← Volver al inicio"):
        st.session_state.active_page = HOME_KEY
        st.rerun()
