import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from header_footer import render_header, render_footer
from api_client import ask_question

def show():
    import streamlit as st
    st.markdown("""
<style>
@media (max-width: 480px) {
    [data-testid="stMainBlockContainer"] { padding: 12px 10px !important; }
    [data-testid="stMetric"] { min-width: 0 !important; }
    [data-testid="stMetricValue"] { font-size: 20px !important; }
    [data-testid="stMetricLabel"] { font-size: 11px !important; }
    h1 { font-size: 20px !important; }
    h2 { font-size: 17px !important; }
    h3 { font-size: 15px !important; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [data-testid="stHorizontalBlock"] > div { min-width: 140px !important; flex: 1 !important; }
}
@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] { padding: 16px 12px !important; }
    [data-testid="stMetricValue"] { font-size: 22px !important; }
}
/* Accessibility — improved text contrast */
[data-testid="stMetricLabel"] { color: #C8C8D8 !important; font-size: 13px !important; }
[data-testid="stMetricValue"] { color: #F4F1EB !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] { font-size: 12px !important; }
/* Chart labels contrast */
.element-container p { color: #C8C8D8 !important; }
/* Selectbox contrast */
[data-testid="stSelectbox"] label { color: #C8C8D8 !important; font-size: 13px !important; }
[data-testid="stSelectbox"] > div > div {
    background: #1C1A3A !important;
    border-color: rgba(123,92,245,0.3) !important;
    color: #F4F1EB !important;
}
/* File uploader contrast */
[data-testid="stFileUploader"] label { color: #C8C8D8 !important; }
/* Dataframe contrast */
[data-testid="stDataFrame"] { border: 1px solid rgba(123,92,245,0.15) !important; }
/* Focus indicators for keyboard navigation */
button:focus, input:focus, select:focus {
    outline: 2px solid #7B5CF5 !important;
    outline-offset: 2px !important;
}
</style>
""", unsafe_allow_html=True)
    render_header("Ask a Question")
    st.caption("Ask anything about your business in plain English.")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    st.markdown("**Suggested questions:**")
    suggestions = ["Why is profit down this month?","Which products sell best?",
                   "Which campaign is wasting money?","How many months of cash runway do I have?",
                   "Who are my best customers?","Which channel drives the most revenue?"]
    cols = st.columns(3)
    for i, q in enumerate(suggestions):
        if cols[i % 3].button(q, key=f"suggest_{i}"):
            st.session_state.prefill = q
    st.markdown("---")
    def display_answer(ans):
        st.write(ans["answer"])
        c1,c2 = st.columns(2)
        with c1:
            if ans.get("reason"): st.markdown(f"**Reason:** {ans['reason']}")
            if ans.get("action"): st.info(f"**Suggested action:** {ans['action']}")
        with c2:
            if ans.get("evidence"):
                st.markdown("**Evidence:**")
                for e in ans["evidence"]: st.caption(f"• {e['source']}: {e['detail']}")
        if ans.get("confidence"):
            st.progress(ans["confidence"], text=f"Confidence: {ans['confidence']*100:.0f}%")
    for entry in st.session_state.chat_history:
        with st.chat_message("user"): st.write(entry["question"])
        with st.chat_message("assistant"): display_answer(entry["answer"])
    prefill = st.session_state.pop("prefill", "")
    question = st.chat_input("Type your question here...")
    if not question and prefill: question = prefill
    if question:
        with st.chat_message("user"): st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = ask_question(question)
            if answer:
                display_answer(answer)
                st.session_state.chat_history.append({"question": question, "answer": answer})
    if st.session_state.chat_history:
        if st.button("Clear conversation"):
            st.session_state.chat_history = []; st.rerun()
    render_footer()