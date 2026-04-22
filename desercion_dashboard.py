"""
Dashboard: Deserción Estudiantil
Página para invocar desde el archivo maestro de Streamlit.
Conexión a MongoDB via st.secrets["mongo"]["uri"]

Cambios v2:
  - Filtros movidos al cuerpo de la página (expander colapsable)
  - nav_bar() sticky arriba con botón "← Inicio" para volver al maestro
"""

import streamlit as st
import plotly.express as px
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
PLOTLY_TPL    = "plotly_dark"


# ─────────────────────────────────────────────
#  CSS GLOBAL DEL DASHBOARD
# ─────────────────────────────────────────────

CSS = """
<style>
/* ── Tarjetas métricas ── */
.metric-card {
    background: linear-gradient(135deg, #16213E 0%, #0F3460 100%);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 8px;
}
.metric-card .label {
    font-size: 0.75rem;
    color: #aab4be;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
}
.metric-card .value {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}
.metric-card .delta {
    font-size: 0.8rem;
    color: #8892a4;
    margin-top: 4px;
}

/* ── Título de sección ── */
.section-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #EAEAEA;
    border-bottom: 2px solid #457B9D;
    padding-bottom: 6px;
    margin: 28px 0 16px 0;
}
</style>
"""


# ─────────────────────────────────────────────
#  COMPONENTE REUTILIZABLE: NAV BAR
#  Colócalo al inicio de cada show().
#  Usa st.session_state.active_page del maestro.
# ─────────────────────────────────────────────

