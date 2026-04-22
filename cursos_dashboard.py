"""
Dashboard: Rendimiento del Curso
Página para invocar desde el archivo maestro de Streamlit.
Conexión a MongoDB via st.secrets["mongo"]["uri"]
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# ─────────────────────────────────────────────
#  CONEXIÓN Y CARGA DE DATOS
# ─────────────────────────────────────────────

@st.cache_resource
def get_client():
    uri = st.secrets["mongo"]["uri"]
    return MongoClient(uri)

@st.cache_data(ttl=300)
def load_data():
    client = get_client()
    db_name = st.secrets["mongo"].get("db", "universidad_horizonte")
    db = client[db_name]
    students     = pd.DataFrame(list(db.students.find({}, {"_id": 0})))
    enrollments  = pd.DataFrame(list(db.enrollments.find({}, {"_id": 0})))
    courses      = pd.DataFrame(list(db.courses.find({}, {"_id": 0})))
    return students, enrollments, courses

# ─────────────────────────────────────────────
#  PALETA Y CSS
# ─────────────────────────────────────────────

COLOR_PRIMARY = "#E63946"
COLOR_WARNING = "#F4A261"
COLOR_SUCCESS = "#2A9D8F"
COLOR_INFO    = "#457B9D"
COLOR_PURPLE  = "#9B5DE5"
COLOR_GOLD    = "#FFD166"
PLOTLY_TPL    = "plotly_dark"

CSS = """
<style>
.metric-card {
    background: linear-gradient(135deg, #16213E 0%, #0F3460 100%);
    border-radius: 12px; padding: 18px 20px; margin-bottom: 8px;
    border-left: 4px solid var(--card-color, #457B9D); position: relative; overflow: hidden;
}
.metric-card::after {
    content: ""; position: absolute; top: -20px; right: -20px;
    width: 80px; height: 80px; border-radius: 50%;
    background: var(--card-color, #457B9D); opacity: 0.06;
}
.metric-card .mc-label { font-size: 0.72rem; color: #8892a4; text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 6px; }
.metric-card .mc-value { font-size: 1.9rem; font-weight: 700; line-height: 1; margin-bottom: 4px; }
.metric-card .mc-delta { font-size: 0.78rem; color: #8892a4; }
.metric-card .mc-icon { position: absolute; top: 14px; right: 16px; font-size: 1.4rem; opacity: 0.5; }

.course-card {
    background: linear-gradient(135deg, #16213E 0%, #0F3460 100%);
    border-radius: 14px; padding: 24px 28px; border: 1px solid #2a2a4a;
    display: flex; align-items: center; gap: 20px; margin-bottom: 4px; height: 100%;
}
.course-avatar {
    width: 64px; height: 64px; border-radius: 50%; background: linear-gradient(135deg, #457B9D, #9B5DE5);
    display: flex; align-items: center; justify-content: center; font-size: 1.8rem; flex-shrink: 0;
}
.course-name { font-size: 1.3rem; font-weight: 700; color: #EAEAEA; margin: 0 0 4px 0; }
.course-id { font-size: 0.78rem; color: #6a7280; margin: 0 0 8px 0; font-family: monospace; }
.course-badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600; margin-right: 6px;
}

.section-title { font-size: 1.05rem; font-weight: 600; color: #EAEAEA; border-bottom: 2px solid #457B9D; padding-bottom: 6px; margin: 28px 0 16px 0; }

.data-table { width:100%; border-collapse: collapse; font-size:0.85rem; }
.data-table th { text-align: left; padding: 8px 12px; background: #16213E; color: #8892a4; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.07em; border-bottom: 1px solid #2a2a4a; }
.data-table td { padding: 10px 12px; color: #EAEAEA; border-bottom: 1px solid #1e2a3a; }
.data-table tr:hover td { background: rgba(69,123,157,0.08); }
.status-pill { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
</style>
"""

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def nav_bar(page_title: str, page_icon: str = "📄"):
    col_btn, col_bread = st.columns([1.2, 8])
    with col_btn:
        if st.button("⬅ Inicio", key=f"nav_back_{page_title}", use_container_width=True):
            st.session_state.active_page = "🏠  Inicio"
            st.rerun()
    with col_bread:
        st.markdown(
            f"<div style='line-height:1; padding:10px 0 0 4px;'>"
            f"<span style='font-size:0.78rem; color:#4a5568;'>🏠 Inicio &nbsp;›&nbsp;</span>"
            f"<span style='font-size:0.82rem; color:#EAEAEA; font-weight:600;'>{page_icon} {page_title}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("<hr style='border:none; border-top:1px solid #2a2a4a; margin:10px 0 20px 0;'>", unsafe_allow_html=True)

def _section(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

def _metric_card(label, value, delta="", color=COLOR_INFO, icon=""):
    st.markdown(f"""
    <div class="metric-card" style="--card-color:{color}; border-left-color:{color};">
        <div class="mc-icon">{icon}</div><div class="mc-label">{label}</div>
        <div class="mc-value" style="color:{color};">{value}</div><div class="mc-delta">{delta}</div>
    </div>""", unsafe_allow_html=True)

def _course_card(course: dict):
    name = course.get("name", "Nombre de Curso")
    cid = course.get("course_id", "—")
    dept = course.get("department", "General")
    modality = course.get("modality", "Híbrido")
    st.markdown(f"""
    <div class="course-card">
        <div class="course-avatar">📚</div>
        <div style="flex:1;">
            <div class="course-name">{name}</div><div class="course-id">Código: {cid}</div>
            <span class="course-badge" style="background:rgba(69,123,157,0.2); color:{COLOR_INFO}; border:1px solid {COLOR_INFO};">🏢 {dept}</span>
            <span class="course-badge" style="background:rgba(155,93,229,0.15); color:{COLOR_PURPLE}; border:1px solid {COLOR_PURPLE};">💻 {modality}</span>
        </div>
    </div>""", unsafe_allow_html=True)

def _students_table(df: pd.DataFrame):
    rows_html = ""
    for _, row in df.iterrows():
        nota = row.get("final_grade", 0)
        asistencia = row.get("attendance_rate", 0) * 100
        
        color_nota = COLOR_SUCCESS if nota >= 14 else (COLOR_WARNING if nota >= 11 else COLOR_PRIMARY)
        icon_nota = "✅" if nota >= 11 else "🔴"
        color_asist = COLOR_SUCCESS if asistencia >= 75 else (COLOR_WARNING if asistencia >= 60 else COLOR_PRIMARY)
        
        rows_html += f"""
        <tr>
            <td style="font-family:monospace; color:#8892a4;">{row.get('student_id', '')}</td>
            <td style="font-weight:500;">{row.get('Student Name', '')}</td>
            <td>{row.get('term', '')}</td>
            <td><span class="status-pill" style="background:rgba(0,0,0,0.3); color:{color_nota}; border:1px solid {color_nota};">{icon_nota} {nota:.1f}</span></td>
            <td><span style="color:{color_asist}; font-weight:600;">{asistencia:.1f}%</span></td>
        </tr>"""

    st.markdown(f"""
    <table class="data-table">
        <thead>
            <tr><th>ID Estudiante</th><th>Nombre Completo</th><th>Ciclo</th><th>Nota Final</th><th>Asistencia</th></tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────

def show():
    st.markdown(CSS, unsafe_allow_html=True)
    nav_bar("Análisis de Rendimiento por Curso", "📚")

    st.markdown("""
    <div style="background:linear-gradient(90deg,#457B9D,#9B5DE5); border-radius:12px; padding:20px 28px; margin-bottom:20px;">
        <h1 style="color:white; margin:0; font-size:1.8rem;">📚 Rendimiento por Curso</h1>
        <p style="color:#dde; margin:4px 0 0 0; font-size:0.9rem;">Evalúa el desempeño general, asistencia y distribución de notas.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Cargando datos..."):
        try:
            students, enrollments, courses = load_data()
        except Exception as e:
            st.error("❌ Error al conectar con MongoDB. Verifica tus secretos.")
            return

    lista_cursos = courses["course_id"].tolist()
    if not lista_cursos:
        st.warning("No se encontraron cursos.")
        return

    dict_cursos = {row["course_id"]: f"{row['course_id']} - {row['name']}" for _, row in courses.iterrows()}
    
    sel_course = st.selectbox(
        "🔎 Buscar curso",
        options=lista_cursos,
        format_func=lambda x: dict_cursos.get(x, x),
        key="course_selector"
    )
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    course_row = courses[courses["course_id"] == sel_course].iloc[0].to_dict()
    enr_course = enrollments[enrollments["course_id"] == sel_course].copy()
    enr_course['final_grade'] = pd.to_numeric(enr_course['final_grade'], errors='coerce')

    # ════════════════════════════════════════
    #  SECCIÓN 1 · INFO Y FILTROS (BOX CORREGIDO)
    # ════════════════════════════════════════
    col_info, col_filters = st.columns([1, 1.5])
    
    with col_info:
        _course_card(course_row)

    with col_filters:
        # CORRECCIÓN 1: Usamos st.container nativo para el Box
        with st.container(border=True):
            st.markdown("<span style='font-size:0.85rem; color:#8892a4; text-transform:uppercase; font-weight:bold;'>FILTROS DE ANÁLISIS</span>", unsafe_allow_html=True)
            f1, f2 = st.columns(2)
            with f1:
                ciclos_disp = enr_course['term'].dropna().unique().tolist()
                ciclos_sel = st.multiselect("Ciclo(s)", options=ciclos_disp, default=ciclos_disp)
            with f2:
                tipo_filtro = st.selectbox("Condición Nota", ["Todas", ">= Mínima", "<= Máxima", "Rango"])
                
            if tipo_filtro == ">= Mínima":
                val_min = st.number_input("Nota mínima", 0, 20, 11)
            elif tipo_filtro == "<= Máxima":
                val_max = st.number_input("Nota máxima", 0, 20, 10)
            elif tipo_filtro == "Rango":
                val_rango = st.slider("Rango", 0, 20, (10, 15))

    # Aplicar Filtros
    df_filtered = enr_course[enr_course['term'].isin(ciclos_sel)].copy()
    if tipo_filtro == ">= Mínima":
        df_filtered = df_filtered[df_filtered['final_grade'] >= val_min]
    elif tipo_filtro == "<= Máxima":
        df_filtered = df_filtered[df_filtered['final_grade'] <= val_max]
    elif tipo_filtro == "Rango":
        df_filtered = df_filtered[(df_filtered['final_grade'] >= val_rango[0]) & (df_filtered['final_grade'] <= val_rango[1])]

    if df_filtered.empty:
        st.warning("⚠️ No hay estudiantes que coincidan con los filtros aplicados.")
        return

    # ════════════════════════════════════════
    #  SECCIÓN 2 · KPIs
    # ════════════════════════════════════════
    _section("📊 Rendimiento del Segmento")
    
    total_alumnos = len(df_filtered)
    promedio = df_filtered['final_grade'].mean()
    asistencia = df_filtered['attendance_rate'].mean() * 100
    aprobados = len(df_filtered[df_filtered['final_grade'] >= 11])
    tasa_aprob = (aprobados / total_alumnos) * 100 if total_alumnos > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    with k1: _metric_card("Matriculados", str(total_alumnos), delta="Filtrados", icon="👥")
    with k2:
        c_prom = COLOR_SUCCESS if promedio >= 14 else (COLOR_WARNING if promedio >= 11 else COLOR_PRIMARY)
        _metric_card("Promedio de Notas", f"{promedio:.1f} / 20" if pd.notna(promedio) else "N/A", color=c_prom, icon="📈")
    with k3:
        c_tasa = COLOR_SUCCESS if tasa_aprob >= 70 else (COLOR_WARNING if tasa_aprob >= 50 else COLOR_PRIMARY)
        _metric_card("Tasa de Aprobación", f"{tasa_aprob:.1f}%", color=c_tasa, icon="🎓")
    with k4:
        c_asist = COLOR_SUCCESS if asistencia >= 75 else COLOR_WARNING
        _metric_card("Asistencia", f"{asistencia:.1f}%" if pd.notna(asistencia) else "N/A", color=c_asist, icon="📅")

    # ════════════════════════════════════════
    #  SECCIÓN 3 · GRÁFICOS
    # ════════════════════════════════════════
    _section("📈 Análisis Visual")
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig_dist = px.histogram(
            df_filtered, x="final_grade", nbins=10, color_discrete_sequence=[COLOR_INFO],
            labels={'final_grade': 'Nota Final', 'count': 'Frecuencia'}, template=PLOTLY_TPL
        )
        fig_dist.add_vline(x=11, line_dash="dash", line_color=COLOR_GOLD, line_width=2, annotation_text="Aprobación (11)", annotation_font=dict(color=COLOR_GOLD, size=11))
        fig_dist.update_layout(title="Distribución de Calificaciones", title_font_size=15, height=360, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=50, b=40, l=20, r=20))
        st.plotly_chart(fig_dist, use_container_width=True)

    with col_g2:
        fig_scat = px.scatter(
            df_filtered, x="attendance_rate", y="final_grade", hover_data=['student_id'],
            color='final_grade', color_continuous_scale="Teal",
            labels={'attendance_rate': 'Tasa de Asistencia', 'final_grade': 'Nota Final'}, template=PLOTLY_TPL
        )
        fig_scat.update_layout(title="Relación: Asistencia vs Rendimiento", title_font_size=15, height=360, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis_tickformat='%', margin=dict(t=50, b=40, l=20, r=20))
        fig_scat.add_hline(y=11, line_dash="dot", line_color=COLOR_PRIMARY)
        st.plotly_chart(fig_scat, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 4 · DETALLE Y PAGINACIÓN
    # ════════════════════════════════════════
    _section("🧑‍🎓 Listado de Estudiantes")
    
    df_detail = df_filtered.merge(students[['student_id', 'first_name', 'last_name']], on="student_id", how="left")
    df_detail['Student Name'] = df_detail['first_name'] + " " + df_detail['last_name']
    df_detail = df_detail.sort_values(by="final_grade", ascending=False)
    
    # CORRECCIÓN 2: Lógica de Paginación Manual (50 por página)
    ITEMS_PER_PAGE = 50
    total_items = len(df_detail)
    total_pages = max(1, (total_items - 1) // ITEMS_PER_PAGE + 1)

    # Inicializar o validar la página actual en session_state
    if "curso_page" not in st.session_state:
        st.session_state.curso_page = 1
    
    # Si los filtros cambian drásticamente y la página actual excede el límite, reiniciar
    if st.session_state.curso_page > total_pages:
        st.session_state.curso_page = 1

    # Extraer el bloque (slice) de 50 registros correspondiente a la página actual
    start_idx = (st.session_state.curso_page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    df_page = df_detail.iloc[start_idx:end_idx]
    
    # Mostrar la tabla HTML solo con esos 50 estudiantes
    _students_table(df_page)

    # Controles de paginación (Solo aparecen si hay más de 1 página)
    if total_pages > 1:
        st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
        col_btn1, col_lbl, col_btn2 = st.columns([1, 2, 1])
        
        with col_btn1:
            if st.button("⬅ Anterior", disabled=(st.session_state.curso_page == 1), use_container_width=True):
                st.session_state.curso_page -= 1
                st.rerun()
                
        with col_lbl:
            st.markdown(f"<div style='text-align:center; padding-top:8px; color:#8892a4; font-weight:bold;'>Página {st.session_state.curso_page} de {total_pages} ({total_items} registros)</div>", unsafe_allow_html=True)
            
        with col_btn2:
            if st.button("Siguiente ➡", disabled=(st.session_state.curso_page == total_pages), use_container_width=True):
                st.session_state.curso_page += 1
                st.rerun()

# ─────────────────────────────────────────────
#  EJECUCIÓN STANDALONE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(page_title="Rendimiento del Curso", page_icon="📚", layout="wide")
    if "active_page" not in st.session_state:
        st.session_state.active_page = "📚  Cursos"
    show()