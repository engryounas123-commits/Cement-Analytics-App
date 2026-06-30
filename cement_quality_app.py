
"""
Cement Quality Analytics Dashboard App
======================================
Supports: Raw Meal, Clinker (OPC), and Cement data analysis
Modules: Trends, KPIs, Coating Index, Strength Prediction, Cost, Kiln Feed/Coal
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="Cement Quality Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================== CUSTOM CSS =====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1e3a5f;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
    }
    .kpi-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        border-radius: 12px;
        padding: 1.2rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: #fbbf24;
    }
    .kpi-label {
        font-size: 0.9rem;
        color: #cbd5e1;
        margin-top: 0.3rem;
    }
    .recommendation-box {
        background: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
    }
    .section-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1e3a5f;
        margin: 1.5rem 0 1rem 0;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ===================== HELPER FUNCTIONS =====================

def detect_material_type(df):
    cols = [c.upper() for c in df.columns]
    col_str = ' '.join(cols)
    clinker_indicators = ['C3S', 'C2S', 'C3A', 'C4AF', 'LIQ_PHASE', 'LIQUID', 'F_CAO', 'FREE CAO', 'LSF', 'CLINKER']
    rawmeal_indicators = ['LOI', 'RAW', 'MOISTURE', 'COMBINED', 'HOMOGENEITY']
    cement_indicators = ['BLAINE', 'FINENESS', 'SOUNDNESS', 'SETTING', 'INITIAL', 'FINAL', 'COMPRESSIVE', '3DAY', '7DAY', '28DAY']
    clinker_score = sum(1 for ind in clinker_indicators if ind in col_str)
    rawmeal_score = sum(1 for ind in rawmeal_indicators if ind in col_str)
    cement_score = sum(1 for ind in cement_indicators if ind in col_str)
    scores = {'Clinker': clinker_score, 'Raw Meal': rawmeal_score, 'Cement': cement_score}
    detected = max(scores, key=scores.get)
    if scores[detected] == 0:
        if 'LSF' in col_str and 'C3S' not in col_str:
            detected = 'Raw Meal'
        elif 'LSF' in col_str:
            detected = 'Clinker'
        else:
            detected = 'Unknown'
    return detected


def calc_cpk(data, target, usl, lsl):
    mean = data.mean()
    std = data.std()
    if std == 0 or pd.isna(std):
        return np.inf, np.inf, mean, std
    cpu = (usl - mean) / (3 * std)
    cpl = (mean - lsl) / (3 * std)
    cpk = min(cpu, cpl)
    cp = (usl - lsl) / (6 * std)
    return cp, cpk, mean, std


def predict_strength(c3s, c2s, c3a, f_cao, lsf):
    base_strength = 35.0
    c3s_contrib = (c3s - 45) * 0.85
    c2s_contrib = (c2s - 25) * 0.25
    c3a_contrib = (c3a - 7) * 0.5
    f_cao_penalty = max(0, f_cao - 1.0) * (-3.0)
    lsf_bonus = (lsf - 90) * 0.3
    predicted = base_strength + c3s_contrib + c2s_contrib + c3a_contrib + f_cao_penalty + lsf_bonus
    return max(30, min(65, predicted))


def calc_coating_index(liquid_phase, c3a, c4af):
    if c4af == 0:
        return 0
    ratio = c3a / c4af
    return (liquid_phase * ratio) / 10


def calc_burnability_index(f_cao, lsf):
    return f_cao * lsf / 100


def calc_quality_index(df):
    scores = []
    if 'LSF' in df.columns:
        lsf_score = 100 - abs(df['LSF'] - 92.0) * 5
        scores.append(lsf_score * 0.30)
    if 'SM' in df.columns:
        sm_score = 100 - abs(df['SM'] - 2.25) * 100
        scores.append(sm_score * 0.25)
    if 'AM' in df.columns:
        am_score = 100 - abs(df['AM'] - 1.30) * 100
        scores.append(am_score * 0.20)
    if 'F_CaO' in df.columns or 'F-CaO' in df.columns:
        f_col = 'F_CaO' if 'F_CaO' in df.columns else 'F-CaO'
        f_score = 100 - (df[f_col] - 1.2).clip(lower=0) * 50
        scores.append(f_score * 0.25)
    if not scores:
        return pd.Series([75] * len(df))
    total = sum(scores)
    return total.clip(0, 100)


def generate_report(df, material_type, specs):
    report = []
    report.append("=" * 80)
    report.append("CEMENT QUALITY ANALYTICS REPORT - " + material_type.upper())
    report.append("=" * 80)
    report.append("Samples Analyzed: " + str(len(df)))
    report.append("")
    report.append("PARAMETER SUMMARY")
    report.append("-" * 80)
    for col in df.select_dtypes(include=[np.number]).columns:
        if col in ['Quality_Index', 'Coating_Index', 'Burnability_Index']:
            continue
        mean = df[col].mean()
        std = df[col].std()
        cv = (std/mean*100 if mean != 0 else 0)
        report.append(f"{col:<20} Mean: {mean:>10.3f}   Std: {std:>10.3f}   CV: {cv:>6.2f}%")
    report.append("")
    report.append("PROCESS CAPABILITY")
    report.append("-" * 80)
    for param, spec in specs.items():
        if param in df.columns:
            cp, cpk, mean, std = calc_cpk(df[param], spec['target'], spec['usl'], spec['lsl'])
            status = 'Excellent' if cpk >= 1.33 else 'Capable' if cpk >= 1.0 else 'Marginal' if cpk >= 0.67 else 'Poor'
            report.append(f"{param:<15} Cp: {cp:>6.2f}   Cpk: {cpk:>6.2f}   Status: {status}")
    if 'Quality_Index' in df.columns:
        report.append("")
        report.append(f"QUALITY INDEX: {df['Quality_Index'].mean():.2f}/100")
    if 'Coating_Index' in df.columns:
        report.append("")
        report.append(f"COATING INDEX: {df['Coating_Index'].mean():.3f} (Range: {df['Coating_Index'].min():.3f} - {df['Coating_Index'].max():.3f})")
    report.append("")
    report.append("=" * 80)
    return "\n".join(report)


def get_download_link(df, filename="analysis_report.csv"):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" style="text-decoration:none;"><button style="background:#3b82f6;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;">📥 Download CSV Report</button></a>'
    return href


# ===================== MAIN APP =====================

def main():
    st.markdown('<div class="main-header">🏭 Cement Quality Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Intelligent analysis for Raw Meal, Clinker, and Cement data</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.title("📁 Data Upload")
        uploaded_file = st.file_uploader(
            "Drop your Excel/CSV file here",
            type=['csv', 'xlsx', 'xls'],
            help="Upload Raw Meal, Clinker, or Cement control register data"
        )
        st.markdown("---")
        st.markdown("### 📋 Supported Formats")
        st.markdown("- **CSV** (.csv)")
        st.markdown("- **Excel** (.xlsx, .xls)")
        st.markdown("---")
        st.markdown("### 🏷️ Auto-Detection")
        st.markdown("The app automatically detects material type based on column headers:")
        st.markdown("- **Clinker**: C3S, C2S, C3A, C4AF, LSF, SM, AM, F-CaO")
        st.markdown("- **Raw Meal**: LOI, LSF, SM, AM (pre-calcination)")
        st.markdown("- **Cement**: Blaine, Fineness, Setting Time, Compressive Strength")
        st.markdown("---")
        st.markdown("### ⚙️ Analysis Modules")
        st.markdown("✅ Trend Analysis")
        st.markdown("✅ Process KPIs & Cp/Cpk")
        st.markdown("✅ Coating Index")
        st.markdown("✅ Strength Prediction")
        st.markdown("✅ Cost Metrics")
        st.markdown("✅ Kiln Feed & Coal Trends")
        st.markdown("✅ Auto-Report Generation")

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            df.columns = df.columns.str.strip()
            material_type = detect_material_type(df)
            time_cols = [c for c in df.columns if any(x in c.upper() for x in ['TIME', 'DATE', 'HOUR', 'SHIFT'])]
            if time_cols:
                df = df.rename(columns={time_cols[0]: 'Time'})

            st.success(f"✅ File loaded! Detected material type: **{material_type}**")

            col_mapping = {
                'F-CaO': 'F_CaO', 'Free CaO': 'F_CaO', 'FreeCaO': 'F_CaO',
                'Liq.Phase': 'Liq_phase', 'Liquid Phase': 'Liq_phase', 'LIQ PHASE': 'Liq_phase',
                'C3S': 'C3S', 'C2S': 'C2S', 'C3A': 'C3A', 'C4AF': 'C4AF',
                'Temp': 'Temp', 'Temperature': 'Temp'
            }
            df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})

            if all(c in df.columns for c in ['Liq_phase', 'C3A', 'C4AF']):
                df['Coating_Index'] = calc_coating_index(df['Liq_phase'], df['C3A'], df['C4AF'])
            if all(c in df.columns for c in ['F_CaO', 'LSF']):
                df['Burnability_Index'] = calc_burnability_index(df['F_CaO'], df['LSF'])
            df['Quality_Index'] = calc_quality_index(df)

            if material_type == 'Clinker' and all(c in df.columns for c in ['C3S', 'C2S', 'C3A', 'F_CaO', 'LSF']):
                df['Predicted_Strength_28D'] = df.apply(
                    lambda row: predict_strength(row['C3S'], row['C2S'], row['C3A'], row['F_CaO'], row['LSF']), axis=1
                )

            if material_type == 'Clinker':
                specs = {
                    'LSF': {'target': 92.0, 'usl': 96.0, 'lsl': 88.0},
                    'SM': {'target': 2.25, 'usl': 2.50, 'lsl': 2.00},
                    'AM': {'target': 1.30, 'usl': 1.50, 'lsl': 1.10},
                    'F_CaO': {'target': 1.0, 'usl': 1.5, 'lsl': 0.0},
                    'C3S': {'target': 50.0, 'usl': 55.0, 'lsl': 45.0},
                    'Liq_phase': {'target': 28.0, 'usl': 30.0, 'lsl': 26.0}
                }
            elif material_type == 'Raw Meal':
                specs = {
                    'LSF': {'target': 92.0, 'usl': 96.0, 'lsl': 88.0},
                    'SM': {'target': 2.25, 'usl': 2.50, 'lsl': 2.00},
                    'AM': {'target': 1.30, 'usl': 1.50, 'lsl': 1.10},
                    'LOI': {'target': 35.0, 'usl': 38.0, 'lsl': 32.0}
                }
            else:
                specs = {
                    'Blaine': {'target': 350, 'usl': 400, 'lsl': 300},
                    'SO3': {'target': 2.5, 'usl': 3.0, 'lsl': 2.0}
                }

            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "📊 Overview & KPIs",
                "📈 Trends & Control",
                "🔬 Process Capability",
                "🎯 Coating & Burnability",
                "💰 Cost & Operations",
                "📄 Report & Export"
            ])

            # ========== TAB 1: OVERVIEW & KPIs ==========
            with tab1:
                st.markdown('<div class="section-title">📊 Key Performance Indicators</div>', unsafe_allow_html=True)
                kpi_cols = st.columns(6)
                kpi_data = []
                if 'LSF' in df.columns:
                    kpi_data.append(("Avg LSF", f"{df['LSF'].mean():.2f}", "Target: 92.0"))
                if 'SM' in df.columns:
                    kpi_data.append(("Avg SM", f"{df['SM'].mean():.2f}", "Target: 2.25"))
                if 'AM' in df.columns:
                    kpi_data.append(("Avg AM", f"{df['AM'].mean():.2f}", "Target: 1.30"))
                if 'C3S' in df.columns:
                    kpi_data.append(("Avg C3S", f"{df['C3S'].mean():.1f}%", "Target: 50%"))
                if 'F_CaO' in df.columns:
                    kpi_data.append(("Avg F-CaO", f"{df['F_CaO'].mean():.2f}%", "Target: <1.2%"))
                if 'Quality_Index' in df.columns:
                    kpi_data.append(("Quality Index", f"{df['Quality_Index'].mean():.1f}", "Score: 0-100"))

                for i, (label, value, subtext) in enumerate(kpi_data[:6]):
                    with kpi_cols[i]:
                        st.markdown(f'<div class="kpi-card"><div style="font-size:0.9rem; color:#94a3b8;">{label}</div><div class="kpi-value">{value}</div><div style="font-size:0.75rem; color:#64748b; margin-top:0.3rem;">{subtext}</div></div>', unsafe_allow_html=True)

                st.markdown("---")
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown('<div class="section-title">📋 Data Preview</div>', unsafe_allow_html=True)
                    st.dataframe(df.head(20), use_container_width=True, height=400)
                with col2:
                    st.markdown('<div class="section-title">📊 Statistics</div>', unsafe_allow_html=True)
                    st.dataframe(df.describe().round(3), use_container_width=True, height=400)

                st.markdown('<div class="section-title">🎯 Overall Assessment</div>', unsafe_allow_html=True)
                if 'Quality_Index' in df.columns:
                    q_mean = df['Quality_Index'].mean()
                    if q_mean >= 97:
                        grade, color = "EXCELLENT", "#10b981"
                    elif q_mean >= 95:
                        grade, color = "GOOD", "#3b82f6"
                    elif q_mean >= 93:
                        grade, color = "ACCEPTABLE", "#f59e0b"
                    else:
                        grade, color = "NEEDS IMPROVEMENT", "#ef4444"
                    st.markdown(f'<div style="background: linear-gradient(135deg, {color}22 0%, {color}11 100%); border: 2px solid {color}; border-radius: 12px; padding: 1.5rem; text-align: center;"><div style="font-size: 1.2rem; color: {color}; font-weight: 700;">OVERALL GRADE: {grade}</div><div style="font-size: 2.5rem; color: {color}; font-weight: 800; margin: 0.5rem 0;">{q_mean:.1f}/100</div><div style="color: #64748b;">Quality Index Score</div></div>', unsafe_allow_html=True)

            # ========== TAB 2: TRENDS & CONTROL ==========
            with tab2:
                st.markdown('<div class="section-title">📈 Parameter Trends with Control Limits</div>', unsafe_allow_html=True)
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                exclude = ['Quality_Index', 'Coating_Index', 'Burnability_Index', 'Predicted_Strength_28D']
                plot_cols = [c for c in numeric_cols if c not in exclude]
                selected_params = st.multiselect("Select parameters to visualize:", plot_cols, default=plot_cols[:4] if len(plot_cols) >= 4 else plot_cols)

                if selected_params:
                    x_col = df['Time'] if 'Time' in df.columns else df.index
                    fig = make_subplots(rows=(len(selected_params) + 1) // 2, cols=2, subplot_titles=selected_params, vertical_spacing=0.1)
                    for i, param in enumerate(selected_params):
                        row = i // 2 + 1
                        col = i % 2 + 1
                        fig.add_trace(go.Scatter(x=x_col, y=df[param], mode='lines+markers', name=param, line=dict(width=2)), row=row, col=col)
                        if param in specs:
                            fig.add_hline(y=specs[param]['target'], line_dash="dash", line_color="#f59e0b", row=row, col=col)
                            fig.add_hline(y=specs[param]['usl'], line_dash="dot", line_color="#ef4444", row=row, col=col)
                            fig.add_hline(y=specs[param]['lsl'], line_dash="dot", line_color="#ef4444", row=row, col=col)
                    fig.update_layout(height=300 * ((len(selected_params) + 1) // 2), showlegend=False, template="plotly_white", title_text="24-Hour Trend Analysis with Control Limits")
                    st.plotly_chart(fig, use_container_width=True)

                if material_type == 'Clinker' and all(c in df.columns for c in ['C3S', 'C2S', 'C3A', 'C4AF']):
                    st.markdown('<div class="section-title">🧪 Mineral Phase Composition</div>', unsafe_allow_html=True)
                    fig = go.Figure()
                    colors_min = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
                    minerals = ['C3S', 'C2S', 'C3A', 'C4AF']
                    for mineral, color in zip(minerals, colors_min):
                        fig.add_trace(go.Scatter(x=x_col, y=df[mineral], mode='lines', stackgroup='one', name=mineral, line=dict(width=0.5, color=color), fillcolor=color))
                    fig.update_layout(title="Mineral Phase Stacked Area", yaxis_title="Weight %", template="plotly_white", height=500)
                    st.plotly_chart(fig, use_container_width=True)

            # ========== TAB 3: PROCESS CAPABILITY ==========
            with tab3:
                st.markdown('<div class="section-title">🔬 Process Capability Analysis (Cp / Cpk)</div>', unsafe_allow_html=True)
                capability_data = []
                for param, spec in specs.items():
                    if param in df.columns:
                        cp, cpk, mean, std = calc_cpk(df[param], spec['target'], spec['usl'], spec['lsl'])
                        status = 'Excellent' if cpk >= 1.33 else 'Capable' if cpk >= 1.0 else 'Marginal' if cpk >= 0.67 else 'Poor'
                        capability_data.append({'Parameter': param, 'Mean': f"{mean:.3f}", 'Std Dev': f"{std:.3f}", 'Cp': f"{cp:.2f}", 'Cpk': f"{cpk:.2f}", 'Status': status})
                if capability_data:
                    cap_df = pd.DataFrame(capability_data)
                    def color_status(val):
                        if val == 'Excellent': return 'background-color: #10b981; color: white'
                        elif val == 'Capable': return 'background-color: #3b82f6; color: white'
                        elif val == 'Marginal': return 'background-color: #f59e0b; color: white'
                        else: return 'background-color: #ef4444; color: white'
                    st.dataframe(cap_df.style.applymap(color_status, subset=['Status']), use_container_width=True)
                    fig = px.bar(cap_df, x='Parameter', y='Cpk', color='Status', color_discrete_map={'Excellent': '#10b981', 'Capable': '#3b82f6', 'Marginal': '#f59e0b', 'Poor': '#ef4444'}, title="Process Capability Index (Cpk) by Parameter", template="plotly_white")
                    fig.add_hline(y=1.33, line_dash="dash", line_color="#10b981", annotation_text="Excellent")
                    fig.add_hline(y=1.0, line_dash="dash", line_color="#3b82f6", annotation_text="Capable")
                    fig.add_hline(y=0.67, line_dash="dash", line_color="#f59e0b", annotation_text="Marginal")
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown('<div class="section-title">📊 Parameter Variability (CV %)</div>', unsafe_allow_html=True)
                cv_data = []
                for col in plot_cols:
                    mean = df[col].mean()
                    if mean != 0:
                        cv = (df[col].std() / mean) * 100
                        cv_data.append({'Parameter': col, 'CV_%': cv})
                if cv_data:
                    cv_df = pd.DataFrame(cv_data).sort_values('CV_%', ascending=True)
                    fig = px.bar(cv_df, x='CV_%', y='Parameter', orientation='h', color='CV_%', color_continuous_scale='RdYlGn_r', title="Coefficient of Variation by Parameter", template="plotly_white")
                    fig.add_vline(x=1.0, line_dash="dash", line_color="#ef4444", annotation_text="Target <1%")
                    st.plotly_chart(fig, use_container_width=True)

            # ========== TAB 4: COATING & BURNABILITY ==========
            with tab4:
                st.markdown('<div class="section-title">🎯 Coating Index & Burnability Analysis</div>', unsafe_allow_html=True)
                if 'Coating_Index' in df.columns:
                    col1, col2, col3 = st.columns(3)
                    with col1: st.metric("Avg Coating Index", f"{df['Coating_Index'].mean():.3f}")
                    with col2: st.metric("Max Coating Index", f"{df['Coating_Index'].max():.3f}")
                    with col3:
                        risk = "LOW" if df['Coating_Index'].mean() < 1.55 else "MODERATE" if df['Coating_Index'].mean() < 1.65 else "HIGH"
                        st.metric("Coating Risk", risk)
                    x_col = df['Time'] if 'Time' in df.columns else df.index
                    fig = px.bar(df, x=x_col, y='Coating_Index', color='Coating_Index', color_continuous_scale='YlOrRd', title="Coating Index by Time", template="plotly_white")
                    fig.add_hline(y=1.55, line_dash="dash", line_color="#f59e0b", annotation_text="Moderate Risk")
                    fig.add_hline(y=1.65, line_dash="dash", line_color="#ef4444", annotation_text="High Risk")
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown("**Coating Index Interpretation:**<br>- **< 1.55**: Low coating tendency<br>- **1.55 – 1.65**: Moderate coating tendency<br>- **> 1.65**: High coating tendency — increased ring risk", unsafe_allow_html=True)
                else:
                    st.info("Coating Index requires Liq_phase, C3A, and C4AF columns.")

                if 'Burnability_Index' in df.columns:
                    st.markdown('<div class="section-title">🔥 Burnability Index</div>', unsafe_allow_html=True)
                    x_col = df['Time'] if 'Time' in df.columns else df.index
                    fig = px.line(df, x=x_col, y='Burnability_Index', markers=True, title="Burnability Index Trend (F-CaO x LSF / 100)", template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown("Lower burnability index indicates better clinker burnability.")

                if 'Predicted_Strength_28D' in df.columns:
                    st.markdown('<div class="section-title">💪 Predicted 28-Day Compressive Strength</div>', unsafe_allow_html=True)
                    x_col = df['Time'] if 'Time' in df.columns else df.index
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=x_col, y=df['Predicted_Strength_28D'], mode='lines+markers', name='Predicted Strength', line=dict(color='#3b82f6', width=3)))
                    fig.add_hline(y=42.5, line_dash="dash", line_color="#10b981", annotation_text="OPC 42.5 Target")
                    fig.add_hline(y=52.5, line_dash="dash", line_color="#8b5cf6", annotation_text="OPC 52.5 Target")
                    fig.update_layout(title="Expected 28-Day Compressive Strength (MPa)", yaxis_title="Strength (MPa)", template="plotly_white", height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown(f'<div class="recommendation-box"><strong>Strength Prediction:</strong><br>Predicted 28-day strength ranges from <strong>{df["Predicted_Strength_28D"].min():.1f} to {df["Predicted_Strength_28D"].max():.1f} MPa</strong> (Avg: <strong>{df["Predicted_Strength_28D"].mean():.1f} MPa</strong>).<br>To increase strength: Increase LSF toward 92.0 and reduce Free CaO below 1.2%.</div>', unsafe_allow_html=True)

            # ========== TAB 5: COST & OPERATIONS ==========
            with tab5:
                st.markdown('<div class="section-title">💰 Cost & Operational Metrics</div>', unsafe_allow_html=True)
                st.markdown("### 🏭 Kiln Feed & Coal Trend Simulator")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Fuel Efficiency Metrics**")
                    if 'F_CaO' in df.columns:
                        x_col = df['Time'] if 'Time' in df.columns else df.index
                        fuel_eff = 100 - (df['F_CaO'] - 1.0).clip(lower=0) * 20
                        fig = px.line(x=x_col, y=fuel_eff, markers=True, title="Fuel Efficiency Index (%)", labels={'y': 'Efficiency %', 'x': 'Time'}, template="plotly_white")
                        fig.add_hline(y=95, line_dash="dash", line_color="#10b981")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("F-CaO data required for fuel efficiency calculation.")
                with col2:
                    st.markdown("**Raw Material Utilization**")
                    if 'LSF' in df.columns:
                        x_col = df['Time'] if 'Time' in df.columns else df.index
                        rm_eff = 100 - abs(df['LSF'] - 92.0) * 2
                        fig = px.line(x=x_col, y=rm_eff, markers=True, title="Raw Material Efficiency (%)", labels={'y': 'Efficiency %', 'x': 'Time'}, template="plotly_white")
                        fig.add_hline(y=95, line_dash="dash", line_color="#10b981")
                        st.plotly_chart(fig, use_container_width=True)

                st.markdown("### 📊 Cost Impact Calculator")
                col1, col2, col3 = st.columns(3)
                with col1: coal_price = st.number_input("Coal Price ($/ton)", value=120.0, step=5.0)
                with col2: limestone_price = st.number_input("Limestone Price ($/ton)", value=15.0, step=1.0)
                with col3: daily_production = st.number_input("Daily Production (tons)", value=3000.0, step=100.0)

                if 'F_CaO' in df.columns and 'LSF' in df.columns:
                    avg_f_cao = df['F_CaO'].mean()
                    avg_lsf = df['LSF'].mean()
                    excess_fuel = max(0, avg_f_cao - 1.0) * 0.05 * daily_production
                    fuel_cost_impact = excess_fuel * coal_price / 1000
                    lsf_deviation = abs(avg_lsf - 92.0)
                    raw_material_waste = lsf_deviation * 0.02 * daily_production * limestone_price / 1000
                    total_daily_cost = fuel_cost_impact + raw_material_waste
                    st.markdown(f'<div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 1rem; margin-top: 1rem;"><h4 style="color: #92400e; margin-top: 0;">💡 Estimated Daily Cost Impact</h4><p><strong>Excess Fuel Cost:</strong> ${fuel_cost_impact:.2f}/day (F-CaO = {avg_f_cao:.2f}%)</p><p><strong>Raw Material Waste:</strong> ${raw_material_waste:.2f}/day (LSF deviation = {lsf_deviation:.2f})</p><p style="font-size: 1.2rem; color: #92400e; font-weight: bold;">Total Estimated Impact: ${total_daily_cost:.2f}/day</p><p style="font-size: 1rem; color: #92400e;">Annual Impact: ~${total_daily_cost * 365:,.0f}/year</p></div>', unsafe_allow_html=True)

                if 'Temp' in df.columns and 'F_CaO' in df.columns:
                    st.markdown("### 🌡️ Temperature vs Free CaO Correlation")
                    fig = px.scatter(df, x='Temp', y='F_CaO', trendline="ols", title="Kiln Temperature vs Free CaO Relationship", template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)
                    corr = df['Temp'].corr(df['F_CaO'])
                    st.markdown(f"**Correlation Coefficient:** {corr:.3f}")
                    if corr < -0.3:
                        st.success("Strong negative correlation: Higher temperatures reduce Free CaO.")
                    elif corr > 0.3:
                        st.warning("Positive correlation detected — investigate kiln operation.")
                    else:
                        st.info("Weak correlation — other factors dominate Free CaO variation.")

            # ========== TAB 6: REPORT & EXPORT ==========
            with tab6:
                st.markdown('<div class="section-title">📄 Comprehensive Analysis Report</div>', unsafe_allow_html=True)
                report_text = generate_report(df, material_type, specs)
                st.text_area("Generated Report", report_text, height=500)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(get_download_link(df, f"{material_type.lower()}_analysis_data.csv"), unsafe_allow_html=True)
                with col2:
                    b64 = base64.b64encode(report_text.encode()).decode()
                    href = f'<a href="data:file/txt;base64,{b64}" download="{material_type.lower()}_quality_report.txt" style="text-decoration:none;"><button style="background:#10b981;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;">📥 Download Text Report</button></a>'
                    st.markdown(href, unsafe_allow_html=True)

                st.markdown('<div class="section-title">🎯 Actionable Recommendations</div>', unsafe_allow_html=True)
                recommendations = []
                if 'LSF' in df.columns:
                    lsf_mean = df['LSF'].mean()
                    if lsf_mean < 91.8:
                        recommendations.append(f"🔴 **Increase LSF:** Current {lsf_mean:.2f} is below target 92.0. Add 0.5-1.0% limestone to raw mix.")
                    elif lsf_mean > 92.5:
                        recommendations.append(f"🟡 **Decrease LSF:** Current {lsf_mean:.2f} is above optimal. Reduce limestone slightly.")
                    else:
                        recommendations.append(f"🟢 **LSF Optimal:** Current {lsf_mean:.2f} is well-controlled.")
                if 'F_CaO' in df.columns:
                    f_mean = df['F_CaO'].mean()
                    if f_mean > 1.3:
                        recommendations.append(f"🔴 **Reduce Free CaO:** Current {f_mean:.2f}% is high. Optimize burn zone temp or raw meal fineness.")
                    elif f_mean > 1.1:
                        recommendations.append(f"🟡 **Monitor Free CaO:** Current {f_mean:.2f}% is acceptable but can be improved.")
                    else:
                        recommendations.append(f"🟢 **Free CaO Excellent:** Current {f_mean:.2f}% indicates good burnability.")
                if 'Coating_Index' in df.columns:
                    ci_mean = df['Coating_Index'].mean()
                    if ci_mean > 1.65:
                        recommendations.append(f"🔴 **High Coating Risk:** Index {ci_mean:.2f}. Inspect kiln for ring formation.")
                    elif ci_mean > 1.55:
                        recommendations.append(f"🟡 **Moderate Coating:** Index {ci_mean:.2f}. Maintain regular kiln inspection schedule.")
                    else:
                        recommendations.append(f"🟢 **Low Coating Risk:** Index {ci_mean:.2f}. Kiln operation is safe.")
                if 'C3S' in df.columns:
                    c3s_mean = df['C3S'].mean()
                    if c3s_mean < 48:
                        recommendations.append(f"🔴 **Low C3S:** {c3s_mean:.1f}% may result in lower early strength. Increase LSF and burning intensity.")
                    elif c3s_mean < 50:
                        recommendations.append(f"🟡 **C3S Acceptable:** {c3s_mean:.1f}%. Slight increase in LSF will optimize strength.")
                    else:
                        recommendations.append(f"🟢 **C3S Excellent:** {c3s_mean:.1f}% supports high early strength development.")
                for rec in recommendations:
                    st.markdown(f'<div class="recommendation-box">{rec}</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.info("Please ensure your file has proper column headers matching standard cement terminology.")

    else:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">📤</div>
            <h2 style="color: #1e3a5f;">Upload Your Data to Begin Analysis</h2>
            <p style="color: #64748b; font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
                Drop an Excel or CSV file containing your Raw Meal, Clinker, or Cement control data.
                The app will automatically detect the material type and generate comprehensive analytics.
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**📋 Clinker Expected Columns:**<br>- Time, SiO2, Al2O3, Fe2O3, CaO, MgO<br>- K2O, Na2O, SO3, LSF, SM, AM<br>- C3S, C2S, C3A, C4AF, Liq_phase<br>- F_CaO, Temp, Litre_Weight", unsafe_allow_html=True)
        with col2:
            st.markdown("**📋 Raw Meal Expected Columns:**<br>- Time, SiO2, Al2O3, Fe2O3, CaO, MgO<br>- LOI, LSF, SM, AM, Moisture<br>- Homogeneity_Index", unsafe_allow_html=True)
        with col3:
            st.markdown("**📋 Cement Expected Columns:**<br>- Time, Blaine, SO3, Setting_Time<br>- 3Day_Strength, 7Day_Strength, 28Day_Strength<br>- Soundness, Fineness, LOI", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
