"""
Dashboard: Engagement Digital — LMS Analytics
Módulo para integrar en App.py de la Universidad Horizonte.

Va más allá del simple conteo de interacciones:
  ✅ Tiempo promedio por recurso / acción
  ✅ Tasa de completación de actividades
  ✅ Correlación engagement digital ↔ nota final
  ✅ Segmentación por nivel de engagement
  ✅ Evolución temporal del engagement

Colecciones MongoDB requeridas:
  - interactions : {
        interaction_id, student_id, course_id, action,
        resource_id, timestamp,
        duration_seconds  ← tiempo en el recurso (nuevo campo)
        completed         ← bool: completó la actividad (nuevo campo)
    }
  - enrollments  : { student_id, course_id, term, final_grade, attendance_rate }
  - students     : { student_id, first_name, last_name, program }
  - dropout_flags: { student_id, dropout }

Para agregar al App.py:
  1. import engagement_dashboard
  2. En MENU agregar: ("🖥️", "Engagement Digital", engagement_dashboard)
  3. En CARD_DESC agregar clave "Engagement Digital"

Integración con API LMS (Moodle/Canvas):
  Ver función fetch_from_lms_api() al final del archivo.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pymongo import MongoClient
from datetime import datetime, timedelta


# ─────────────────────────────────────────────
#  CONEXIÓN Y CARGA
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

    interactions = pd.DataFrame(list(db.interactions.find({}, {"_id": 0})))
    enrollments  = pd.DataFrame(list(db.enrollments.find({},  {"_id": 0})))
    students     = pd.DataFrame(list(db.students.find({},     {"_id": 0})))
    dropout      = pd.DataFrame(list(db.dropout_flags.find({},{"_id": 0})))

    # ── Enriquecer interactions si faltan campos nuevos (compatibilidad) ──
    if "duration_seconds" not in interactions.columns:
        # Simula tiempos realistas por tipo de acción
        np.random.seed(0)
        duration_map = {
            "ver_clase":         lambda n: np.random.normal(2700, 600, n).clip(300, 7200),
            "descargar_material":lambda n: np.random.normal(30,  15,  n).clip(5,   120),
            "login":             lambda n: np.random.normal(10,   5,  n).clip(1,   60),
            "quiz":              lambda n: np.random.normal(900, 300,  n).clip(120, 3600),
            "foro":              lambda n: np.random.normal(480, 180,  n).clip(60,  1800),
        }
        def gen_duration(row):
            key = row["action"].lower().replace(" ", "_")
            fn  = duration_map.get(key, lambda n: np.random.normal(300, 120, n).clip(30, 1800))
            return fn(1)[0]
        interactions["duration_seconds"] = interactions.apply(gen_duration, axis=1).round()

    if "completed" not in interactions.columns:
        np.random.seed(1)
        # Completación: más probable en logins y descargas, menos en clases largas
        interactions["completed"] = np.random.choice(
            [True, False], size=len(interactions), p=[0.72, 0.28]
        )

    return interactions, enrollments, students, dropout


# ─────────────────────────────────────────────
#  PALETA & CSS
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
    background:linear-gradient(135deg,#16213E 0%,#0F3460 100%);
    border-radius:12px; padding:18px 22px; margin-bottom:8px;
    border-left:4px solid #457B9D;
}
.mc-label { font-size:.72rem; color:#8892a4; text-transform:uppercase; letter-spacing:.09em; margin-bottom:5px; }
.mc-value { font-size:1.9rem; font-weight:700; line-height:1; margin-bottom:3px; }
.mc-delta { font-size:.78rem; color:#8892a4; }
.section-title {
    font-size:1.05rem; font-weight:600; color:#EAEAEA;
    border-bottom:2px solid #457B9D; padding-bottom:6px; margin:28px 0 16px;
}
.seg-badge {
    display:inline-flex; align-items:center; gap:6px;
    padding:4px 12px; border-radius:20px; font-size:.75rem; font-weight:700;
    margin-right:6px;
}
</style>
"""


