"""
Dashboard: Deserción Estudiantil
Página para invocar desde el archivo maestro de Streamlit.
Conexión a MongoDB via st.secrets["mongo"]["uri"]
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

    students    = pd.DataFrame(list(db.students.find({}, {"_id": 0})))
    enrollments = pd.DataFrame(list(db.enrollments.find({}, {"_id": 0})))
    payments    = pd.DataFrame(list(db.payments.find({}, {"_id": 0})))
    interactions= pd.DataFrame(list(db.interactions.find({}, {"_id": 0})))
    dropout     = pd.DataFrame(list(db.dropout_flags.find({}, {"_id": 0})))
    courses     = pd.DataFrame(list(db.courses.find({}, {"_id": 0})))

    return students, enrollments, payments, interactions, dropout, courses


# ─────────────────────────────────────────────
#  PALETA Y ESTILO
# ─────────────────────────────────────────────

COLOR_PRIMARY   = "#E63946"   # rojo alerta
COLOR_WARNING   = "#F4A261"   # naranja
COLOR_SUCCESS   = "#2A9D8F"   # verde teal
COLOR_INFO      = "#457B9D"   # azul
COLOR_BG        = "#1A1A2E"   # fondo oscuro
COLOR_SURFACE   = "#16213E"
COLOR_TEXT      = "#EAEAEA"

PLOTLY_TEMPLATE = "plotly_dark"

CARD_CSS = """
<style>
    .metric-card {
        background: linear-gradient(135deg, #16213E 0%, #0F3460 100%);
        border-radius: 12px;
        padding: 20px 24px;
        border-left: 4px solid {color};
        margin-bottom: 8px;
    }
    .metric-card .label {
        font-size: 0.78rem;
        color: #aab4be;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
    }
    .metric-card .value {
        font-size: 2rem;
        font-weight: 700;
        color: {color};
        line-height: 1;
    }
    .metric-card .delta {
        font-size: 0.82rem;
        color: #aab4be;
        margin-top: 4px;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #EAEAEA;
        border-bottom: 2px solid #457B9D;
        padding-bottom: 6px;
        margin: 24px 0 16px 0;
    }
</style>
"""

def metric_card(label, value, delta="", color=COLOR_INFO):
    css = CARD_CSS.replace("{color}", color)
    st.markdown(css, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="metric-card" style="border-left-color:{color}">
        <div class="label">{label}</div>
        <div class="value" style="color:{color}">{value}</div>
        <div class="delta">{delta}</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL — LLAMAR DESDE MAESTRO
# ─────────────────────────────────────────────

def show():
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    # ── Header ──────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(90deg,#E63946,#457B9D);
                border-radius:12px;padding:20px 28px;margin-bottom:24px;">
        <h1 style="color:white;margin:0;font-size:1.8rem;">
            📉 Dashboard de Deserción Estudiantil
        </h1>
        <p style="color:#dde;margin:4px 0 0 0;font-size:0.9rem;">
            Monitoreo, análisis y alertas tempranas · Ingeniería de Software
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Carga de datos ───────────────────────
    with st.spinner("Cargando datos desde MongoDB..."):
        try:
            students, enrollments, payments, interactions, dropout, courses = load_data()
        except Exception as e:
            st.error(f"❌ Error al conectar con MongoDB: {e}")
            st.info("Verifica que `st.secrets['mongo']['uri']` y `st.secrets['mongo']['db']` estén configurados.")
            return

    # ── Preprocesamiento ─────────────────────
    if "dropout" in dropout.columns:
        dropout_students = dropout[dropout["dropout"] == True]["student_id"].unique()
    else:
        dropout_students = []

    total_students   = students["student_id"].nunique()
    total_dropout    = len(dropout_students)
    tasa_desercion   = total_dropout / total_students * 100 if total_students else 0

    dropout_merged = dropout[dropout["dropout"] == True].merge(
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

    # ── Filtros laterales ────────────────────
    with st.sidebar:
        st.markdown("### 🎛️ Filtros")
        terms = sorted(dropout["term"].unique().tolist())
        sel_terms = st.multiselect("Ciclo académico", terms, default=terms)
        reasons = dropout["reason"].unique().tolist()
        sel_reasons = st.multiselect("Motivo de deserción", reasons, default=reasons)
        st.markdown("---")
        st.caption("Los filtros afectan todas las visualizaciones.")

    df_filt = dropout_merged[
        (dropout_merged["term"].isin(sel_terms)) &
        (dropout_merged["reason"].isin(sel_reasons))
    ]

    # ════════════════════════════════════════
    #  SECCIÓN 1 · KPIs PRINCIPALES
    # ════════════════════════════════════════
    st.markdown('<div class="section-title">📊 Indicadores Clave</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Estudiantes", f"{total_students:,}", color=COLOR_INFO)
    with c2:
        metric_card("Estudiantes en Riesgo", f"{total_dropout:,}",
                    delta=f"{tasa_desercion:.1f}% del total", color=COLOR_PRIMARY)
    with c3:
        fin = (dropout_merged["reason"] == "financiero").sum()
        metric_card("Deserción Financiera", f"{fin:,}",
                    delta=f"{fin/total_dropout*100:.0f}% del total deserción" if total_dropout else "",
                    color=COLOR_WARNING)
    with c4:
        aca = (dropout_merged["reason"] == "academico").sum()
        metric_card("Deserción Académica", f"{aca:,}",
                    delta=f"{aca/total_dropout*100:.0f}% del total deserción" if total_dropout else "",
                    color="#9B5DE5")

    # ════════════════════════════════════════
    #  SECCIÓN 2 · DISTRIBUCIÓN Y TENDENCIA
    # ════════════════════════════════════════
    st.markdown('<div class="section-title">📈 Distribución y Evolución</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    # — Dona: Motivo de deserción —
    with col_a:
        reason_counts = df_filt["reason"].value_counts().reset_index()
        reason_counts.columns = ["Motivo", "Cantidad"]
        reason_counts["Motivo"] = reason_counts["Motivo"].str.capitalize()

        fig_dona = px.pie(
            reason_counts, names="Motivo", values="Cantidad",
            hole=0.55,
            color="Motivo",
            color_discrete_map={"Financiero": COLOR_WARNING, "Academico": "#9B5DE5"},
            title="Deserción por Motivo",
            template=PLOTLY_TEMPLATE,
        )
        fig_dona.update_traces(textposition="outside", textinfo="percent+label")
        fig_dona.update_layout(
            showlegend=True,
            title_font_size=15,
            margin=dict(t=50, b=20, l=20, r=20),
            height=340,
        )
        st.plotly_chart(fig_dona, use_container_width=True)

    # — Barras: Deserción por ciclo —
    with col_b:
        by_term = df_filt.groupby(["term", "reason"]).size().reset_index(name="cantidad")
        by_term["reason"] = by_term["reason"].str.capitalize()

        fig_term = px.bar(
            by_term, x="term", y="cantidad", color="reason",
            barmode="group",
            color_discrete_map={"Financiero": COLOR_WARNING, "Academico": "#9B5DE5"},
            title="Deserción por Ciclo Académico",
            labels={"term": "Ciclo", "cantidad": "Estudiantes", "reason": "Motivo"},
            template=PLOTLY_TEMPLATE,
            text_auto=True,
        )
        fig_term.update_layout(
            title_font_size=15,
            margin=dict(t=50, b=20, l=20, r=20),
            height=340,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_term, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 3 · RENDIMIENTO ACADÉMICO
    # ════════════════════════════════════════
    st.markdown('<div class="section-title">🎓 Rendimiento Académico vs Deserción</div>', unsafe_allow_html=True)

    col_c, col_d = st.columns(2)

    # — Box: Distribución de notas desertores vs activos —
    with col_c:
        enr_box = enr_merged.copy()
        enr_box["Perfil"] = enr_box["dropout"].map({True: "Desertor", False: "Activo"})
        fig_box = px.box(
            enr_box, x="Perfil", y="final_grade", color="Perfil",
            color_discrete_map={"Desertor": COLOR_PRIMARY, "Activo": COLOR_SUCCESS},
            title="Distribución de Notas Finales",
            labels={"final_grade": "Nota Final (0–20)", "Perfil": ""},
            template=PLOTLY_TEMPLATE,
            points="outliers",
        )
        fig_box.update_layout(
            title_font_size=15, height=340,
            margin=dict(t=50, b=20, l=20, r=20), showlegend=False
        )
        st.plotly_chart(fig_box, use_container_width=True)

    # — Barras horizontales: Nota promedio por curso —
    with col_d:
        enr_course = enr_merged.merge(courses, on="course_id", how="left")
        enr_course["Perfil"] = enr_course["dropout"].map({True: "Desertor", False: "Activo"})
        avg_course = enr_course.groupby(["name", "Perfil"])["final_grade"].mean().reset_index()
        avg_course.columns = ["Curso", "Perfil", "Promedio"]
        avg_course["Promedio"] = avg_course["Promedio"].round(1)

        fig_course = px.bar(
            avg_course, x="Promedio", y="Curso", color="Perfil",
            barmode="group", orientation="h",
            color_discrete_map={"Desertor": COLOR_PRIMARY, "Activo": COLOR_SUCCESS},
            title="Nota Promedio por Curso",
            labels={"Promedio": "Nota Promedio", "Curso": ""},
            template=PLOTLY_TEMPLATE,
            text_auto=".1f",
        )
        fig_course.update_layout(
            title_font_size=15, height=340,
            margin=dict(t=50, b=20, l=20, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_course, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 4 · ASISTENCIA Y PAGOS
    # ════════════════════════════════════════
    st.markdown('<div class="section-title">💳 Asistencia y Situación de Pagos</div>', unsafe_allow_html=True)

    col_e, col_f = st.columns(2)

    # — Scatter: Asistencia vs Nota coloreado por deserción —
    with col_e:
        enr_scatter = enr_merged.copy()
        enr_scatter["Perfil"] = enr_scatter["dropout"].map({True: "Desertor", False: "Activo"})
        fig_scatter = px.scatter(
            enr_scatter, x="attendance_rate", y="final_grade",
            color="Perfil",
            color_discrete_map={"Desertor": COLOR_PRIMARY, "Activo": COLOR_SUCCESS},
            opacity=0.6,
            title="Asistencia vs Nota Final",
            labels={
                "attendance_rate": "Tasa de Asistencia",
                "final_grade": "Nota Final (0–20)",
                "Perfil": ""
            },
            template=PLOTLY_TEMPLATE,
            trendline="ols",
        )
        fig_scatter.update_layout(
            title_font_size=15, height=350,
            margin=dict(t=50, b=20, l=20, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis_tickformat=".0%",
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # — Barras apiladas: Estado de pagos por perfil —
    with col_f:
        pay_merged_c = pay_merged.copy()
        pay_merged_c["Perfil"] = pay_merged_c["dropout"].map({True: "Desertor", False: "Activo"})
        pay_counts = pay_merged_c.groupby(["Perfil", "status"]).size().reset_index(name="cantidad")
        pay_counts["status"] = pay_counts["status"].str.capitalize()

        fig_pay = px.bar(
            pay_counts, x="Perfil", y="cantidad", color="status",
            barmode="stack",
            color_discrete_map={
                "Pagado":   COLOR_SUCCESS,
                "Tardio":   COLOR_WARNING,
                "Pendiente": COLOR_PRIMARY,
            },
            title="Estado de Pagos por Perfil",
            labels={"cantidad": "Registros", "status": "Estado", "Perfil": ""},
            template=PLOTLY_TEMPLATE,
            text_auto=True,
        )
        fig_pay.update_layout(
            title_font_size=15, height=350,
            margin=dict(t=50, b=20, l=20, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_pay, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 5 · ENGAGEMENT EN LMS
    # ════════════════════════════════════════
    st.markdown('<div class="section-title">💻 Actividad en el LMS</div>', unsafe_allow_html=True)

    col_g, col_h = st.columns(2)

    inter_merged = interactions.merge(
        dropout[["student_id", "dropout"]].drop_duplicates(),
        on="student_id", how="left"
    ).fillna({"dropout": False})
    inter_merged["Perfil"] = inter_merged["dropout"].map({True: "Desertor", False: "Activo"})

    # — Barras: acciones LMS por perfil —
    with col_g:
        act_count = inter_merged.groupby(["Perfil", "action"]).size().reset_index(name="cantidad")
        act_count["action"] = act_count["action"].str.replace("_", " ").str.title()

        fig_lms = px.bar(
            act_count, x="action", y="cantidad", color="Perfil",
            barmode="group",
            color_discrete_map={"Desertor": COLOR_PRIMARY, "Activo": COLOR_SUCCESS},
            title="Tipo de Interacciones en LMS",
            labels={"action": "Acción", "cantidad": "Total", "Perfil": ""},
            template=PLOTLY_TEMPLATE,
            text_auto=True,
        )
        fig_lms.update_layout(
            title_font_size=15, height=340,
            margin=dict(t=50, b=20, l=20, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_lms, use_container_width=True)

    # — Línea: actividad mensual —
    with col_h:
        inter_merged["timestamp"] = pd.to_datetime(inter_merged["timestamp"])
        inter_merged["mes"] = inter_merged["timestamp"].dt.to_period("M").astype(str)
        monthly = inter_merged.groupby(["mes", "Perfil"]).size().reset_index(name="interacciones")

        fig_line = px.line(
            monthly, x="mes", y="interacciones", color="Perfil",
            markers=True,
            color_discrete_map={"Desertor": COLOR_PRIMARY, "Activo": COLOR_SUCCESS},
            title="Actividad Mensual en LMS",
            labels={"mes": "Mes", "interacciones": "Interacciones", "Perfil": ""},
            template=PLOTLY_TEMPLATE,
        )
        fig_line.update_layout(
            title_font_size=15, height=340,
            margin=dict(t=50, b=20, l=20, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis_tickangle=-30,
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 6 · TABLA DE ALERTAS TEMPRANAS
    # ════════════════════════════════════════
    st.markdown('<div class="section-title">🚨 Alertas Tempranas — Estudiantes en Riesgo</div>',
                unsafe_allow_html=True)

    # Combinar señales de riesgo
    avg_grade  = enrollments.groupby("student_id")["final_grade"].mean().reset_index()
    avg_grade.columns = ["student_id", "nota_promedio"]
    avg_attend = enrollments.groupby("student_id")["attendance_rate"].mean().reset_index()
    avg_attend.columns = ["student_id", "asistencia_promedio"]
    pay_status = payments[payments["status"].isin(["pendiente", "tardio"])]\
                    .groupby("student_id").size().reset_index(name="pagos_malos")

    risk = students[["student_id", "first_name", "last_name", "program"]].copy()
    risk = risk.merge(avg_grade,  on="student_id", how="left")
    risk = risk.merge(avg_attend, on="student_id", how="left")
    risk = risk.merge(pay_status, on="student_id", how="left")
    risk["pagos_malos"] = risk["pagos_malos"].fillna(0).astype(int)
    risk["nota_promedio"] = risk["nota_promedio"].round(1)
    risk["asistencia_promedio"] = (risk["asistencia_promedio"] * 100).round(1)

    # Score de riesgo (0-100)
    risk["score_riesgo"] = (
        ((20 - risk["nota_promedio"].clip(0, 20)) / 20 * 50) +
        ((1  - risk["asistencia_promedio"].clip(0, 100) / 100) * 30) +
        (risk["pagos_malos"].clip(0, 4) / 4 * 20)
    ).round(1)

    risk["Nivel"] = pd.cut(
        risk["score_riesgo"],
        bins=[0, 30, 55, 100],
        labels=["🟢 Bajo", "🟡 Medio", "🔴 Alto"]
    )

    risk_high = risk[risk["Nivel"].isin(["🟡 Medio", "🔴 Alto"])]\
                    .sort_values("score_riesgo", ascending=False)\
                    .head(20)

    risk_display = risk_high.rename(columns={
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

    st.dataframe(
        risk_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score Riesgo": st.column_config.ProgressColumn(
                "Score Riesgo", min_value=0, max_value=100, format="%.1f"
            ),
            "Asist. %": st.column_config.NumberColumn("Asist. %", format="%.1f%%"),
        }
    )

    # ── Footer ───────────────────────────────
    st.markdown("---")
    st.caption(
        f"📅 Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  "
        "Datos: MongoDB · Visualizaciones: Plotly  |  "
        "Score de riesgo = 50% nota + 30% asistencia + 20% pagos"
    )


# ─────────────────────────────────────────────
#  EJECUCIÓN DIRECTA (prueba standalone)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(
        page_title="Deserción Estudiantil",
        page_icon="📉",
        layout="wide",
    )
    show()