import streamlit as st

def show():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');

    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #0A0C10 !important; color: #F4F1EB !important;
    }
    [data-testid="stSidebar"]  { display: none !important; }
    [data-testid="stHeader"]   { background: transparent !important; }
    [data-testid="stMainBlockContainer"] { padding: 0 !important; max-width: 100% !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    footer, #MainMenu { visibility: hidden; }

    /* Button overrides */
    div[data-testid="stButton"] > button {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        border: none !important;
        transition: all 0.2s !important;
        width: 100% !important;
    }
    div[data-testid="stButton"] > button[kind="primary"] {
        background: #C8F135 !important;
        color: #0A0C10 !important;
        padding: 14px 32px !important;
        border-radius: 4px !important;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background: #d9ff3d !important;
        transform: translateY(-1px) !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"] {
        background: transparent !important;
        color: #C8F135 !important;
        border: 1px solid rgba(200,241,53,0.35) !important;
        padding: 14px 32px !important;
        border-radius: 4px !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background: rgba(200,241,53,0.08) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── NAV ─────────────────────────────────────────────
    st.markdown("""
    <style>
    :root { --ink:#0A0C10; --paper:#F4F1EB; --lime:#C8F135; --slate:#1C2333; --mist:#8A94A8; }

    @keyframes fadeUp  { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
    @keyframes fadeIn  { from{opacity:0} to{opacity:1} }
    @keyframes pulse   { 0%,100%{opacity:1} 50%{opacity:0.3} }
    @keyframes chartDraw { from{stroke-dashoffset:1000} to{stroke-dashoffset:0} }
    .chart-line { stroke-dasharray:1000; stroke-dashoffset:1000; animation:chartDraw 2.5s ease forwards 1s; }

    .ld-nav {
        padding: 18px 48px;
        display: flex; align-items: center; justify-content: space-between;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        background: rgba(10,12,16,0.95);
        backdrop-filter: blur(20px);
    }
    .ld-logo { font-family:'Bebas Neue',sans-serif; font-size:28px; letter-spacing:3px; color:var(--lime); }
    .ld-badge { font-family:'DM Mono',monospace; font-size:11px; color:var(--mist); letter-spacing:2px; text-transform:uppercase; }
    </style>

    <div class="ld-nav">
      <div class="ld-logo">BI DASH</div>
      <div class="ld-badge">SME Intelligence Platform</div>
      <div style="width:160px"></div>
    </div>
    """, unsafe_allow_html=True)

    # Nav "Open Dashboard" button top-right
    nav1, nav2, nav3 = st.columns([5, 1.5, 1.5])
    with nav3:
        if st.button("Open Dashboard →", type="primary", key="nav_btn", use_container_width=True):
            st.session_state.page = "login"; st.rerun()

    # ── HERO ─────────────────────────────────────────────
    st.markdown("""
    <style>
    .ld-hero {
        display: grid; grid-template-columns: 1fr 1fr;
        align-items: center; gap: 56px;
        padding: 72px 48px 80px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        position: relative; overflow: hidden;
    }
    .ld-hero::after {
        content:''; position:absolute; right:-100px; top:40%;
        transform:translateY(-50%);
        width:500px; height:500px;
        background:radial-gradient(circle,rgba(200,241,53,0.06) 0%,transparent 70%);
        pointer-events:none;
    }
    .ld-eyebrow {
        font-family:'DM Mono',monospace; font-size:11px; letter-spacing:3px;
        color:var(--lime); text-transform:uppercase; margin-bottom:20px;
        display:flex; align-items:center; gap:12px;
        animation:fadeUp 0.7s ease forwards 0.1s; opacity:0;
    }
    .ld-eyebrow::before { content:''; width:32px; height:1px; background:var(--lime); }
    .ld-h1 {
        font-family:'DM Sans',sans-serif;
        font-size: clamp(52px, 6vw, 86px);
        font-weight: 800;
        line-height: 1.0;
        letter-spacing: -1px;
        margin-bottom: 28px;
        animation: fadeUp 0.7s ease forwards 0.2s; opacity:0;
    }
    .ld-h1 span { color: var(--lime); display:block; }
    .ld-sub {
        font-size:17px; font-weight:300; line-height:1.7; color:var(--mist);
        max-width:460px; margin-bottom:36px;
        animation:fadeUp 0.7s ease forwards 0.35s; opacity:0;
    }
    .ld-hero-btns {
        display:flex; gap:16px; align-items:center; flex-wrap:wrap;
        animation:fadeUp 0.7s ease forwards 0.45s; opacity:0;
    }
    .ld-ghost-link {
        font-size:15px; color:var(--mist); text-decoration:none;
        display:flex; align-items:center; gap:6px;
        border-bottom:1px solid rgba(138,148,168,0.35); padding-bottom:2px;
        transition:color 0.2s;
    }
    .ld-ghost-link:hover { color:var(--paper); }

    /* Dashboard frame */
    .ld-frame {
        background:#1C2333; border:1px solid rgba(255,255,255,0.09);
        border-radius:12px; overflow:hidden;
        box-shadow:0 32px 100px rgba(0,0,0,0.55),0 0 0 1px rgba(200,241,53,0.08);
        animation:fadeIn 0.9s ease forwards 0.6s; opacity:0;
    }
    .ld-frame-bar {
        background:#141820; padding:12px 16px;
        display:flex; align-items:center; gap:7px;
        border-bottom:1px solid rgba(255,255,255,0.06);
    }
    .ld-dot { width:10px; height:10px; border-radius:50%; }
    .ld-frame-url {
        margin-left:10px; background:rgba(255,255,255,0.05);
        border-radius:4px; padding:4px 12px;
        font-family:'DM Mono',monospace; font-size:10px; color:var(--mist); flex:1;
    }
    .ld-frame-body {
        padding:16px; position:relative;
        background:linear-gradient(160deg,#1a2035 0%,#111623 100%);
    }
    .ld-live {
        display:inline-flex; align-items:center; gap:5px; margin-bottom:14px;
        font-family:'DM Mono',monospace; font-size:10px; color:var(--lime); letter-spacing:1px;
    }
    .ld-live-dot { width:6px; height:6px; background:var(--lime); border-radius:50%; animation:pulse 1.5s infinite; }
    .ld-kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:14px; }
    .ld-kpi { background:rgba(0,0,0,0.25); border:1px solid rgba(255,255,255,0.07); border-radius:6px; padding:12px 14px; }
    .ld-kpi-lbl { font-family:'DM Mono',monospace; font-size:8px; color:var(--mist); letter-spacing:1px; text-transform:uppercase; margin-bottom:4px; }
    .ld-kpi-val { font-family:'DM Sans',sans-serif; font-size:22px; font-weight:800; color:var(--lime); line-height:1; }
    .ld-kpi-up { font-size:9px; color:#4ade80; margin-top:3px; }
    .ld-kpi-dn { font-size:9px; color:#f87171; margin-top:3px; }
    .ld-chart-lbl { font-family:'DM Mono',monospace; font-size:9px; color:var(--mist); margin-bottom:8px; }
    .ld-alerts { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:12px; }
    .ld-ah { background:rgba(248,113,113,0.07); border:1px solid rgba(248,113,113,0.18); border-left:2px solid #f87171; padding:9px 12px; border-radius:4px; font-size:10px; color:#fca5a5; }
    .ld-am { background:rgba(250,204,21,0.05); border:1px solid rgba(250,204,21,0.15); border-left:2px solid #fbbf24; padding:9px 12px; border-radius:4px; font-size:10px; color:#fcd34d; }
    </style>

    <section class="ld-hero">
      <div>
        <div class="ld-eyebrow">AI-powered business intelligence</div>
        <h1 class="ld-h1">Stop Guessing.<br><span>Start Knowing.</span></h1>
        <p class="ld-sub">Ask plain-English questions about your business. Get instant answers with evidence, reasons, and actions — powered by your real data.</p>

      </div>
      <div class="ld-frame">
        <div class="ld-frame-bar">
          <div class="ld-dot" style="background:#FF5F57"></div>
          <div class="ld-dot" style="background:#FFBD2E"></div>
          <div class="ld-dot" style="background:#28C840"></div>
          <div class="ld-frame-url">dashboard.local/overview</div>
        </div>
        <div class="ld-frame-body">
          <div class="ld-live"><div class="ld-live-dot"></div>LIVE</div>
          <div class="ld-kpis">
            <div class="ld-kpi"><div class="ld-kpi-lbl">Revenue</div><div class="ld-kpi-val">$125K</div><div class="ld-kpi-up">▲ 6%</div></div>
            <div class="ld-kpi"><div class="ld-kpi-lbl">Net Profit</div><div class="ld-kpi-val">$36K</div><div class="ld-kpi-up">▲ 4%</div></div>
            <div class="ld-kpi"><div class="ld-kpi-lbl">Cash Run.</div><div class="ld-kpi-val">2.4</div><div class="ld-kpi-dn">▲ Low</div></div>
            <div class="ld-kpi"><div class="ld-kpi-lbl">ROI</div><div class="ld-kpi-val">1.96X</div><div class="ld-kpi-up">▲ Best</div></div>
          </div>
          <div class="ld-chart-lbl">Revenue vs Expenses — Last 3 months</div>
          <svg viewBox="0 0 460 120" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:100%;border-radius:4px;background:rgba(0,0,0,0.2);padding:8px;margin-bottom:2px;">
            <line x1="0" y1="30"  x2="460" y2="30"  stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <line x1="0" y1="60"  x2="460" y2="60"  stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <line x1="0" y1="90"  x2="460" y2="90"  stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <path d="M0 110 C60 90 120 70 180 52 C240 34 300 78 360 44 L460 20 L460 120 L0 120 Z" fill="url(#ag)" opacity="0.25"/>
            <path class="chart-line" d="M0 110 C60 90 120 70 180 52 C240 34 300 78 360 44 L460 20" stroke="#C8F135" stroke-width="2.5" fill="none"/>
            <path class="chart-line" d="M0 115 C60 108 120 102 180 90 C240 78 300 105 360 94 L460 82" stroke="rgba(200,241,53,0.3)" stroke-width="1.5" fill="none" style="animation-delay:1.4s"/>
            <circle cx="360" cy="44" r="5" fill="#C8F135"><animate attributeName="opacity" values="0;1" dur="0.3s" begin="3s" fill="freeze"/></circle>
            <circle cx="360" cy="44" r="12" fill="none" stroke="#C8F135" stroke-width="1" opacity="0"><animate attributeName="opacity" values="0;0.4" dur="0.3s" begin="3s" fill="freeze"/></circle>
            <defs>
              <linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#C8F135"/><stop offset="100%" stop-color="#C8F135" stop-opacity="0"/>
              </linearGradient>
            </defs>
          </svg>
          <div class="ld-alerts">
            <div class="ld-ah">🔴 Cash runway below 3 months</div>
            <div class="ld-am">🟡 Campaign B losing money</div>
          </div>
        </div>
      </div>
    </section>
    """, unsafe_allow_html=True)

    # Hero "Open Dashboard" button
    h1, h2, h3 = st.columns([1, 1, 4])
    with h1:
        if st.button("Open Dashboard →", type="primary", key="hero_open", use_container_width=True):
            st.session_state.page = "login"; st.rerun()

    # ── STATS STRIP ──────────────────────────────────────
    st.markdown("""
    <style>
    .ld-stats {
        display:grid; grid-template-columns:repeat(4,1fr);
        border-top:1px solid rgba(255,255,255,0.06);
        border-bottom:1px solid rgba(255,255,255,0.06);
    }
    .ld-stat {
        padding:40px 48px;
        border-right:1px solid rgba(255,255,255,0.06);
    }
    .ld-stat:last-child { border-right:none; }
    .ld-stat-num {
        font-family:'DM Sans',sans-serif; font-weight:800;
        font-size:clamp(40px,4vw,60px); color:var(--lime);
        line-height:1; letter-spacing:-1px;
    }
    .ld-stat-txt { font-size:14px; color:var(--mist); margin-top:6px; }
    </style>

    <div class="ld-stats">
      <div class="ld-stat"><div class="ld-stat-num">1,445</div><div class="ld-stat-txt">Sales orders analysed</div></div>
      <div class="ld-stat"><div class="ld-stat-num">20+</div><div class="ld-stat-txt">Business questions answered</div></div>
      <div class="ld-stat"><div class="ld-stat-num">4</div><div class="ld-stat-txt">Domains covered</div></div>
      <div class="ld-stat"><div class="ld-stat-num">87%</div><div class="ld-stat-txt">Average AI confidence score</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── FEATURES ─────────────────────────────────────────
    st.markdown("""
    <style>
    .ld-features { padding:80px 48px; }
    .ld-feat-headline {
        font-family:'DM Sans',sans-serif; font-weight:800;
        font-size:clamp(36px,4vw,52px); line-height:1.05;
        letter-spacing:-0.5px; margin-bottom:52px;
    }
    .ld-feat-headline span { color:var(--lime); }
    .ld-feat-grid {
        display:grid; grid-template-columns:repeat(3,1fr);
        border:1px solid rgba(255,255,255,0.08);
        border-radius:2px;
    }
    .ld-feat-card {
        padding:36px 32px;
        border-right:1px solid rgba(255,255,255,0.07);
        border-bottom:1px solid rgba(255,255,255,0.07);
        transition:background 0.25s;
        position:relative; overflow:hidden;
    }
    .ld-feat-card:hover { background:rgba(255,255,255,0.03); }
    .ld-feat-card::before {
        content:''; position:absolute; top:0; left:0; right:0; height:2px;
        background:var(--lime); transform:scaleX(0); transform-origin:left; transition:transform 0.35s;
    }
    .ld-feat-card:hover::before { transform:scaleX(1); }
    .ld-feat-num { font-family:'DM Mono',monospace; font-size:10px; color:rgba(200,241,53,0.45); letter-spacing:2px; margin-bottom:12px; }
    .ld-feat-icon { font-size:20px; margin-bottom:14px; }
    .ld-feat-title { font-family:'DM Sans',sans-serif; font-weight:700; font-size:15px; margin-bottom:10px; color:var(--paper); }
    .ld-feat-desc { font-size:13px; color:var(--mist); line-height:1.65; }
    </style>

    <section class="ld-features">
      <h2 class="ld-feat-headline">Your Business,<br><span>Explained.</span></h2>
      <div class="ld-feat-grid">
        <div class="ld-feat-card"><div class="ld-feat-num">01</div><div class="ld-feat-icon">💬</div><div class="ld-feat-title">Ask in plain English</div><p class="ld-feat-desc">Type "Why did profit drop?" and get a clear answer with reasons, evidence, and a suggested action.</p></div>
        <div class="ld-feat-card"><div class="ld-feat-num">02</div><div class="ld-feat-icon">📊</div><div class="ld-feat-title">Finance at a glance</div><p class="ld-feat-desc">Revenue, expenses, profit margin, burn rate, and cash runway — always up to date, always explainable.</p></div>
        <div class="ld-feat-card"><div class="ld-feat-num">03</div><div class="ld-feat-icon">📈</div><div class="ld-feat-title">Sales & marketing truth</div><p class="ld-feat-desc">See which channel, product, or campaign is actually making money — and which ones are draining it.</p></div>
        <div class="ld-feat-card"><div class="ld-feat-num">04</div><div class="ld-feat-icon">👥</div><div class="ld-feat-title">Know your customers</div><p class="ld-feat-desc">Spot repeat buyers, identify churn risk, and see which segments drive the most lifetime value.</p></div>
        <div class="ld-feat-card"><div class="ld-feat-num">05</div><div class="ld-feat-icon">🔔</div><div class="ld-feat-title">Alerts before it's too late</div><p class="ld-feat-desc">Get warned automatically when cash runway drops, margins shrink, or campaign ROI turns negative.</p></div>
        <div class="ld-feat-card"><div class="ld-feat-num">06</div><div class="ld-feat-icon">📁</div><div class="ld-feat-title">Just upload your CSV</div><p class="ld-feat-desc">No integrations. No setup. Drop your export files in and your dashboard is live in under a minute.</p></div>
      </div>
    </section>
    """, unsafe_allow_html=True)

    # ── CHAT DEMO ─────────────────────────────────────────
    st.markdown("""
    <style>
    .ld-chat-section {
        padding:80px 48px;
        background:var(--slate);
        border-top:1px solid rgba(255,255,255,0.06);
    }
    .ld-chat-eyebrow {
        font-family:'DM Mono',monospace; font-size:11px; letter-spacing:3px;
        color:var(--lime); text-transform:uppercase; text-align:center; margin-bottom:16px;
    }
    .ld-chat-title {
        font-family:'DM Sans',sans-serif; font-weight:800;
        font-size:clamp(28px,3.5vw,44px);
        text-align:center; margin-bottom:48px; letter-spacing:-0.5px;
    }
    .ld-chat-title span { color:var(--lime); }
    .ld-chat-wrap {
        background:#141c2e; border:1px solid rgba(255,255,255,0.08);
        border-radius:12px; padding:28px; max-width:640px; margin:0 auto;
    }
    .ld-chat-msg { margin-bottom:18px; }
    .ld-msg-user { display:flex; justify-content:flex-end; }
    .ld-msg-ai   { display:flex; justify-content:flex-start; }
    .ld-bubble-user {
        background:var(--lime); color:#0A0C10;
        font-size:14px; font-weight:600;
        padding:12px 18px; border-radius:12px 12px 2px 12px; max-width:74%;
    }
    .ld-bubble-ai {
        background:#1e2840; border:1px solid rgba(255,255,255,0.07);
        color:var(--paper); font-size:13px;
        padding:16px 18px; border-radius:12px 12px 12px 2px; max-width:84%;
    }
    .ld-bubble-ai strong { color:var(--paper); font-weight:700; display:block; margin-bottom:10px; }
    .ld-answer-card {
        background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07);
        border-radius:6px; padding:12px 14px;
    }
    .ld-answer-row { display:flex; gap:12px; margin-bottom:6px; align-items:flex-start; }
    .ld-answer-lbl {
        font-family:'DM Mono',monospace; font-size:9px; color:var(--lime);
        letter-spacing:1px; min-width:72px; padding-top:1px;
    }
    .ld-answer-val { color:var(--mist); font-size:12px; line-height:1.5; }
    .ld-conf { display:flex; align-items:center; gap:10px; margin-top:8px; }
    .ld-conf-bar { flex:1; height:3px; background:rgba(255,255,255,0.08); border-radius:2px; overflow:hidden; }
    .ld-conf-fill { height:100%; background:var(--lime); width:87%; }
    .ld-conf-lbl { font-family:'DM Mono',monospace; font-size:9px; color:var(--lime); }
    </style>

    <section class="ld-chat-section">
      <div class="ld-chat-eyebrow">See it in action</div>
      <h2 class="ld-chat-title">Ask. <span>Get the Answer.</span> Act.</h2>
      <div class="ld-chat-wrap">
        <div class="ld-chat-msg ld-msg-user">
          <div class="ld-bubble-user">Why did profit drop in November?</div>
        </div>
        <div class="ld-chat-msg ld-msg-ai">
          <div class="ld-bubble-ai">
            <strong>Net profit dropped 18% in November.</strong>
            <div class="ld-answer-card">
              <div class="ld-answer-row"><span class="ld-answer-lbl">REASON</span><span class="ld-answer-val">Ad spend rose 31% while revenue grew only 6%</span></div>
              <div class="ld-answer-row"><span class="ld-answer-lbl">EVIDENCE</span><span class="ld-answer-val">Campaign B: $8,200 spend at 0.4x ROI</span></div>
              <div class="ld-answer-row"><span class="ld-answer-lbl">ACTION</span><span class="ld-answer-val">Pause Campaign B — reallocate to Campaign 1 (2.93x ROI)</span></div>
              <div class="ld-conf">
                <span class="ld-answer-lbl">CONFIDENCE</span>
                <div class="ld-conf-bar"><div class="ld-conf-fill"></div></div>
                <span class="ld-conf-lbl">87%</span>
              </div>
            </div>
          </div>
        </div>
        <div class="ld-chat-msg ld-msg-user">
          <div class="ld-bubble-user">Which customers are at risk of churning?</div>
        </div>
        <div class="ld-chat-msg ld-msg-ai">
          <div class="ld-bubble-ai">
            <strong>3 customers are at high churn risk.</strong>
            <div class="ld-answer-card">
              <div class="ld-answer-row"><span class="ld-answer-lbl">CUSTOMER 12</span><span class="ld-answer-val">Risk: 0.92 — last order 78 days ago</span></div>
              <div class="ld-answer-row"><span class="ld-answer-lbl">CUSTOMER 45</span><span class="ld-answer-val">Risk: 0.87 — last order 65 days ago</span></div>
              <div class="ld-answer-row"><span class="ld-answer-lbl">ACTION</span><span class="ld-answer-val">Launch retention campaign targeting these 3 customers</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>
    """, unsafe_allow_html=True)

    # ── FINAL CTA ─────────────────────────────────────────
    st.markdown("""
    <style>
    .ld-cta {
        padding: 100px 48px;
        text-align: center;
        background: var(--ink);
        border-top: 1px solid rgba(255,255,255,0.06);
        position: relative; overflow: hidden;
    }
    .ld-cta::before {
        content:''; position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
        width:600px; height:600px;
        background:radial-gradient(circle,rgba(200,241,53,0.05) 0%,transparent 70%);
        pointer-events:none;
    }
    .ld-cta-title {
        font-family:'DM Sans',sans-serif; font-weight:800;
        font-size:clamp(36px,5vw,60px); line-height:1.05;
        letter-spacing:-1px; margin-bottom:20px;
        position:relative; z-index:1;
    }
    .ld-cta-title span { color:var(--lime); }
    .ld-cta-sub {
        font-size:16px; color:var(--mist); max-width:440px;
        margin:0 auto 36px; line-height:1.7;
        position:relative; z-index:1;
    }
    .ld-cta-badges {
        display:flex; gap:32px; justify-content:center; flex-wrap:wrap;
        margin-top:20px; position:relative; z-index:1;
    }
    .ld-cta-badge {
        font-family:'DM Mono',monospace; font-size:11px;
        color:rgba(200,241,53,0.45); letter-spacing:2px; text-transform:uppercase;
    }
    .ld-footer {
        padding:28px 48px;
        border-top:1px solid rgba(255,255,255,0.06);
        display:flex; align-items:center; justify-content:center;
    }
    .ld-footer-logo { font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--lime); letter-spacing:3px; }
    </style>

    <section class="ld-cta">
      <h2 class="ld-cta-title">Your Data.<br><span>Your Answers.</span></h2>
      <p class="ld-cta-sub">Upload your CSV files and start asking questions about your business in under 60 seconds.</p>
    </section>
    """, unsafe_allow_html=True)

    # CTA "Get Started" button — centred
    _, cta_col, _ = st.columns([2, 1.5, 2])
    with cta_col:
        if st.button("Get Started →", type="primary", key="cta_btn", use_container_width=True):
            st.session_state.page = "register"; st.rerun()

    st.markdown("""
    <div style="padding:0 48px 20px;text-align:center;">
      <div style="display:flex;gap:32px;justify-content:center;flex-wrap:wrap;margin-top:16px;">
        <span style="font-family:'DM Mono',monospace;font-size:11px;color:rgba(200,241,53,0.4);letter-spacing:2px;text-transform:uppercase;">CSV upload only</span>
        <span style="font-family:'DM Mono',monospace;font-size:11px;color:rgba(200,241,53,0.4);letter-spacing:2px;text-transform:uppercase;">No setup needed</span>
        <span style="font-family:'DM Mono',monospace;font-size:11px;color:rgba(200,241,53,0.4);letter-spacing:2px;text-transform:uppercase;">Real data · Real answers</span>
      </div>
    </div>
    <footer class="ld-footer">
      <div class="ld-footer-logo">BI DASH</div>
    </footer>
    """, unsafe_allow_html=True)