def nav_bar(page_title: str, page_icon: str = "📄"):
    """
    Barra de navegación superior con botón de retorno al menú principal.
    - El botón "← Inicio" setea active_page = '🏠  Inicio' y llama st.rerun().
    - El breadcrumb muestra la ruta actual.
    - Una línea divisoria separa la barra del contenido.

    Para usar en cualquier dashboard:
        from desercion_dashboard import nav_bar   # o importa el módulo que lo tenga
        nav_bar("Mi Dashboard", "📊")
    """
    col_btn, col_bread = st.columns([1.2, 8])

    with col_btn:
        if st.button(
            "⬅ Inicio",
            key=f"nav_back_{page_title}",
            use_container_width=True,
            help="Regresar al menú principal de dashboards",
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
#  HELPERS INTERNOS
# ─────────────────────────────────────────────

def _metric_card(label, value, delta="", color=COLOR_INFO):
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid {color};">
        <div class="label">{label}</div>
        <div class="value" style="color:{color};">{value}</div>
        <div class="delta">{delta}</div>
    </div>""", unsafe_allow_html=True)

def _section(title):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────

def show():
    st.markdown(CSS, unsafe_allow_html=True)

    # ── NAV BAR (siempre arriba) ─────────────
    nav_bar("Deserción Estudiantil", "📉")

    # ── HEADER ──────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(90deg,#E63946,#457B9D);
                border-radius:12px; padding:20px 28px; margin-bottom:20px;">
        <h1 style="color:white; margin:0; font-size:1.8rem;">
            📉 Dashboard de Deserción Estudiantil
        </h1>
        <p style="color:#dde; margin:4px 0 0 0; font-size:0.9rem;">
            Monitoreo, análisis y alertas tempranas · Ingeniería de Software
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── CARGA ───────────────────────────────
    with st.spinner("Cargando datos desde MongoDB..."):
        try:
            students, enrollments, payments, interactions, dropout, courses = load_data()
        except Exception as e:
            st.error(f"❌ Error al conectar con MongoDB: {e}")
            st.info("Verifica `st.secrets['mongo']['uri']` y `st.secrets['mongo']['db']`.")
            return

    # ── PREPROCESAMIENTO ────────────────────
    total_students = students["student_id"].nunique()
    dropout_true   = dropout[dropout["dropout"] == True]
    total_dropout  = dropout_true["student_id"].nunique()
    tasa_desercion = total_dropout / total_students * 100 if total_students else 0

    dropout_merged = dropout_true.merge(
        students[["student_id", "first_name", "last_name", "gender", "program"]],
        on="student_id", how="left"
    )
    enr_merged = enrollments.merge(
        dropout[["student_id", "dropout"]].drop_duplicates(),
        on="student_id", how="left"
    ).fillna({"dropout": False})
    pay_merged = payments.merge(
        dropout[["student_id", "dropout"]].drop_duplicates(),
        on="student_id", how="left"
    ).fillna({"dropout": False})

    # ── FILTROS EN PÁGINA ───────────────────
    with st.expander("🎛️ Filtros del dashboard", expanded=False):
        st.markdown(
            "<p style='font-size:0.82rem; color:#8892a4; margin:0 0 12px 0;'>"
            "Los filtros aplican a las secciones de Distribución y Evolución.</p>",
            unsafe_allow_html=True,
        )
        fc1, fc2 = st.columns([2, 2])
        with fc1:
            terms_opts = sorted(dropout["term"].unique().tolist())
            sel_terms = st.multiselect(
                "📅 Ciclo académico", terms_opts,
                default=terms_opts, key="des_terms"
            )
        with fc2:
            reasons_opts = dropout["reason"].unique().tolist()
            sel_reasons = st.multiselect(
                "🔍 Motivo de deserción", reasons_opts,
                default=reasons_opts, key="des_reasons"
            )        

    df_filt = dropout_merged[
        (dropout_merged["term"].isin(sel_terms)) &
        (dropout_merged["reason"].isin(sel_reasons))
    ]

    # ════════════════════════════════════════
    #  SECCIÓN 1 · KPIs
    # ════════════════════════════════════════
    _section("📊 Indicadores Clave")

    fin = (dropout_merged["reason"] == "financiero").sum()
    aca = (dropout_merged["reason"] == "academico").sum()
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        _metric_card("Total Estudiantes", f"{total_students:,}", color=COLOR_INFO)
    with c2:
        _metric_card("Desertores totales unicos", f"{total_dropout:,}", color=COLOR_WARNING
                    #  delta=f"{tasa_desercion:.1f}% del total", color=COLOR_PRIMARY
                     )
    with c3:
        _metric_card("Deserción Financiera", f"{fin:,}",
                     delta=f"{fin/len(dropout_true)*100:.0f}% de desertores" if total_dropout else "",
                     color=COLOR_WARNING)
    with c4:
        _metric_card("Deserción Académica", f"{aca:,}",
                     delta=f"{aca/len(dropout_true)*100:.0f}% de desertores" if total_dropout else "",
                     color=COLOR_PURPLE)

    # ════════════════════════════════════════
    #  SECCIÓN 2 · DISTRIBUCIÓN Y EVOLUCIÓN
    # ════════════════════════════════════════
    _section("📈 Distribución y Evolución")
    col_a, col_b = st.columns(2)

    with col_a:
        rc = df_filt["reason"].value_counts().reset_index()
        rc.columns = ["Motivo", "Cantidad"]
        rc["Motivo"] = rc["Motivo"].str.capitalize()
        fig = px.pie(rc, names="Motivo", values="Cantidad", hole=0.55,
                     color="Motivo",
                     color_discrete_map={"Financiero": COLOR_WARNING, "Academico": COLOR_PURPLE},
                     title="Deserción por Motivo", template=PLOTLY_TPL)
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(title_font_size=15, height=340, showlegend=True,
                          margin=dict(t=50, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        bt = df_filt.groupby(["term", "reason"]).size().reset_index(name="cantidad")
        bt["reason"] = bt["reason"].str.capitalize()
        fig = px.bar(bt, x="term", y="cantidad", color="reason", barmode="group",
                     color_discrete_map={"Financiero": COLOR_WARNING, "Academico": COLOR_PURPLE},
                     title="Deserción por Ciclo Académico",
                     labels={"term": "Ciclo", "cantidad": "Estudiantes", "reason": "Motivo"},
                     template=PLOTLY_TPL, text_auto=True)
        fig.update_layout(title_font_size=15, height=340,
                          margin=dict(t=50, b=20, l=20, r=20),
                          legend=dict(orientation="h", yanchor="bottom", y=0.95, x=0.60))
        st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 3 · RENDIMIENTO ACADÉMICO
    # ════════════════════════════════════════
    _section("🎓 Rendimiento Académico vs Deserción")
    col_c, col_d = st.columns(2)

    with col_c:
        eb = enr_merged.copy()
        eb["Perfil"] = eb["dropout"].map({True: "Desertor", False: "Activo"})
        fig = px.box(eb, x="Perfil", y="final_grade", color="Perfil",
                     color_discrete_map={"Desertor": COLOR_PRIMARY, "Activo": COLOR_SUCCESS},
                     title="Distribución de Notas Finales",
                     labels={"final_grade": "Nota Final (0–20)", "Perfil": ""},
                     template=PLOTLY_TPL, points="outliers")
        fig.update_layout(title_font_size=15, height=340, showlegend=False,
                          margin=dict(t=50, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_d:
        ec = enr_merged.merge(courses, on="course_id", how="left")
        ec["Perfil"] = ec["dropout"].map({True: "Desertor", False: "Activo"})
        ac = ec.groupby(["name", "Perfil"])["final_grade"].mean().reset_index()
        ac.columns = ["Curso", "Perfil", "Promedio"]
        ac["Promedio"] = ac["Promedio"].round(1)
        fig = px.bar(ac, x="Promedio", y="Curso", color="Perfil",
                     barmode="group", orientation="h",
                     color_discrete_map={"Desertor": COLOR_PRIMARY, "Activo": COLOR_SUCCESS},
                     title="Nota Promedio por Curso",
                     labels={"Promedio": "Nota Promedio", "Curso": ""},
                     template=PLOTLY_TPL, text_auto=".1f")
        fig.update_layout(title_font_size=15, height=340,
                          margin=dict(t=50, b=20, l=20, r=20),
                          legend=dict(orientation="h", yanchor="bottom", y=1.00, x=0.60),
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 4 · ASISTENCIA Y PAGOS
    # ════════════════════════════════════════
    _section("💳 Asistencia y Situación de Pagos")
    col_e, col_f = st.columns(2)

    with col_e:
        es = enr_merged.copy()
        es["Perfil"] = es["dropout"].map({True: "Desertor", False: "Activo"})
        fig = px.scatter(es, x="attendance_rate", y="final_grade",
                         color="Perfil", opacity=0.6,
                         color_discrete_map={"Desertor": COLOR_PRIMARY, "Activo": COLOR_SUCCESS},
                         title="Asistencia vs Nota Final",
                         labels={"attendance_rate": "Tasa de Asistencia",
                                 "final_grade": "Nota Final (0–20)", "Perfil": ""},
                         template=PLOTLY_TPL, trendline="ols")
        fig.update_layout(title_font_size=15, height=350,
                          margin=dict(t=50, b=20, l=20, r=20),
                          legend=dict(orientation="h", yanchor="bottom", y=0.95),
                          xaxis_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

    with col_f:
        pc = pay_merged.copy()
        pc["Perfil"] = pc["dropout"].map({True: "Desertor", False: "Activo"})
        pct = pc.groupby(["Perfil", "status"]).size().reset_index(name="cantidad")
        pct["status"] = pct["status"].str.capitalize()
        fig = px.bar(pct, x="Perfil", y="cantidad", color="status", barmode="stack",
                     color_discrete_map={"Pagado": COLOR_SUCCESS,
                                         "Tardio": COLOR_WARNING,
                                         "Pendiente": COLOR_PRIMARY},
                     title="Estado de Pagos por Perfil",
                     labels={"cantidad": "Registros", "status": "Estado", "Perfil": ""},
                     template=PLOTLY_TPL, text_auto=True)
        fig.update_layout(title_font_size=15, height=350,
                          margin=dict(t=50, b=20, l=20, r=20),
                          legend=dict(orientation="h", yanchor="bottom", y=0.95, x=0.50))
        st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 5 · ENGAGEMENT LMS
    # ════════════════════════════════════════
    _section("💻 Actividad en el LMS")
    col_g, col_h = st.columns(2)

    im = interactions.merge(
        dropout[["student_id", "dropout"]].drop_duplicates(),
        on="student_id", how="left"
    ).fillna({"dropout": False})
    im["Perfil"] = im["dropout"].map({True: "Desertor", False: "Activo"})

    with col_g:
        ac2 = im.groupby(["Perfil", "action"]).size().reset_index(name="cantidad")
        ac2["action"] = ac2["action"].str.replace("_", " ").str.title()
        fig = px.bar(ac2, x="action", y="cantidad", color="Perfil", barmode="group",
                     color_discrete_map={"Desertor": COLOR_PRIMARY, "Activo": COLOR_SUCCESS},
                     title="Tipo de Interacciones en LMS",
                     labels={"action": "Acción", "cantidad": "Total", "Perfil": ""},
                     template=PLOTLY_TPL, text_auto=True)
        fig.update_layout(title_font_size=15, height=340,
                          margin=dict(t=50, b=20, l=20, r=20),
                          legend=dict(orientation="h", yanchor="bottom", y=0.95))
        st.plotly_chart(fig, use_container_width=True)

    with col_h:
        im["timestamp"] = pd.to_datetime(im["timestamp"])
        im["mes"] = im["timestamp"].dt.to_period("M").astype(str)
        ml = im.groupby(["mes", "Perfil"]).size().reset_index(name="interacciones")
        fig = px.line(ml, x="mes", y="interacciones", color="Perfil", markers=True,
                      color_discrete_map={"Desertor": COLOR_PRIMARY, "Activo": COLOR_SUCCESS},
                      title="Actividad Mensual en LMS",
                      labels={"mes": "Mes", "interacciones": "Interacciones", "Perfil": ""},
                      template=PLOTLY_TPL)
        fig.update_layout(title_font_size=15, height=340,
                          margin=dict(t=50, b=20, l=20, r=20),
                          legend=dict(orientation="h", yanchor="bottom", y=0.95),
                          xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 6 · ALERTAS TEMPRANAS
    # ════════════════════════════════════════
    _section("🚨 Alertas Tempranas — Estudiantes en Riesgo")

    avg_grade  = enrollments.groupby("student_id")["final_grade"].mean().reset_index()
    avg_grade.columns  = ["student_id", "nota_promedio"]
    avg_attend = enrollments.groupby("student_id")["attendance_rate"].mean().reset_index()
    avg_attend.columns = ["student_id", "asistencia_promedio"]
    pay_bad = payments[payments["status"].isin(["pendiente", "tardio"])]\
                  .groupby("student_id").size().reset_index(name="pagos_malos")

    risk = students[["student_id", "first_name", "last_name", "program"]].copy()
    risk = risk.merge(avg_grade,  on="student_id", how="left")
    risk = risk.merge(avg_attend, on="student_id", how="left")
    risk = risk.merge(pay_bad,    on="student_id", how="left")
    risk["pagos_malos"]         = risk["pagos_malos"].fillna(0).astype(int)
    risk["nota_promedio"]       = risk["nota_promedio"].round(1)
    risk["asistencia_promedio"] = (risk["asistencia_promedio"] * 100).round(1)
    risk["score_riesgo"] = (
        ((20 - risk["nota_promedio"].clip(0, 20)) / 20 * 50) +
        ((1  - risk["asistencia_promedio"].clip(0, 100) / 100) * 30) +
        (risk["pagos_malos"].clip(0, 4) / 4 * 20)
    ).round(1)
    risk["Nivel"] = pd.cut(
        risk["score_riesgo"], bins=[0, 30, 55, 100],
        labels=["🟢 Bajo", "🟡 Medio", "🔴 Alto"]
    )

    risk_disp = (
        risk[risk["Nivel"].isin(["🟡 Medio", "🔴 Alto"])]
        .sort_values("score_riesgo", ascending=False)
        .head(20)
        .rename(columns={
            "first_name":           "Nombre",
            "last_name":            "Apellido",
            "program":              "Programa",
            "nota_promedio":        "Nota Prom.",
            "asistencia_promedio":  "Asist. %",
            "pagos_malos":          "Pagos Pend./Tardíos",
            "score_riesgo":         "Score Riesgo",
            "Nivel":                "Nivel Riesgo",
        })[["Nombre","Apellido","Programa","Nota Prom.","Asist. %",
            "Pagos Pend./Tardíos","Score Riesgo","Nivel Riesgo"]]
    )

    st.dataframe(
        risk_disp,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score Riesgo": st.column_config.ProgressColumn(
                "Score Riesgo", min_value=0, max_value=100, format="%.1f"
            ),
            "Asist. %": st.column_config.NumberColumn("Asist. %", format="%.1f%%"),
        }
    )

    # ── Footer ────────────────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:0.75rem; color:#4a5568; text-align:center; padding:12px 0;'>"
        f"📅 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')} &nbsp;·&nbsp; "
        f"MongoDB &nbsp;·&nbsp; Plotly &nbsp;·&nbsp; "
        f"Score = 50% nota + 30% asistencia + 20% pagos</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
#  EJECUCIÓN STANDALONE (prueba directa)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(
        page_title="Deserción Estudiantil",
        page_icon="📉",
        layout="wide",
    )
    if "active_page" not in st.session_state:
        st.session_state.active_page = "📉  Deserción Estudiantil"
    show()