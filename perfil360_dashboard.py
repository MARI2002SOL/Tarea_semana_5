"""
Dashboard: Perfil 360° del Estudiante
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
    db_name = st.secrets["mongo"].get("db", "universidad")
    db = client[db_name]
    students     = pd.DataFrame(list(db.students.find({},      {"_id": 0})))
    enrollments  = pd.DataFrame(list(db.enrollments.find({},   {"_id": 0})))
    payments     = pd.DataFrame(list(db.payments.find({},      {"_id": 0})))
    interactions = pd.DataFrame(list(db.interactions.find({},  {"_id": 0})))
    dropout      = pd.DataFrame(list(db.dropout_flags.find({}, {"_id": 0})))
    courses      = pd.DataFrame(list(db.courses.find({},       {"_id": 0})))
    return students, enrollments, payments, interactions, dropout, courses


# ─────────────────────────────────────────────
#  PALETA
# ─────────────────────────────────────────────

COLOR_PRIMARY = "#E63946"
COLOR_WARNING = "#F4A261"
COLOR_SUCCESS = "#2A9D8F"
COLOR_INFO    = "#457B9D"
COLOR_PURPLE  = "#9B5DE5"
COLOR_GOLD    = "#FFD166"
PLOTLY_TPL    = "plotly_dark"

ACTION_COLORS = {
    "Login":              COLOR_INFO,
    "Ver Clase":          COLOR_SUCCESS,
    "Descargar Material": COLOR_PURPLE,
    "Entregar Tarea":     COLOR_GOLD,
    "Participar Foro":    COLOR_WARNING,
}

STATUS_COLORS = {
    "pagado":   COLOR_SUCCESS,
    "tardio":   COLOR_WARNING,
    "pendiente": COLOR_PRIMARY,
}
STATUS_ICONS = {
    "pagado":   "✅",
    "tardio":   "⚠️",
    "pendiente": "🔴",
}


# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────

CSS = """
<style>
/* ── Tarjetas métricas ── */
.metric-card {
    background: linear-gradient(135deg, #16213E 0%, #0F3460 100%);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 8px;
    border-left: 4px solid var(--card-color, #457B9D);
    position: relative;
    overflow: hidden;
}
.metric-card::after {
    content: "";
    position: absolute;
    top: -20px; right: -20px;
    width: 80px; height: 80px;
    border-radius: 50%;
    background: var(--card-color, #457B9D);
    opacity: 0.06;
}
.metric-card .mc-label {
    font-size: 0.72rem;
    color: #8892a4;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 6px;
}
.metric-card .mc-value {
    font-size: 1.9rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 4px;
}
.metric-card .mc-delta {
    font-size: 0.78rem;
    color: #8892a4;
}
.metric-card .mc-icon {
    position: absolute;
    top: 14px; right: 16px;
    font-size: 1.4rem;
    opacity: 0.5;
}

/* ── Perfil card ── */
.profile-card {
    background: linear-gradient(135deg, #16213E 0%, #0F3460 100%);
    border-radius: 14px;
    padding: 24px 28px;
    border: 1px solid #2a2a4a;
    display: flex;
    align-items: center;
    gap: 20px;
    margin-bottom: 4px;
}
.profile-avatar {
    width: 64px; height: 64px;
    border-radius: 50%;
    background: linear-gradient(135deg, #457B9D, #9B5DE5);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.8rem;
    flex-shrink: 0;
}
.profile-name {
    font-size: 1.3rem;
    font-weight: 700;
    color: #EAEAEA;
    margin: 0 0 4px 0;
}
.profile-id {
    font-size: 0.78rem;
    color: #6a7280;
    margin: 0 0 8px 0;
    font-family: monospace;
}
.profile-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 6px;
}

/* ── Alertas ── */
.alert-box {
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 4px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    border: 1px solid;
}
.alert-icon { font-size: 1.4rem; flex-shrink: 0; margin-top: 1px; }
.alert-title { font-size: 0.9rem; font-weight: 700; margin-bottom: 2px; }
.alert-body  { font-size: 0.82rem; opacity: 0.85; }

/* ── Título de sección ── */
.section-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #EAEAEA;
    border-bottom: 2px solid #457B9D;
    padding-bottom: 6px;
    margin: 28px 0 16px 0;
}

/* ── Tabla de pagos ── */
.pay-table { width:100%; border-collapse: collapse; font-size:0.85rem; }
.pay-table th {
    text-align: left;
    padding: 8px 12px;
    background: #16213E;
    color: #8892a4;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    border-bottom: 1px solid #2a2a4a;
}
.pay-table td {
    padding: 10px 12px;
    color: #EAEAEA;
    border-bottom: 1px solid #1e2a3a;
}
.pay-table tr:last-child td { border-bottom: none; }
.pay-table tr:hover td { background: rgba(69,123,157,0.08); }
.status-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}
</style>
"""


# ─────────────────────────────────────────────
#  NAV BAR — reutilizable (igual que en desercion_dashboard)
# ─────────────────────────────────────────────

def nav_bar(page_title: str, page_icon: str = "📄"):
    col_btn, col_bread = st.columns([1.2, 8])
    with col_btn:
        if st.button(
            "⬅ Inicio",
            key=f"nav_back_{page_title}",
            use_container_width=True,
            help="Regresar al menú principal",
        ):
            st.session_state.active_page = "🏠  Inicio"
            st.rerun()
    with col_bread:
        st.markdown(
            f"<div style='line-height:1; padding:10px 0 0 4px;'>"
            f"<span style='font-size:0.78rem; color:#4a5568;'>🏠 Inicio &nbsp;›&nbsp;</span>"
            f"<span style='font-size:0.82rem; color:#EAEAEA; font-weight:600;'>"
            f"{page_icon} {page_title}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        "<hr style='border:none; border-top:1px solid #2a2a4a; margin:10px 0 20px 0;'>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def _section(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def _metric_card(label, value, delta="", color=COLOR_INFO, icon=""):
    st.markdown(f"""
    <div class="metric-card" style="--card-color:{color}; border-left-color:{color};">
        <div class="mc-icon">{icon}</div>
        <div class="mc-label">{label}</div>
        <div class="mc-value" style="color:{color};">{value}</div>
        <div class="mc-delta">{delta}</div>
    </div>""", unsafe_allow_html=True)


def _alert(is_dropout: bool, reason: str = ""):
    if is_dropout:
        reason_label = {"academico": "Bajo rendimiento académico",
                        "financiero": "Dificultades financieras"}.get(reason, reason.capitalize())
        st.markdown(f"""
        <div class="alert-box"
             style="background:rgba(230,57,70,0.12); border-color:#E63946;">
            <div class="alert-icon">🚨</div>
            <div>
                <div class="alert-title" style="color:#E63946;">
                    Estudiante con riesgo de deserción detectado
                </div>
                <div class="alert-body" style="color:#f8a0a8;">
                    Motivo registrado: <strong>{reason_label}</strong> ·
                    Se recomienda intervención inmediata del equipo de consejería.
                </div>
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-box"
             style="background:rgba(42,157,143,0.12); border-color:#2A9D8F;">
            <div class="alert-icon">✅</div>
            <div>
                <div class="alert-title" style="color:#2A9D8F;">
                    Estudiante activo sin alertas de deserción
                </div>
                <div class="alert-body" style="color:#7ecfc8;">
                    No se han registrado señales de riesgo para este estudiante en los
                    ciclos evaluados.
                </div>
            </div>
        </div>""", unsafe_allow_html=True)


def _profile_card(student: dict, status_color: str, status_label: str,
                  program_color: str = COLOR_INFO):
    gender_icon = "👨‍🎓" if student.get("gender", "M") == "M" else "👩‍🎓"
    full_name   = f"{student['first_name']} {student['last_name']}"
    program     = student.get("program", "—")
    sid         = student.get("student_id", "—")
    created     = student.get("created_at", None)
    since_str   = ""
    if created:
        try:
            since_str = f"Registrado: {pd.to_datetime(created).strftime('%d/%m/%Y')}"
        except Exception:
            pass

    st.markdown(f"""
    <div class="profile-card">
        <div class="profile-avatar">{gender_icon}</div>
        <div style="flex:1;">
            <div class="profile-name">{full_name}</div>
            <div class="profile-id">ID: {sid} &nbsp;·&nbsp; {since_str}</div>
            <span class="profile-badge"
                  style="background:rgba(69,123,157,0.2); color:{program_color};
                         border:1px solid {program_color};">
                🎓 {program}
            </span>
            <span class="profile-badge"
                  style="background:rgba(42,157,143,0.15); color:{status_color};
                         border:1px solid {status_color};">
                {status_label}
            </span>
        </div>
    </div>""", unsafe_allow_html=True)


def _payment_table(pay_df: pd.DataFrame):
    rows_html = ""
    for _, row in pay_df.iterrows():
        status = str(row.get("status", "")).lower()
        color  = STATUS_COLORS.get(status, "#aab4be")
        icon   = STATUS_ICONS.get(status, "•")
        label  = status.capitalize()
        fecha  = ""
        try:
            fecha = pd.to_datetime(row["payment_date"]).strftime("%d/%m/%Y")
        except Exception:
            fecha = str(row.get("payment_date", "—"))
        monto  = f"S/ {row.get('amount', 0):,.0f}"
        ciclo  = row.get("term", "—")
        rows_html += f"""
        <tr>
            <td>{ciclo}</td>
            <td>{fecha}</td>
            <td style="font-weight:600;">{monto}</td>
            <td>
                <span class="status-pill"
                      style="background:rgba(0,0,0,0.3); color:{color};
                             border:1px solid {color};">
                    {icon} {label}
                </span>
            </td>
        </tr>"""

    st.markdown(f"""
    <table class="pay-table">
        <thead>
            <tr>
                <th>Ciclo</th>
                <th>Fecha de Pago</th>
                <th>Monto</th>
                <th>Estado</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────

def show():
    st.markdown(CSS, unsafe_allow_html=True)

    # ── NAV BAR ──────────────────────────────
    nav_bar("Perfil 360° del Estudiante", "🧑‍🎓")

    # ── HEADER ───────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(90deg,#457B9D,#9B5DE5);
                border-radius:12px; padding:20px 28px; margin-bottom:20px;">
        <h1 style="color:white; margin:0; font-size:1.8rem;">
            🧑‍🎓 Perfil 360° del Estudiante
        </h1>
        <p style="color:#dde; margin:4px 0 0 0; font-size:0.9rem;">
            Vista integral de rendimiento, pagos, actividad y riesgo · Ingeniería de Software
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── CARGA ────────────────────────────────
    with st.spinner("Cargando datos desde MongoDB..."):
        try:
            students, enrollments, payments, interactions, dropout, courses = load_data()
        except Exception as e:
            st.error(f"❌ Error al conectar con MongoDB: {e}")
            st.info("Verifica `st.secrets['mongo']['uri']` y `st.secrets['mongo']['db']`.")
            return

    # ── SELECTOR DE ESTUDIANTE ───────────────
    student_ids = sorted(students["student_id"].unique().tolist())
    sel_id = st.selectbox(
        "🔎 Seleccionar estudiante",
        student_ids,
        key="perfil_student_id",
        help="Busca por ID de estudiante",
    )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── DATOS DEL ESTUDIANTE SELECCIONADO ────
    stu_row = students[students["student_id"] == sel_id].iloc[0].to_dict()

    enr_stu  = enrollments[enrollments["student_id"] == sel_id].copy()
    pay_stu  = payments[payments["student_id"] == sel_id].copy()
    int_stu  = interactions[interactions["student_id"] == sel_id].copy()
    drop_stu = dropout[dropout["student_id"] == sel_id]

    is_dropout  = not drop_stu.empty and bool(drop_stu["dropout"].any())
    drop_reason = drop_stu[drop_stu["dropout"] == True]["reason"].values[0] \
                  if is_dropout else ""

    # KPI base
    enr_stu_courses = enr_stu.merge(courses, on="course_id", how="left")
    total_cursos    = enr_stu["course_id"].nunique()
    promedio_notas  = enr_stu["final_grade"].mean() if not enr_stu.empty else 0
    prom_asistencia = enr_stu["attendance_rate"].mean() * 100 if not enr_stu.empty else 0
    pagos_pendientes = pay_stu[pay_stu["status"].isin(["pendiente", "tardio"])].shape[0]

    status_raw   = str(stu_row.get("status", "activo")).lower()
    status_color = COLOR_SUCCESS if status_raw == "activo" else COLOR_PRIMARY
    status_label = f"● {status_raw.capitalize()}"

    # ════════════════════════════════════════
    #  SECCIÓN 1 · PERFIL + ALERTA
    # ════════════════════════════════════════
    _section("👤 Perfil del Estudiante")

    col_prof, col_alert = st.columns([1, 1])

    with col_prof:
        _profile_card(stu_row, status_color, status_label)

    with col_alert:
        _alert(is_dropout, drop_reason)

    # ════════════════════════════════════════
    #  SECCIÓN 2 · KPIs
    # ════════════════════════════════════════
    _section("📊 Indicadores del Estudiante")

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        _metric_card(
            "Cursos Matriculados",
            str(total_cursos),
            delta=f"en {enr_stu['term'].nunique()} ciclo(s)",
            color=COLOR_INFO,
            icon="📚",
        )
    with k2:
        prom_color = COLOR_SUCCESS if promedio_notas >= 14 else \
                     COLOR_WARNING if promedio_notas >= 11 else COLOR_PRIMARY
        _metric_card(
            "Promedio Acumulado",
            f"{promedio_notas:.1f} / 20",
            delta="✔ Aprobado" if promedio_notas >= 11 else "✘ En riesgo académico",
            color=prom_color,
            icon="🎯",
        )
    with k3:
        asist_color = COLOR_SUCCESS if prom_asistencia >= 75 else \
                      COLOR_WARNING if prom_asistencia >= 60 else COLOR_PRIMARY
        _metric_card(
            "Asistencia Promedio",
            f"{prom_asistencia:.1f}%",
            delta="✔ Regular" if prom_asistencia >= 75 else "⚠ Baja asistencia",
            color=asist_color,
            icon="📅",
        )
    with k4:
        pago_color = COLOR_SUCCESS if pagos_pendientes == 0 else \
                     COLOR_WARNING if pagos_pendientes == 1 else COLOR_PRIMARY
        pago_delta = "✔ Al día" if pagos_pendientes == 0 else \
                     f"⚠ {pagos_pendientes} pago(s) sin regularizar"
        _metric_card(
            "Pagos Pendientes / Tardíos",
            str(pagos_pendientes),
            delta=pago_delta,
            color=pago_color,
            icon="💳",
        )

    # ════════════════════════════════════════
    #  SECCIÓN 3 · GRÁFICOS
    # ════════════════════════════════════════
    _section("📈 Rendimiento y Actividad")

    col_g1, col_g2 = st.columns(2)

    # — Bar chart: notas por curso —
    with col_g1:
        if not enr_stu_courses.empty and "name" in enr_stu_courses.columns:
            # Promedio por curso (puede tener varios ciclos)
            notas_curso = (
                enr_stu_courses
                .groupby("name")["final_grade"]
                .mean()
                .reset_index()
                .rename(columns={"name": "Curso", "final_grade": "Nota"})
                .sort_values("Nota", ascending=True)
            )
            notas_curso["Nota"] = notas_curso["Nota"].round(1)
            notas_curso["Color"] = notas_curso["Nota"].apply(
                lambda n: COLOR_SUCCESS if n >= 14 else
                          COLOR_WARNING if n >= 11 else COLOR_PRIMARY
            )

            fig_bar = go.Figure()

            # Barras de notas
            fig_bar.add_trace(go.Bar(
                x=notas_curso["Nota"],
                y=notas_curso["Curso"],
                orientation="h",
                marker_color=notas_curso["Color"].tolist(),
                text=notas_curso["Nota"].apply(lambda v: f"{v:.1f}"),
                textposition="outside",
                textfont=dict(color="#EAEAEA", size=12),
                hovertemplate="<b>%{y}</b><br>Nota promedio: %{x:.1f}<extra></extra>",
                name="Nota promedio",
            ))

            # Línea vertical aprobatoria
            fig_bar.add_vline(
                x=11,
                line_dash="dash",
                line_color="#FFD166",
                line_width=2,
                annotation_text="Mín. aprobatorio (11)",
                annotation_position="top right",
                annotation_font=dict(color="#FFD166", size=11),
            )

            fig_bar.update_layout(
                title="Nota Promedio por Curso",
                title_font_size=15,
                template=PLOTLY_TPL,
                height=360,
                xaxis=dict(range=[0, 22], title="Nota (0–20)",
                           tickvals=list(range(0, 22, 2))),
                yaxis=dict(title=""),
                margin=dict(t=50, b=30, l=10, r=60),
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No hay datos de cursos para este estudiante.")

    # — Dona: distribución de interacciones —
    with col_g2:
        if not int_stu.empty:
            int_counts = int_stu["action"].value_counts().reset_index()
            int_counts.columns = ["Acción", "Cantidad"]
            int_counts["Acción"] = int_counts["Acción"]\
                .str.replace("_", " ").str.title()

            fig_pie = px.pie(
                int_counts,
                names="Acción",
                values="Cantidad",
                hole=0.52,
                color="Acción",
                color_discrete_map=ACTION_COLORS,
                title="Distribución de Actividad en LMS",
                template=PLOTLY_TPL,
            )
            fig_pie.update_traces(
                textposition="outside",
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>%{value} interacciones (%{percent})<extra></extra>",
            )
            # Anotación central
            total_int = int_stu.shape[0]
            fig_pie.add_annotation(
                text=f"<b>{total_int}</b><br><span style='font-size:10px'>acciones</span>",
                x=0.5, y=0.5,
                font=dict(size=16, color="#EAEAEA"),
                showarrow=False,
            )
            fig_pie.update_layout(
                title_font_size=15,
                height=360,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.18,
                            font=dict(size=11)),
                margin=dict(t=50, b=60, l=20, r=20),
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No hay registros de actividad en LMS para este estudiante.")

    # ════════════════════════════════════════
    #  SECCIÓN 4 · HISTORIAL DE PAGOS
    # ════════════════════════════════════════
    _section("💳 Historial de Pagos")

    if not pay_stu.empty:
        pay_sorted = pay_stu.sort_values("payment_date", ascending=False)

        # Resumen rápido encima de la tabla
        r1, r2, r3 = st.columns(3)
        total_pagado  = pay_stu[pay_stu["status"] == "pagado"]["amount"].sum()
        total_tardio  = pay_stu[pay_stu["status"] == "tardio"]["amount"].sum()
        total_pendiente = pay_stu[pay_stu["status"] == "pendiente"]["amount"].sum()

        with r1:
            _metric_card("Total Pagado",   f"S/ {total_pagado:,.0f}",
                         color=COLOR_SUCCESS, icon="✅")
        with r2:
            _metric_card("Pagos Tardíos",  f"S/ {total_tardio:,.0f}",
                         color=COLOR_WARNING, icon="⚠️")
        with r3:
            _metric_card("Por Regularizar", f"S/ {total_pendiente:,.0f}",
                         color=COLOR_PRIMARY, icon="🔴")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # Tabla de pagos
        _payment_table(pay_sorted)
    else:
        st.info("No hay registros de pagos para este estudiante.")

    # ── Footer ───────────────────────────────
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:0.75rem; color:#4a5568; text-align:center; padding:12px 0;'>"
        f"📅 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')} &nbsp;·&nbsp; "
        f"ID consultado: <code style='color:#8892a4'>{sel_id}</code> &nbsp;·&nbsp; "
        f"MongoDB · Plotly</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
#  EJECUCIÓN STANDALONE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(
        page_title="Perfil 360° del Estudiante",
        page_icon="🧑‍🎓",
        layout="wide",
    )
    if "active_page" not in st.session_state:
        st.session_state.active_page = "🧑‍🎓  Perfil 360°"
    show()