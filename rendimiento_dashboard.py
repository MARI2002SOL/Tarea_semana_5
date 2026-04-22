"""
Dashboard: Rendimiento Académico por Docente
Módulo para integrar en App.py de la Universidad Horizonte.

Colecciones MongoDB requeridas:
  - teachers        : { teacher_id, first_name, last_name, department, email }
  - courses         : { course_id, name, teacher_id, department, modality }
  - enrollments     : { student_id, course_id, term, final_grade, attendance_rate }
  - satisfaction    : { student_id, course_id, term, rating (1-5), comment }   ← nueva
  - dropout_flags   : { student_id, dropout (bool) }

Para agregar al App.py:
  1. import rendimiento_dashboard
  2. En MENU agregar: ("👨‍🏫", "Rendimiento Docente", rendimiento_dashboard)
  3. En CARD_DESC agregar la clave "Rendimiento Docente"
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
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

    teachers    = pd.DataFrame(list(db.teachers.find({},    {"_id": 0})))
    courses     = pd.DataFrame(list(db.courses.find({},     {"_id": 0})))
    enrollments = pd.DataFrame(list(db.enrollments.find({}, {"_id": 0})))
    dropout     = pd.DataFrame(list(db.dropout_flags.find({},{"_id": 0})))

    # Satisfacción es opcional — si no existe se genera sintética
    try:
        satisfaction = pd.DataFrame(list(db.satisfaction.find({}, {"_id": 0})))
        if satisfaction.empty:
            raise ValueError("vacío")
    except Exception:
        # Datos sintéticos de satisfacción para demo
        np.random.seed(42)
        satisfaction = enrollments[["student_id", "course_id", "term"]].copy()
        satisfaction["rating"] = np.random.choice([3, 4, 4, 4, 5, 5], size=len(satisfaction))

    return teachers, courses, enrollments, dropout, satisfaction


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
    background: linear-gradient(135deg, #16213E 0%, #0F3460 100%);
    border-radius: 12px; padding: 18px 22px; margin-bottom: 8px;
    border-left: 4px solid #457B9D; position: relative; overflow: hidden;
}
.metric-card .mc-label { font-size:0.72rem; color:#8892a4; text-transform:uppercase; letter-spacing:.09em; margin-bottom:5px; }
.metric-card .mc-value { font-size:1.9rem; font-weight:700; line-height:1; margin-bottom:3px; }
.metric-card .mc-delta { font-size:0.78rem; color:#8892a4; }

.section-title {
    font-size:1.05rem; font-weight:600; color:#EAEAEA;
    border-bottom:2px solid #457B9D; padding-bottom:6px; margin:28px 0 16px;
}

.teacher-card {
    background: linear-gradient(135deg,#16213E,#0F3460);
    border-radius:14px; padding:24px; border:1px solid #2a2a4a;
    display:flex; align-items:center; gap:18px;
}
.teacher-avatar {
    width:64px; height:64px; border-radius:50%;
    background:linear-gradient(135deg,#9B5DE5,#457B9D);
    display:flex; align-items:center; justify-content:center;
    font-size:1.8rem; flex-shrink:0;
}
.teacher-name { font-size:1.2rem; font-weight:700; color:#EAEAEA; }
.teacher-dept { font-size:0.8rem; color:#8892a4; margin-top:3px; }
.badge {
    display:inline-block; padding:3px 10px; border-radius:20px;
    font-size:0.72rem; font-weight:600; margin-right:6px; margin-top:6px;
}

.rank-row {
    display:flex; align-items:center; gap:12px;
    background:#13131F; border:1px solid #1e1e30;
    border-radius:10px; padding:14px 16px; margin-bottom:8px;
    transition: border-color .2s;
}
.rank-row:hover { border-color:#2a2a4a; }
.rank-num { font-size:1.1rem; font-weight:800; color:#2a2a4a; min-width:28px; font-family:monospace; }
.rank-name { font-size:0.9rem; font-weight:600; color:#EAEAEA; flex:1; }
.rank-bar-wrap { width:120px; background:#1e1e30; border-radius:4px; height:6px; overflow:hidden; }
.rank-bar { height:6px; border-radius:4px; }
.rank-val { font-size:0.82rem; font-weight:700; min-width:38px; text-align:right; }
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
            f"<span style='font-size:0.78rem; color:#4a5568;'>🏠 Inicio &nbsp;›&nbsp;</span>"
            f"<span style='font-size:0.82rem; color:#EAEAEA; font-weight:600;'>{page_icon} {page_title}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("<hr style='border:none; border-top:1px solid #2a2a4a; margin:10px 0 20px 0;'>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def _section(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def _metric_card(label, value, delta="", color=COLOR_INFO):
    st.markdown(f"""
    <div class="metric-card" style="border-left-color:{color};">
        <div class="mc-label">{label}</div>
        <div class="mc-value" style="color:{color};">{value}</div>
        <div class="mc-delta">{delta}</div>
    </div>""", unsafe_allow_html=True)


def _stars(rating: float) -> str:
    full  = int(rating)
    half  = 1 if (rating - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + ("½" if half else "") + "☆" * empty


def _perf_color(val, thresholds=(50, 70)):
    if val >= thresholds[1]: return COLOR_SUCCESS
    if val >= thresholds[0]: return COLOR_WARNING
    return COLOR_PRIMARY


# ─────────────────────────────────────────────
#  CONSTRUCCIÓN DEL DATAFRAME CONSOLIDADO
# ─────────────────────────────────────────────

def build_teacher_metrics(teachers, courses, enrollments, dropout, satisfaction):
    """
    Por cada docente calcula:
      - n_courses    : número de cursos distintos
      - n_students   : total de estudiantes únicos
      - avg_grade    : nota promedio de sus estudiantes
      - approval_rate: % que aprueba (nota >= 11)
      - avg_attendance: asistencia promedio
      - dropout_rate : % de desertores entre sus estudiantes
      - avg_rating   : satisfacción promedio (1-5)
    """
    # unir cursos → enrollments
    enr = enrollments.merge(courses[["course_id", "teacher_id"]], on="course_id", how="left")
    enr["final_grade"] = pd.to_numeric(enr["final_grade"], errors="coerce")
    enr["attendance_rate"] = pd.to_numeric(enr["attendance_rate"], errors="coerce")

    # unir dropout
    drop_map = dropout.drop_duplicates("student_id").set_index("student_id")["dropout"].to_dict()
    enr["dropout"] = enr["student_id"].map(drop_map).fillna(False)

    # unir satisfacción
    sat_avg = (satisfaction.groupby("course_id")["rating"].mean().reset_index()
               .rename(columns={"rating": "avg_rating"}))
    enr = enr.merge(courses[["course_id", "teacher_id"]].merge(sat_avg, on="course_id", how="left"),
                    on=["course_id", "teacher_id"], how="left")

    grouped = enr.groupby("teacher_id").agg(
        n_courses      = ("course_id",       "nunique"),
        n_students     = ("student_id",       "nunique"),
        avg_grade      = ("final_grade",      "mean"),
        avg_attendance = ("attendance_rate",  "mean"),
        dropout_count  = ("dropout",          "sum"),
        avg_rating     = ("avg_rating",       "mean"),
    ).reset_index()

    grouped["approval_rate"] = (
        enr[enr["final_grade"] >= 11].groupby("teacher_id")["student_id"].nunique() /
        enr.groupby("teacher_id")["student_id"].nunique() * 100
    ).reindex(grouped["teacher_id"]).values

    grouped["dropout_rate"] = (grouped["dropout_count"] / grouped["n_students"] * 100).round(1)
    grouped["avg_grade"]      = grouped["avg_grade"].round(2)
    grouped["avg_attendance"] = (grouped["avg_attendance"] * 100).round(1)
    grouped["approval_rate"]  = grouped["approval_rate"].round(1)
    grouped["avg_rating"]     = grouped["avg_rating"].round(2)

    # unir nombres
    teachers["full_name"] = teachers["first_name"] + " " + teachers["last_name"]
    metrics = grouped.merge(teachers[["teacher_id", "full_name", "department", "email"]],
                            on="teacher_id", how="left")
    return metrics, enr


# ─────────────────────────────────────────────
#  SCORE PEDAGÓGICO COMPUESTO
# ─────────────────────────────────────────────

def compute_pedagogy_score(row):
    """
    Score 0–100 que mide la efectividad pedagógica del docente.
    Pesos: 35% aprobación + 25% nota promedio + 20% asistencia + 20% satisfacción
    """
    s_aprob  = min(row["approval_rate"], 100) / 100 * 35
    s_grade  = min(row["avg_grade"], 20)     / 20   * 25
    s_attend = min(row["avg_attendance"],100)/ 100  * 20
    s_sat    = (min(row["avg_rating"], 5) - 1) / 4  * 20   # normaliza 1-5 → 0-1
    return round(s_aprob + s_grade + s_attend + s_sat, 1)


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────

def show():
    st.markdown(CSS, unsafe_allow_html=True)
    nav_bar("Rendimiento Académico por Docente", "👨‍🏫")

    st.markdown("""
    <div style="background:linear-gradient(90deg,#9B5DE5,#457B9D);
                border-radius:12px; padding:20px 28px; margin-bottom:20px;">
        <h1 style="color:white; margin:0; font-size:1.8rem;">👨‍🏫 Rendimiento Académico por Docente</h1>
        <p style="color:#dde; margin:4px 0 0 0; font-size:0.9rem;">
            Análisis cruzado de aprobación, asistencia y satisfacción estudiantil · Ingeniería de Software
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── CARGA ─────────────────────────────────
    with st.spinner("Cargando datos desde MongoDB..."):
        try:
            teachers, courses, enrollments, dropout, satisfaction = load_data()
        except Exception as e:
            st.error(f"❌ Error al conectar con MongoDB: {e}")
            st.info("Verifica `st.secrets['mongo']['uri']` y las colecciones requeridas.")
            return

    metrics, enr = build_teacher_metrics(teachers, courses, enrollments, dropout, satisfaction)
    metrics["score_pedagogico"] = metrics.apply(compute_pedagogy_score, axis=1)
    metrics = metrics.sort_values("score_pedagogico", ascending=False)

    # ════════════════════════════════════════
    #  FILTROS
    # ════════════════════════════════════════
    with st.expander("🔎 Filtros", expanded=False):
        f1, f2, f3 = st.columns(3)
        with f1:
            depts = ["Todos"] + sorted(metrics["department"].dropna().unique().tolist())
            sel_dept = st.selectbox("Departamento", depts)
        with f2:
            min_score = st.slider("Score mínimo", 0, 100, 0)
        with f3:
            sel_teacher = st.selectbox("Docente específico", ["Todos"] + metrics["full_name"].tolist())

    mf = metrics.copy()
    if sel_dept != "Todos":
        mf = mf[mf["department"] == sel_dept]
    mf = mf[mf["score_pedagogico"] >= min_score]
    if sel_teacher != "Todos":
        mf = mf[mf["full_name"] == sel_teacher]

    if mf.empty:
        st.warning("⚠️ Sin resultados con los filtros aplicados.")
        return

    # ════════════════════════════════════════
    #  SECCIÓN 1 · KPIs GLOBALES
    # ════════════════════════════════════════
    _section("📊 Indicadores Generales del Cuerpo Docente")

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: _metric_card("Docentes activos",    str(len(mf)),                    color=COLOR_INFO)
    with k2: _metric_card("Aprobación promedio", f"{mf['approval_rate'].mean():.1f}%",
                           color=_perf_color(mf['approval_rate'].mean()))
    with k3: _metric_card("Nota promedio",        f"{mf['avg_grade'].mean():.1f}/20",
                           color=_perf_color(mf['avg_grade'].mean(), (11, 14)))
    with k4: _metric_card("Satisfacción media",   f"{mf['avg_rating'].mean():.2f} / 5",
                           color=COLOR_GOLD)
    with k5: _metric_card("Score pedagógico med.", f"{mf['score_pedagogico'].mean():.1f}",
                           color=COLOR_PURPLE)

    # ════════════════════════════════════════
    #  SECCIÓN 2 · PERFIL DE DOCENTE SELECCIONADO
    # ════════════════════════════════════════
    if sel_teacher != "Todos":
        row = mf.iloc[0]
        _section(f"🧑‍🏫 Perfil: {row['full_name']}")
        st.markdown(f"""
        <div class="teacher-card">
            <div class="teacher-avatar">👨‍🏫</div>
            <div style="flex:1;">
                <div class="teacher-name">{row['full_name']}</div>
                <div class="teacher-dept">🏢 {row.get('department','—')} &nbsp;·&nbsp; 📧 {row.get('email','—')}</div>
                <div>
                    <span class="badge" style="background:rgba(69,123,157,.2); color:{COLOR_INFO}; border:1px solid {COLOR_INFO};">
                        📚 {int(row['n_courses'])} cursos
                    </span>
                    <span class="badge" style="background:rgba(155,93,229,.15); color:{COLOR_PURPLE}; border:1px solid {COLOR_PURPLE};">
                        👥 {int(row['n_students'])} estudiantes
                    </span>
                    <span class="badge" style="background:rgba(255,209,102,.15); color:{COLOR_GOLD}; border:1px solid {COLOR_GOLD};">
                        ⭐ {_stars(row['avg_rating'])} ({row['avg_rating']:.2f})
                    </span>
                </div>
            </div>
            <div style="text-align:center; background:rgba(155,93,229,.1); border:1px solid rgba(155,93,229,.3);
                        border-radius:12px; padding:16px 24px;">
                <div style="font-size:2.2rem; font-weight:800; color:{COLOR_PURPLE};">{row['score_pedagogico']}</div>
                <div style="font-size:0.72rem; color:#8892a4; text-transform:uppercase; letter-spacing:.1em;">Score Pedagógico</div>
            </div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        p1, p2, p3, p4 = st.columns(4)
        with p1: _metric_card("Tasa de Aprobación", f"{row['approval_rate']:.1f}%",
                               color=_perf_color(row['approval_rate']))
        with p2: _metric_card("Nota Promedio", f"{row['avg_grade']:.1f}/20",
                               color=_perf_color(row['avg_grade'], (11, 14)))
        with p3: _metric_card("Asistencia Promedio", f"{row['avg_attendance']:.1f}%",
                               color=_perf_color(row['avg_attendance']))
        with p4: _metric_card("Tasa de Deserción", f"{row['dropout_rate']:.1f}%",
                               color=COLOR_PRIMARY if row['dropout_rate'] > 15 else COLOR_SUCCESS)

        # Radar del docente
        categories = ["Aprobación", "Nota", "Asistencia", "Satisfacción", "Retención"]
        values = [
            row["approval_rate"],
            row["avg_grade"] / 20 * 100,
            row["avg_attendance"],
            (row["avg_rating"] - 1) / 4 * 100,
            100 - row["dropout_rate"],
        ]
        fig_radar = go.Figure(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            line_color=COLOR_PURPLE,
            fillcolor="rgba(155,93,229,0.15)",
            name=row["full_name"],
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100], gridcolor="#2a2a4a", color="#6a7280"),
                       angularaxis=dict(gridcolor="#2a2a4a", color="#EAEAEA")),
            showlegend=False, template=PLOTLY_TPL, height=340,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=20, l=40, r=40),
            title=dict(text="Perfil de Efectividad Pedagógica", font=dict(size=14, color="#EAEAEA")),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 3 · RANKING DE DOCENTES
    # ════════════════════════════════════════
    _section("🏆 Ranking por Score Pedagógico")

    col_rank, col_scatter = st.columns([1, 1.6])

    with col_rank:
        for i, (_, row) in enumerate(mf.head(10).iterrows()):
            bar_pct = row["score_pedagogico"]
            bar_color = COLOR_SUCCESS if bar_pct >= 70 else (COLOR_WARNING if bar_pct >= 50 else COLOR_PRIMARY)
            st.markdown(f"""
            <div class="rank-row">
                <span class="rank-num">#{i+1}</span>
                <span class="rank-name">{row['full_name']}</span>
                <div class="rank-bar-wrap">
                    <div class="rank-bar" style="width:{bar_pct}%; background:{bar_color};"></div>
                </div>
                <span class="rank-val" style="color:{bar_color};">{bar_pct}</span>
            </div>""", unsafe_allow_html=True)

    with col_scatter:
        fig_sc = px.scatter(
            mf, x="approval_rate", y="avg_rating",
            size="n_students", color="score_pedagogico",
            color_continuous_scale="Viridis",
            hover_name="full_name",
            hover_data={"avg_grade": ":.1f", "dropout_rate": ":.1f%",
                        "n_courses": True, "score_pedagogico": ":.1f"},
            labels={"approval_rate": "Tasa Aprobación (%)",
                    "avg_rating": "Satisfacción (1-5)",
                    "score_pedagogico": "Score"},
            title="Aprobación vs Satisfacción (tamaño = nº alumnos)",
            template=PLOTLY_TPL,
        )
        fig_sc.update_layout(height=400, margin=dict(t=50, b=30, l=20, r=20),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_sc, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 4 · DISTRIBUCIÓN POR DEPARTAMENTO
    # ════════════════════════════════════════
    _section("🏢 Análisis por Departamento")
    col_d1, col_d2 = st.columns(2)

    dept_summary = mf.groupby("department").agg(
        approval_rate    = ("approval_rate",    "mean"),
        avg_rating       = ("avg_rating",       "mean"),
        score_pedagogico = ("score_pedagogico", "mean"),
        n_teachers       = ("teacher_id",       "count"),
    ).reset_index().round(2)

    with col_d1:
        fig_dept = px.bar(dept_summary, x="department", y="approval_rate",
                          color="score_pedagogico", color_continuous_scale="Plasma",
                          labels={"department": "Departamento", "approval_rate": "Tasa Aprobación (%)"},
                          title="Tasa de Aprobación por Departamento",
                          template=PLOTLY_TPL, text_auto=".1f")
        fig_dept.add_hline(y=70, line_dash="dash", line_color=COLOR_SUCCESS,
                           annotation_text="Meta 70%", annotation_font=dict(color=COLOR_SUCCESS))
        fig_dept.update_layout(height=360, margin=dict(t=50, b=40, l=20, r=20),
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_dept, use_container_width=True)

    with col_d2:
        fig_sat = px.bar(dept_summary, x="department", y="avg_rating",
                         color="avg_rating", color_continuous_scale="Teal",
                         labels={"department": "Departamento", "avg_rating": "Satisfacción (1-5)"},
                         title="Satisfacción Estudiantil por Departamento",
                         template=PLOTLY_TPL, text_auto=".2f")
        fig_sat.add_hline(y=4.0, line_dash="dash", line_color=COLOR_GOLD,
                          annotation_text="Meta 4.0", annotation_font=dict(color=COLOR_GOLD))
        fig_sat.update_layout(height=360, margin=dict(t=50, b=40, l=20, r=20),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_sat, use_container_width=True)

    # ════════════════════════════════════════
    #  SECCIÓN 5 · NECESIDADES DE FORMACIÓN
    # ════════════════════════════════════════
    _section("🎯 Diagnóstico de Necesidades de Formación")

    mf["necesita_apoyo"] = (
        (mf["approval_rate"]  < 60) |
        (mf["avg_attendance"] < 65) |
        (mf["avg_rating"]     < 3.5)
    )

    apoyo = mf[mf["necesita_apoyo"]].copy()
    excelentes = mf[mf["score_pedagogico"] >= 75].copy()

    col_ap, col_ex = st.columns(2)

    with col_ap:
        st.markdown(f"""
        <div style="background:rgba(230,57,70,.08); border:1px solid rgba(230,57,70,.25);
                    border-radius:12px; padding:16px 20px; margin-bottom:12px;">
            <div style="font-size:0.85rem; font-weight:700; color:{COLOR_PRIMARY}; margin-bottom:8px;">
                🔴 Docentes que requieren acompañamiento ({len(apoyo)})
            </div>
            <div style="font-size:0.75rem; color:#8892a4;">
                Criterio: aprobación &lt;60% · asistencia &lt;65% · satisfacción &lt;3.5
            </div>
        </div>""", unsafe_allow_html=True)
        if not apoyo.empty:
            for _, r in apoyo.iterrows():
                flags = []
                if r["approval_rate"]  < 60: flags.append("📉 Baja aprobación")
                if r["avg_attendance"] < 65: flags.append("📅 Baja asistencia")
                if r["avg_rating"]     < 3.5: flags.append("⭐ Baja satisfacción")
                st.markdown(f"""
                <div style="background:#13131F; border:1px solid #1e1e30; border-radius:10px;
                            padding:12px 16px; margin-bottom:8px;">
                    <strong style="color:#EAEAEA;">{r['full_name']}</strong>
                    <span style="color:#6a7280; font-size:0.78rem;"> · {r.get('department','—')}</span><br>
                    <span style="font-size:0.78rem; color:{COLOR_PRIMARY};">{" &nbsp; ".join(flags)}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.success("✅ Ningún docente requiere intervención con los filtros actuales.")

    with col_ex:
        st.markdown(f"""
        <div style="background:rgba(42,157,143,.08); border:1px solid rgba(42,157,143,.25);
                    border-radius:12px; padding:16px 20px; margin-bottom:12px;">
            <div style="font-size:0.85rem; font-weight:700; color:{COLOR_SUCCESS}; margin-bottom:8px;">
                🟢 Docentes destacados — Buenas prácticas ({len(excelentes)})
            </div>
            <div style="font-size:0.75rem; color:#8892a4;">
                Criterio: score pedagógico ≥ 75
            </div>
        </div>""", unsafe_allow_html=True)
        if not excelentes.empty:
            for _, r in excelentes.iterrows():
                st.markdown(f"""
                <div style="background:#13131F; border:1px solid #1e1e30; border-radius:10px;
                            padding:12px 16px; margin-bottom:8px;">
                    <strong style="color:#EAEAEA;">{r['full_name']}</strong>
                    <span style="color:#6a7280; font-size:0.78rem;"> · {r.get('department','—')}</span><br>
                    <span style="font-size:0.78rem; color:{COLOR_SUCCESS};">
                        ✅ Aprobación: {r['approval_rate']:.1f}% &nbsp;·&nbsp;
                        ⭐ {r['avg_rating']:.2f}/5 &nbsp;·&nbsp;
                        Score: {r['score_pedagogico']}
                    </span>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("ℹ️ No hay docentes destacados con los filtros aplicados.")

    # ════════════════════════════════════════
    #  SECCIÓN 6 · TABLA COMPLETA
    # ════════════════════════════════════════
    _section("📋 Tabla Completa de Docentes")

    display_cols = {
        "full_name":         "Docente",
        "department":        "Departamento",
        "n_courses":         "Cursos",
        "n_students":        "Estudiantes",
        "approval_rate":     "Aprobación %",
        "avg_grade":         "Nota Prom.",
        "avg_attendance":    "Asistencia %",
        "avg_rating":        "Satisfacción",
        "dropout_rate":      "Deserción %",
        "score_pedagogico":  "Score",
    }
    table = mf[list(display_cols.keys())].rename(columns=display_cols)

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score Pedagógico", min_value=0, max_value=100, format="%.1f"),
            "Satisfacción": st.column_config.NumberColumn("Satisfacción", format="%.2f ⭐"),
            "Aprobación %": st.column_config.NumberColumn("Aprobación %", format="%.1f%%"),
            "Asistencia %": st.column_config.NumberColumn("Asistencia %", format="%.1f%%"),
        }
    )

    # ── Footer ─────────────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:0.75rem; color:#4a5568; text-align:center; padding:12px 0;'>"
        f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')} &nbsp;·&nbsp; MongoDB &nbsp;·&nbsp; "
        f"Score = 35% aprobación + 25% nota + 20% asistencia + 20% satisfacción</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
#  EJECUCIÓN STANDALONE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(page_title="Rendimiento Docente", page_icon="👨‍🏫", layout="wide")
    if "active_page" not in st.session_state:
        st.session_state.active_page = "👨‍🏫  Rendimiento Docente"
    show()
