#  built by nnnsightnnn — signal from noise
"""
v0.5 — Web Dashboard
=====================
Run with:  python3 -m streamlit run dashboard.py
"""

import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from sir_model import DiffusionParams, run_sir, summarize
from monte_carlo import run_monte_carlo
from presets import PRESETS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Info Diffusion Simulator",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Colour palette ────────────────────────────────────────────────────────────
C_BLUE, C_ORANGE, C_GREEN = "#4C9BE8", "#F28B30", "#2ECC71"
C_RED,  C_PURPLE, C_TEAL  = "#E74C3C", "#9B59B6", "#1ABC9C"
PLOT_BG, PAPER_BG          = "#1A1D27", "#0F1117"
GRID_CLR, TEXT_CLR         = "#2A2D3A", "#E8EAF0"

LAYOUT_BASE = dict(
    plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
    font=dict(color=TEXT_CLR, family="Inter, sans-serif"),
    xaxis=dict(gridcolor=GRID_CLR, zerolinecolor=GRID_CLR),
    yaxis=dict(gridcolor=GRID_CLR, zerolinecolor=GRID_CLR),
    margin=dict(l=50, r=20, t=50, b=50),
    legend=dict(bgcolor=PLOT_BG, bordercolor=GRID_CLR, borderwidth=1),
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📡 Info Diffusion")
    st.caption("Model how a video's information spreads through a population")
    st.divider()

    # Preset buttons — clicking one stores values into session state
    st.subheader("⚡ Presets")
    cols = st.columns(2)
    for i, p in enumerate(PRESETS):
        if cols[i % 2].button(p.display, use_container_width=True, key=f"preset_{i}"):
            for k, v in p.params().items():
                st.session_state[f"p_{k}"] = v

    st.divider()
    st.subheader("🎛️ Parameters")

    def _get(key, default):
        return st.session_state.get(f"p_{key}", default)

    seed_viewers      = st.number_input("Seed viewers", 1, 10_000_000, step=10,
                            value=_get("seed_viewers", 10), key="p_seed_viewers",
                            help="How many people watched the video at launch")
    population_size   = st.number_input("Population size", 1_000, 500_000_000, step=10_000,
                            value=_get("population_size", 1_000_000), key="p_population_size")
    conversation_rate = st.slider("Conversation rate (people told / day)", 0.1, 10.0, step=0.1,
                            value=float(_get("conversation_rate", 3.0)), key="p_conversation_rate",
                            help="Avg people each informed person tells per day")
    spread_probability = st.slider("Spread probability", 0.01, 1.0, step=0.01,
                            value=float(_get("spread_probability", 0.15)), key="p_spread_probability",
                            help="Chance listener actually cares and shares")
    recovery_rate     = st.slider("Recovery rate (go silent / day)", 0.01, 0.50, step=0.01,
                            value=float(_get("recovery_rate", 0.10)), key="p_recovery_rate")
    days              = st.slider("Days to simulate", 14, 180, value=90, step=1)
    run_mc            = st.toggle("Show Monte Carlo variance", value=True)
    n_trials          = st.slider("MC trials", 50, 500, value=150, step=50, disabled=not run_mc)


# ── Run simulation (once, shared across all tabs) ─────────────────────────────
params = DiffusionParams(
    seed_viewers=int(seed_viewers), population_size=int(population_size),
    conversation_rate=conversation_rate, spread_probability=spread_probability,
    recovery_rate=recovery_rate, days_to_simulate=days,
)
snapshots = run_sir(params)
stats     = summarize(snapshots, params)
N         = params.population_size
r0        = params.R0

xs         = [s.day          for s in snapshots]
pct_reach  = [s.pct_reached  for s in snapshots]
pct_active = [s.pct_active   for s in snapshots]
abs_inf    = [s.informed      for s in snapshots]
abs_reach  = [s.total_reached for s in snapshots]

# Pre-compute MC once so both Tab1 and Tab2 share the same run
mc = None
if run_mc:
    with st.spinner(f"Running {n_trials} Monte Carlo trials..."):
        mc = run_monte_carlo(params, n_trials=n_trials)

# ── Header ────────────────────────────────────────────────────────────────────
verdict = "🔥 VIRAL" if r0 > 1 else "💨 FIZZLE"
st.markdown("## 📡 Info Diffusion Simulator")
st.caption(f"Viral coefficient **R₀ = {r0:.2f}** — {verdict}  ·  "
           f"β = {params.beta:.3f}  ·  γ = {recovery_rate:.2f}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Peak active spreaders", f"{stats['peak_informed']:,}",
          f"day {stats['peak_day']}")
m2.metric("Final reach", f"{stats['final_reach_pct']:.1f}%",
          f"{stats['final_reached']:,} people")
d50 = stats["day_50pct"]
m3.metric("Days to reach 50%", f"Day {d50}" if d50 else "Never")
d10 = stats["day_10pct"]
m4.metric("Days to reach 10%", f"Day {d10}" if d10 else "Never")
st.divider()


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 S-Curve", "🎲 Monte Carlo", "🔬 SIR Breakdown", "⚡ Sensitivity"])

# ═══ TAB 1 — S-Curve ══════════════════════════════════════════════════════════
with tab1:
    fig = go.Figure()

    if mc is not None:
        pct_mat = mc.ever_reached_matrix / N * 100
        p5, p95  = np.percentile(pct_mat, 5, axis=0), np.percentile(pct_mat, 95, axis=0)
        mean_mc  = pct_mat.mean(axis=0)
        fig.add_trace(go.Scatter(
            x=list(xs) + list(xs[::-1]), y=list(p95) + list(p5[::-1]),
            fill="toself", fillcolor="rgba(76,155,232,0.15)",
            line=dict(color="rgba(0,0,0,0)"),
            name="5–95th percentile (MC)", hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(x=xs, y=mean_mc, name="MC mean",
            line=dict(color=C_BLUE, width=2, dash="dot")))

    fig.add_trace(go.Scatter(x=xs, y=pct_reach, name="Deterministic SIR",
        line=dict(color=C_ORANGE, width=3)))
    fig.add_hline(y=50, line_dash="dash", line_color=GRID_CLR,
                  annotation_text="50%", annotation_font_color=TEXT_CLR)
    fig.add_hline(y=90, line_dash="dash", line_color=GRID_CLR,
                  annotation_text="90%", annotation_font_color=TEXT_CLR)
    fig.update_layout(**LAYOUT_BASE,
        title="Information S-Curve — % of population ever reached",
        xaxis_title="Days since release", yaxis_title="% of population ever reached",
        yaxis_ticksuffix="%", yaxis_range=[-2, 103], height=460)
    st.plotly_chart(fig, use_container_width=True)

    if r0 > 1:
        st.success(f"**Viral!** R₀={r0:.2f} — information self-sustains. "
                   f"Peak buzz on day {stats['peak_day']} with {stats['peak_informed']:,} "
                   f"active spreaders simultaneously.")
    else:
        st.warning(f"**Fizzle.** R₀={r0:.2f} < 1 — each spreader infects fewer than one "
                   f"new person. Try raising conversation rate or spread probability.")


# ═══ TAB 2 — Monte Carlo ══════════════════════════════════════════════════════
with tab2:
    if mc is None:
        st.info("Enable **Show Monte Carlo variance** in the sidebar to see this tab.")
    else:
        final_pct = mc.final_reach() / N * 100
        d50_arr   = mc.days_to_pct(50)
        valid_d50 = d50_arr[~np.isnan(d50_arr)]

        col_a, col_b = st.columns(2)
        with col_a:
            fig2a = go.Figure()
            fig2a.add_trace(go.Histogram(x=final_pct, nbinsx=30,
                marker_color=C_BLUE, opacity=0.85, name="% ever reached"))
            fig2a.update_layout(**LAYOUT_BASE,
                title="Distribution of Final Reach Across Trials",
                xaxis_title="% population ever reached", xaxis_ticksuffix="%",
                yaxis_title="# trials", height=360)
            st.plotly_chart(fig2a, use_container_width=True)
            st.caption(f"Mean: **{final_pct.mean():.1f}%** · Std: {final_pct.std():.1f}% · "
                       f"Range: [{final_pct.min():.1f}%, {final_pct.max():.1f}%]")

        with col_b:
            fig2b = go.Figure()
            if len(valid_d50):
                fig2b.add_trace(go.Histogram(x=valid_d50, nbinsx=25,
                    marker_color=C_ORANGE, opacity=0.85, name="days to 50%"))
                fig2b.update_layout(**LAYOUT_BASE,
                    title="Days to Reach 50% of Population",
                    xaxis_title="Days", yaxis_title="# trials", height=360)
                st.plotly_chart(fig2b, use_container_width=True)
                st.caption(f"Mean: **{valid_d50.mean():.1f} days** · Std: {valid_d50.std():.1f} · "
                           f"Range: [{valid_d50.min():.0f}, {valid_d50.max():.0f}]")
            else:
                st.plotly_chart(fig2b.update_layout(**LAYOUT_BASE,
                    title="Days to Reach 50% — Never achieved", height=360),
                    use_container_width=True)
                st.warning("50% reach was never achieved in any trial.")

        st.markdown("#### All trial trajectories (fan chart)")
        fig2c = go.Figure()
        sample_idx = np.random.choice(n_trials, min(80, n_trials), replace=False)
        for i in sample_idx:
            fig2c.add_trace(go.Scatter(
                x=xs, y=mc.ever_reached_matrix[i] / N * 100,
                mode="lines", line=dict(color=C_BLUE, width=0.5),
                opacity=0.2, showlegend=False, hoverinfo="skip"))
        fig2c.add_trace(go.Scatter(x=xs, y=mc.ever_reached_matrix.mean(axis=0) / N * 100,
            name="Mean", line=dict(color=C_ORANGE, width=2.5)))
        fig2c.update_layout(**LAYOUT_BASE,
            title=f"Fan Chart — {min(80, n_trials)} sampled trials",
            xaxis_title="Days", yaxis_title="% ever reached",
            yaxis_ticksuffix="%", height=380)
        st.plotly_chart(fig2c, use_container_width=True)


# ═══ TAB 3 — SIR Compartments ════════════════════════════════════════════════
with tab3:
    col3a, col3b = st.columns(2)
    with col3a:
        sus = [s.susceptible for s in snapshots]
        rec = [s.recovered   for s in snapshots]
        fig3a = go.Figure()
        fig3a.add_trace(go.Scatter(x=xs, y=[v/N*100 for v in sus],
            name="Susceptible (haven't heard)", fill="tozeroy",
            fillcolor="rgba(155,89,182,0.3)", line=dict(color=C_PURPLE, width=1.5)))
        fig3a.add_trace(go.Scatter(x=xs, y=[v/N*100 for v in abs_inf],
            name="Informed (spreading)", fill="tozeroy",
            fillcolor="rgba(76,155,232,0.4)", line=dict(color=C_BLUE, width=2)))
        fig3a.add_trace(go.Scatter(x=xs, y=[v/N*100 for v in rec],
            name="Recovered (silent)", fill="tozeroy",
            fillcolor="rgba(46,204,113,0.3)", line=dict(color=C_GREEN, width=1.5)))
        fig3a.update_layout(**LAYOUT_BASE,
            title="SIR Compartments Over Time",
            xaxis_title="Days", yaxis_title="% of population",
            yaxis_ticksuffix="%", height=400)
        st.plotly_chart(fig3a, use_container_width=True)

    with col3b:
        new_inf = [max(0, abs_reach[i] - abs_reach[i-1]) for i in range(1, len(abs_reach))]
        fig3b = go.Figure()
        fig3b.add_trace(go.Bar(x=xs[1:], y=new_inf,
            marker_color=C_ORANGE, opacity=0.85, name="New people reached / day"))
        fig3b.update_layout(**LAYOUT_BASE,
            title="Daily New People Reached",
            xaxis_title="Days", yaxis_title="New people reached", height=400)
        st.plotly_chart(fig3b, use_container_width=True)

    with st.expander("📋 Raw day-by-day data"):
        import pandas as pd
        df = pd.DataFrame([{
            "Day": s.day, "Susceptible": s.susceptible,
            "Informed": s.informed, "Recovered": s.recovered,
            "% Active": f"{s.pct_active:.3f}%",
            "% Ever Reached": f"{s.pct_reached:.3f}%",
        } for s in snapshots])
        st.dataframe(df, use_container_width=True, hide_index=True)


# ═══ TAB 4 — Sensitivity ══════════════════════════════════════════════════════
with tab4:
    st.markdown("#### How does changing one parameter move the needle?")
    st.caption("All other parameters fixed at sidebar values.")

    s_col1, s_col2 = st.columns(2)

    # Sweep conversation rate
    with s_col1:
        conv_range = np.linspace(0.5, 8.0, 50)
        d50_c, reach_c, r0_c = [], [], []
        for cr in conv_range:
            p = DiffusionParams(seed_viewers=int(seed_viewers),
                population_size=int(population_size), conversation_rate=cr,
                spread_probability=spread_probability, recovery_rate=recovery_rate,
                days_to_simulate=120)
            det = run_sir(p)
            r0_c.append(p.R0)
            crossed = [s.day for s in det if s.pct_reached >= 50]
            d50_c.append(crossed[0] if crossed else 120)
            reach_c.append(det[-1].pct_reached)

        fig4a = make_subplots(specs=[[{"secondary_y": True}]])
        fig4a.add_trace(go.Scatter(x=conv_range, y=d50_c, name="Days to 50%",
            line=dict(color=C_BLUE, width=2.5)), secondary_y=False)
        fig4a.add_trace(go.Scatter(x=conv_range, y=reach_c, name="Final reach %",
            line=dict(color=C_ORANGE, width=2.5)), secondary_y=True)
        fig4a.add_vline(x=conversation_rate, line_dash="dash", line_color=C_GREEN,
            annotation_text=f"current ({conversation_rate})",
            annotation_font_color=C_GREEN)
        fig4a.update_layout(**LAYOUT_BASE, title="Sweep: Conversation Rate",
            xaxis_title="Conversation rate (people told / day)", height=380)
        fig4a.update_yaxes(title_text="Days to 50% reach", secondary_y=False, gridcolor=GRID_CLR)
        fig4a.update_yaxes(title_text="Final % reached", secondary_y=True,
            ticksuffix="%", gridcolor=GRID_CLR)
        st.plotly_chart(fig4a, use_container_width=True)

    # Sweep spread probability
    with s_col2:
        sp_range = np.linspace(0.01, 0.60, 50)
        d50_s, reach_s = [], []
        for sp in sp_range:
            p = DiffusionParams(seed_viewers=int(seed_viewers),
                population_size=int(population_size), conversation_rate=conversation_rate,
                spread_probability=sp, recovery_rate=recovery_rate, days_to_simulate=120)
            det = run_sir(p)
            crossed = [s.day for s in det if s.pct_reached >= 50]
            d50_s.append(crossed[0] if crossed else 120)
            reach_s.append(det[-1].pct_reached)

        fig4b = make_subplots(specs=[[{"secondary_y": True}]])
        fig4b.add_trace(go.Scatter(x=sp_range * 100, y=d50_s, name="Days to 50%",
            line=dict(color=C_BLUE, width=2.5)), secondary_y=False)
        fig4b.add_trace(go.Scatter(x=sp_range * 100, y=reach_s, name="Final reach %",
            line=dict(color=C_ORANGE, width=2.5)), secondary_y=True)
        fig4b.add_vline(x=spread_probability * 100, line_dash="dash", line_color=C_GREEN,
            annotation_text=f"current ({spread_probability:.0%})",
            annotation_font_color=C_GREEN)
        fig4b.update_layout(**LAYOUT_BASE, title="Sweep: Spread Probability",
            xaxis_title="Spread probability (%)", xaxis_ticksuffix="%", height=380)
        fig4b.update_yaxes(title_text="Days to 50% reach", secondary_y=False, gridcolor=GRID_CLR)
        fig4b.update_yaxes(title_text="Final % reached", secondary_y=True,
            ticksuffix="%", gridcolor=GRID_CLR)
        st.plotly_chart(fig4b, use_container_width=True)

    # Seed viewer comparison bar chart
    st.markdown("#### How much does a bigger launch actually matter?")
    seed_opts  = [10, 50, 100, 500, 1_000, 5_000, 10_000, 50_000, 100_000]
    bar_d50, bar_reach, bar_lbl = [], [], []
    for sv in seed_opts:
        p = DiffusionParams(seed_viewers=sv, population_size=int(population_size),
            conversation_rate=conversation_rate, spread_probability=spread_probability,
            recovery_rate=recovery_rate, days_to_simulate=120)
        det = run_sir(p)
        crossed = [s.day for s in det if s.pct_reached >= 50]
        bar_d50.append(crossed[0] if crossed else 120)
        bar_reach.append(det[-1].pct_reached)
        bar_lbl.append(f"{sv:,}")

    fig4c = make_subplots(rows=1, cols=2,
        subplot_titles=["Days to 50% reach", "Final % ever reached"])
    fig4c.add_trace(go.Bar(x=bar_lbl, y=bar_d50, marker_color=C_BLUE,
        name="Days to 50%"), row=1, col=1)
    fig4c.add_trace(go.Bar(x=bar_lbl, y=bar_reach, marker_color=C_ORANGE,
        name="Final reach %"), row=1, col=2)
    fig4c.update_layout(**LAYOUT_BASE,
        title="Impact of Seed Viewers (same virality)",
        xaxis_title="Seed viewers", height=350, showlegend=False)
    fig4c.update_yaxes(title_text="Days", row=1, col=1, gridcolor=GRID_CLR)
    fig4c.update_yaxes(title_text="% reached", ticksuffix="%", row=1, col=2, gridcolor=GRID_CLR)
    st.plotly_chart(fig4c, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"📡 Info Diffusion Simulator · SIR model adapted for information spread · "
    f"R₀ = β/γ = ({conversation_rate:.2f} × {spread_probability:.2f}) "
    f"/ {recovery_rate:.2f} = **{r0:.2f}**"
)
st.caption(
    "developed by **[nnnsightnnn](https://github.com/nnnsightnnn)** — signal from noise"
)