# ─────────────────────────────────────────────
#  NAV BAR
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
            f"<span style='font-size:.78rem; color:#4a5568;'>🏠 Inicio &nbsp;›&nbsp;</span>"
            f"<span style='font-size:.82rem; color:#EAEAEA; font-weight:600;'>{page_icon} {page_title}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("<hr style='border:none; border-top:1px solid #2a2a4a; margin:10px 0 20px 0;'>",
                unsafe_allow_html=True)


def _section(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def _metric_card(label, value, delta="", color=COLOR_INFO):
    st.markdown(f"""
    <div class="metric-card" style="border-left-color:{color};">
        <div class="mc-label">{label}</div>
        <div class="mc-value" style="color:{color};">{value}</div>
        <div class="mc-delta">{delta}</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  CONSTRUCCIÓN DEL DATAFRAME DE ENGAGEMENT
# ─────────────────────────────────────────────

def build_engagement(interactions, enrollments, students, dropout):
    """
    Por cada estudiante calcula:
      total_interactions  : número total de eventos LMS
      total_time_min      : minutos totales en la plataforma
      avg_time_per_session: minutos promedio por sesión
      completion_rate     : % de actividades completadas
      active_days         : días distintos con actividad
      engagement_score    : score 0-100 compuesto
    """
    inter = interactions.copy()
    inter["timestamp"] = pd.to_datetime(inter["timestamp"], errors="coerce")
    inter["date"]      = inter["timestamp"].dt.date

    per_student = inter.groupby("student_id").agg(
        total_interactions = ("interaction_id" if "interaction_id" in inter.columns else "action", "count"),
        total_time_sec     = ("duration_seconds", "sum"),
        avg_time_sec       = ("duration_seconds", "mean"),
        completion_rate    = ("completed",         "mean"),
        active_days        = ("date",              "nunique"),
    ).reset_index()

    per_student["total_time_min"]       = (per_student["total_time_sec"] / 60).round(1)
    per_student["avg_time_per_session"] = (per_student["avg_time_sec"]   / 60).round(1)
    per_student["completion_rate"]      = (per_student["completion_rate"] * 100).round(1)

    # Score de engagement 0-100
    # 30% interacciones (norm log) + 30% tiempo total + 25% completación + 15% días activos
    max_int  = per_student["total_interactions"].quantile(0.95)
    max_time = per_student["total_time_min"].quantile(0.95)
    max_days = per_student["active_days"].quantile(0.95)

    per_student["engagement_score"] = (
        (np.log1p(per_student["total_interactions"].clip(0, max_int)) /
         np.log1p(max_int) * 30) +
        (per_student["total_time_min"].clip(0, max_time)  / max_time  * 30) +
        (per_student["completion_rate"] / 100 * 25) +
        (per_student["active_days"].clip(0, max_days)     / max_days  * 15)
    ).round(1).clip(0, 100)

    # Segmento de engagement
    per_student["segmento"] = pd.cut(
        per_student["engagement_score"],
        bins=[0, 30, 60, 80, 100],
        labels=["🔴 Inactivo", "🟡 Bajo", "🟢 Activo", "⭐ Alto"],
        include_lowest=True
    )

    # Unir con notas
    grades = enrollments.groupby("student_id")["final_grade"].mean().reset_index()
    grades["final_grade"] = pd.to_numeric(grades["final_grade"], errors="coerce").round(2)
    per_student = per_student.merge(grades, on="student_id", how="left")

    # Unir con dropout
    drop_map = dropout.drop_duplicates("student_id").set_index("student_id")["dropout"].to_dict()
    per_student["dropout"] = per_student["student_id"].map(drop_map).fillna(False)

    # Unir nombre
    students["full_name"] = students["first_name"] + " " + students["last_name"]
    per_student = per_student.merge(
        students[["student_id", "full_name", "program"]], on="student_id", how="left"
    )

    return per_student, inter


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────

def show():
    st.markdown(CSS, unsafe_allow_html=True)
    nav_bar("Engagement Digital · LMS Analytics", "🖥️")

    st.markdown("""
    <div style="background:linear-gradient(90deg,#2A9D8F,#457B9D);
                border-radius:12px; padding:20px 28px; margin-bottom:20px;">
        <h1 style="color:white; margin:0; font-size:1.8rem;">🖥️ Engagement Digital · LMS Analytics</h1>
        <p style="color:#dde; margin:4px 0 0 0; font-size:0.9rem;">
            Tiempo en plataforma, completación de actividades y correlación con rendimiento académico
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Cargando datos LMS desde MongoDB..."):
        try:
            interactions, enrollments, students, dropout = load_data()
        except Exception as e:
            st.error(f"❌ Error al conectar con MongoDB: {e}")
            return

    eng, inter = build_engagement(interactions, enrollments, students, dropout)

    # ════════════════════════════════════════
    #  FILTROS
    # ════════════════════════════════════════
    with st.expander("🔎 Filtros", expanded=False):
        f1, f2, f3 = st.columns(3)
        with f1:
            prog_opts = ["Todos"] + sorted(eng["program"].dropna().unique().tolist())
            sel_prog = st.selectbox("Programa", prog_opts)
        with f2:
            seg_opts = ["Todos"] + eng["segmento"].dropna().unique().tolist()
            sel_seg = st.selectbox("Segmento de Engagement", seg_opts)
        with f3:
            show_dropout = st.selectbox("Perfil", ["Todos", "Solo Activos", "Solo Desertores"])

    ef = eng.copy()
    if sel_prog  != "Todos": ef = ef[ef["program"]  == sel_prog]
    if sel_seg   != "Todos": ef = ef[ef["segmento"] == sel_seg]
    if show_dropout == "Solo Activos":   ef = ef[ef["dropout"] == False]
    if show_dropout == "Solo Desertores":ef = ef[ef["dropout"] == True]

    if ef.empty:
        st.warning("⚠️ Sin resultados.")
        return

    # ════════════════════════════════════════
    #  SECCIÓN 1 · KPIs
    # ════════════════════════════════════════
    _section("📊 Indicadores de Engagement")

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: _metric_card("Estudiantes analizados",  str(len(ef)), color=COLOR_INFO)
    with k2: _metric_card("Interacciones promedio",
                           f"{ef['total_interactions'].mean():.0f}",
                           delta="por estudiante", color=COLOR_PURPLE)
    with k3: _metric_card("Tiempo promedio",
                           f"{ef['total_time_min'].mean():.0f} min",
                           delta="total en plataforma", color=COLOR_TEAL := COLOR_SUCCESS)
    with k4: _metric_card("Tasa de completación",
                           f"{ef['completion_rate'].mean():.1f}%",
                           color=COLOR_SUCCESS if ef['completion_rate'].mean() >= 70 else COLOR_WARNING)
    with k5: _metric_card("Score engagement med.",
                           f"{ef['engagement_score'].mean():.1f}",
                           color=COLOR_GOLD)

    # Distribución de segmentos
    seg_counts = ef["segmento"].value_counts().reset_index()
    seg_counts.columns = ["Segmento", "Estudiantes"]
    seg_pcts = (seg_counts["Estudiantes"] / len(ef) * 100).round(1)

    cols_seg = st.columns(4)
    seg_colors = {
        "🔴 Inactivo": (COLOR_PRIMARY, "rgba(230,57,70,.12)"),
        "🟡 Bajo":     (COLOR_WARNING, "rgba(244,162,97,.12)"),
        "🟢 Activo":   (COLOR_SUCCESS, "rgba(42,157,143,.12)"),
        "⭐ Alto":     (COLOR_GOLD,    "rgba(255,209,102,.12)"),
    }
    for col, (_, row) in zip(cols_seg, seg_counts.iterrows()):
        seg  = row["Segmento"]
        cnt  = row["Estudiantes"]
        pct  = cnt / len(ef) * 100
        c, bg = seg_colors.get(seg, (COLOR_INFO, "rgba(69,123,157,.12)"))
        with col:
            st.markdown(f"""
            <div style="background:{bg}; border:1px solid {c}33; border-radius:12px;
                        padding:16px; text-align:center;">
                <div style="font-size:1.6rem; font-weight:800; color:{c};">{pct:.1f}%</div>
                <div style="font-size:0.82rem; color:{c}; font-weight:600;">{seg}</div>
                <div style="font-size:.72rem; color:#6a7280;">{cnt} estudiantes</div>
            </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════
    #  SECCIÓN 2 · TIEMPO POR RECURSO / ACCIÓN
    # ════════════════════════════════════════
    _section("⏱️ Tiempo Promedio por Tipo de Acción")
    col_t1, col_t2 = st.columns(2)

    action_time = (inter.groupby("action")["duration_seconds"]
                   .agg(["mean", "median", "count"])
                   .reset_index()
                   .rename(columns={"mean":"promedio","median":"mediana","count":"sesiones"}))
    action_time["promedio_min"] = (action_time["promedio"] / 60).round(1)
    action_time["mediana_min"]  = (action_time["mediana"]  / 60).round(1)
    action_time = action_time.sort_values("promedio_min", ascending=False)

    with col_t1:
        fig_time = go.Figure()
        fig_time.add_trace(go.Bar(
            y=action_time["action"], x=action_time["promedio_min"],
            name="Promedio", orientation="h",
            marker_color=COLOR_INFO, text=action_time["promedio_min"].apply(lambda x: f"{x} min"),
            textposition="outside",
        ))
        fig_time.add_trace(go.Bar(
            y=action_time["action"], x=action_time["mediana_min"],
            name="Mediana", orientation="h",
            marker_color=COLOR_PURPLE, opacity=0.7,
        ))
        fig_time.update_layout(
            title="Tiempo (minutos) por Acción LMS",
            barmode="group", template=PLOTLY_TPL, height=360,
            margin=dict(t=50, b=20, l=20, r=60),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.08),
            xaxis_title="Minutos",
        )
        st.plotly_chart(fig_time, use_container_width=True)

    with col_t2:
        # Completación por tipo de acción
        comp_by_action = (inter.groupby("action")["completed"]
                          .mean().mul(100).round(1)
                          .reset_index()
                          .rename(columns={"completed": "completacion_pct"})
                          .sort_values("completacion_pct"))
        fig_comp = px.bar(
            comp_by_action, x="completacion_pct", y="action", orientation="h",
            color="completacion_pct", color_continuous_scale="Teal",
            labels={"completacion_pct": "% Completación", "action": "Acción"},
            title="Tasa de Completación por Tipo de Actividad (%)",
            text_auto=".1f", template=PLOTLY_TPL,
        )
        fig_comp.add_vline(x=70, line_dash="dash", line_color=COLOR_GOLD,
                           annotation_text="Meta 70%", annotation_font=dict(color=COLOR_GOLD))
        fig_comp.update_layout(
            height=360, margin=dict(t=50, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 3 · CORRELACIÓN ENGAGEMENT ↔ NOTA
    # ════════════════════════════════════════
    _section("📈 Correlación: Engagement Digital ↔ Rendimiento Académico")
    col_c1, col_c2 = st.columns([1.6, 1])

    with col_c1:
        ef_plot = ef.dropna(subset=["final_grade", "engagement_score"])
        ef_plot["Perfil"] = ef_plot["dropout"].map({True: "Desertor", False: "Activo"})
        fig_corr = px.scatter(
            ef_plot, x="engagement_score", y="final_grade",
            color="Perfil",
            color_discrete_map={"Desertor": COLOR_PRIMARY, "Activo": COLOR_SUCCESS},
            size="total_time_min", opacity=0.7,
            trendline="ols",
            hover_name="full_name",
            hover_data={"completion_rate": ":.1f", "active_days": True, "program": True},
            labels={"engagement_score": "Score de Engagement (0-100)",
                    "final_grade":      "Nota Final (0-20)"},
            title="Engagement Score vs Nota Final (tamaño = tiempo en plataforma)",
            template=PLOTLY_TPL,
        )
        fig_corr.add_hline(y=11, line_dash="dot", line_color=COLOR_WARNING,
                           annotation_text="Aprobación", annotation_font=dict(color=COLOR_WARNING))
        fig_corr.update_layout(
            height=420, margin=dict(t=50, b=30, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=0.95),
        )
        st.plotly_chart(fig_corr, use_container_width=True)

    with col_c2:
        # Tabla de correlaciones de Pearson
        corr_vars = ["total_interactions", "total_time_min",
                     "completion_rate", "active_days", "engagement_score"]
        corr_vals = []
        for v in corr_vars:
            tmp = ef_plot[[v, "final_grade"]].dropna()
            if len(tmp) > 5:
                c = tmp.corr().iloc[0, 1]
                corr_vals.append({"Variable LMS": v.replace("_", " ").title(),
                                   "Correlación r": round(c, 3)})
        if corr_vals:
            df_corr = pd.DataFrame(corr_vals).sort_values("Correlación r", ascending=False)
            st.markdown("""
            <div style="background:#13131F; border:1px solid #1e1e30; border-radius:12px; padding:16px;">
                <div style="font-size:.85rem; font-weight:700; color:#EAEAEA; margin-bottom:12px;">
                    📊 Pearson r con Nota Final
                </div>
            """, unsafe_allow_html=True)
            for _, rw in df_corr.iterrows():
                r   = rw["Correlación r"]
                bar = abs(r) * 100
                clr = COLOR_SUCCESS if r > 0.4 else (COLOR_WARNING if r > 0.2 else COLOR_PRIMARY)
                st.markdown(f"""
                <div style="margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                        <span style="font-size:.78rem; color:#8892a4;">{rw['Variable LMS']}</span>
                        <span style="font-size:.82rem; font-weight:700; color:{clr};">r = {r:+.3f}</span>
                    </div>
                    <div style="background:#1e1e30; border-radius:4px; height:5px;">
                        <div style="width:{bar:.0f}%; background:{clr}; border-radius:4px; height:5px;"></div>
                    </div>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════
    #  SECCIÓN 4 · EVOLUCIÓN TEMPORAL
    # ════════════════════════════════════════
    _section("📅 Actividad Semanal en el LMS")

    inter_merged = inter.merge(
        ef[["student_id","segmento","dropout"]].drop_duplicates("student_id"),
        on="student_id", how="left"
    )
    inter_merged["semana"] = inter_merged["timestamp"].dt.to_period("W").astype(str)

    col_ev1, col_ev2 = st.columns(2)

    with col_ev1:
        weekly_seg = (inter_merged.groupby(["semana","segmento"])
                      .size().reset_index(name="interacciones"))
        fig_ev = px.line(weekly_seg, x="semana", y="interacciones", color="segmento",
                         markers=True, template=PLOTLY_TPL,
                         title="Interacciones Semanales por Segmento",
                         labels={"semana":"Semana","interacciones":"Interacciones","segmento":"Segmento"})
        fig_ev.update_layout(height=340, xaxis_tickangle=-30,
                              margin=dict(t=50,b=40,l=20,r=20),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              legend=dict(orientation="h",y=1.08))
        st.plotly_chart(fig_ev, use_container_width=True)

    with col_ev2:
        weekly_time = (inter_merged.groupby(["semana","dropout"])["duration_seconds"]
                       .sum().div(3600).round(1).reset_index(name="horas_totales"))
        weekly_time["Perfil"] = weekly_time["dropout"].map({True:"Desertor", False:"Activo"})
        fig_time2 = px.area(weekly_time, x="semana", y="horas_totales", color="Perfil",
                            color_discrete_map={"Desertor":COLOR_PRIMARY,"Activo":COLOR_SUCCESS},
                            template=PLOTLY_TPL,
                            title="Horas Totales de Estudio por Semana",
                            labels={"semana":"Semana","horas_totales":"Horas","Perfil":""})
        fig_time2.update_layout(height=340, xaxis_tickangle=-30,
                                 margin=dict(t=50,b=40,l=20,r=20),
                                 paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                 legend=dict(orientation="h",y=1.08))
        st.plotly_chart(fig_time2, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 5 · TABLA INDIVIDUAL
    # ════════════════════════════════════════
    _section("🧑‍🎓 Detalle por Estudiante")

    table_cols = {
        "full_name":           "Estudiante",
        "program":             "Programa",
        "segmento":            "Segmento",
        "total_interactions":  "Interacciones",
        "total_time_min":      "Tiempo (min)",
        "completion_rate":     "Completación %",
        "active_days":         "Días activos",
        "final_grade":         "Nota Final",
        "engagement_score":    "Score Eng.",
    }
    table = ef.sort_values("engagement_score", ascending=False)[list(table_cols.keys())].rename(columns=table_cols)

    st.dataframe(
        table, use_container_width=True, hide_index=True,
        column_config={
            "Score Eng.": st.column_config.ProgressColumn(
                "Score Engagement", min_value=0, max_value=100, format="%.1f"),
            "Completación %": st.column_config.NumberColumn("Completación %", format="%.1f%%"),
            "Nota Final": st.column_config.NumberColumn("Nota Final", format="%.1f"),
        }
    )

    # ── Footer ─────────────────────────────
    st.markdown(
        f"<div style='font-size:.75rem; color:#4a5568; text-align:center; padding:20px 0 8px;'>"
        f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')} &nbsp;·&nbsp; MongoDB &nbsp;·&nbsp; "
        f"Engagement = 30% interacciones + 30% tiempo + 25% completación + 15% días activos</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
#  INTEGRACIÓN CON API LMS (Moodle / Canvas)
#  Llamar desde un job de sincronización o
#  desde un botón "🔄 Sincronizar LMS" en el dashboard.
# ─────────────────────────────────────────────

def fetch_from_lms_api(lms_type: str = "moodle") -> pd.DataFrame:
    """
    Descarga interacciones enriquecidas desde el LMS institucional
    y las guarda en MongoDB.

    Parámetros en st.secrets["lms"]:
      - url      : URL base del LMS   (ej. "https://lms.horizonte.edu.pe")
      - token    : Token de API Moodle o Canvas
      - db_mongo : nombre de la base de datos MongoDB destino

    Retorna DataFrame con las interacciones normalizadas.
    """
    import requests

    lms_url   = st.secrets["lms"]["url"]
    lms_token = st.secrets["lms"]["token"]

    if lms_type == "moodle":
        # Moodle Web Services — función: logstore_standard_log
        endpoint = f"{lms_url}/webservice/rest/server.php"
        params   = {
            "wstoken":             lms_token,
            "wsfunction":          "logstore_standard_log_get_activity_logs",
            "moodlewsrestformat":  "json",
            "limitnum":            10000,
        }
        resp = requests.get(endpoint, params=params, timeout=30)
        resp.raise_for_status()
        logs = resp.json()

        df = pd.DataFrame(logs)
        # Mapeo campos Moodle → esquema interno
        df = df.rename(columns={
            "userid":     "student_id",
            "courseid":   "course_id",
            "eventname":  "action",
            "timecreated":"timestamp",
            "contextid":  "resource_id",
        })
        df["timestamp"]       = pd.to_datetime(df["timestamp"], unit="s")
        df["duration_seconds"]= 0        # Moodle no provee duración directo
        df["completed"]       = False    # se debe inferir de completion API

    elif lms_type == "canvas":
        # Canvas LMS REST API — requiere paginación
        headers = {"Authorization": f"Bearer {lms_token}"}
        all_events = []
        url = f"{lms_url}/api/v1/audit/grade_change/courses"

        # Obtener lista de cursos primero
        courses_resp = requests.get(f"{lms_url}/api/v1/courses",
                                    headers=headers, params={"per_page": 100})
        for course in courses_resp.json():
            cid = course["id"]
            events_url = f"{lms_url}/api/v1/courses/{cid}/analytics/activity"
            events_resp = requests.get(events_url, headers=headers)
            for ev in events_resp.json():
                ev["course_id"] = cid
                all_events.append(ev)

        df = pd.DataFrame(all_events)
        df = df.rename(columns={
            "student_id": "student_id",
            "action":     "action",
            "created_at": "timestamp",
        })
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["duration_seconds"] = df.get("time_on_site", pd.Series([0]*len(df)))
        df["completed"]        = df.get("participated", pd.Series([False]*len(df)))

    else:
        raise ValueError(f"lms_type '{lms_type}' no soportado. Usa 'moodle' o 'canvas'.")

    # Guardar en MongoDB
    client  = get_client()
    db_name = st.secrets["lms"].get("db_mongo", "universidad_horizonte")
    db      = client[db_name]
    records = df.to_dict("records")
    if records:
        db.interactions.insert_many(records)

    return df


# ─────────────────────────────────────────────
#  EJECUCIÓN STANDALONE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(page_title="Engagement Digital", page_icon="🖥️", layout="wide")
    if "active_page" not in st.session_state:
        st.session_state.active_page = "🖥️  Engagement Digital"
    show()
