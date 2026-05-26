import streamlit as st
import pandas as pd
from api_client import ask_question, get_overview

def _no_data_state():
    st.markdown("## 💬 AI Chat")
    st.info(
        "**No data uploaded yet.**\n\n"
        "Import your CSV files to unlock the AI chat — then ask plain-English questions "
        "about your revenue, customers, campaigns, and more."
    )
    if st.button("Import your data to get started →", type="primary", key="chat_upload_cta"):
        st.session_state.page = "upload"; st.rerun()

def show():
    # Check whether this company has any uploaded data
    if "has_data" not in st.session_state:
        overview = get_overview()
        st.session_state.has_data = bool(overview and overview.get("has_data", True))
    if not st.session_state.get("has_data"):
        _no_data_state(); return

    st.title("Ask a question")
    st.caption("Ask anything about your business in plain English.")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    st.markdown("**Suggested questions:**")
    suggestions = ["Who are my best customers?", "Which products sell best?",
                   "Which campaign is wasting money?", "How many months of cash runway do I have?",
                   "What is total revenue?", "Which channel drives the most revenue?"]
    cols = st.columns(3)
    for i, q in enumerate(suggestions):
        if cols[i % 3].button(q, key=f"suggest_{i}"):
            st.session_state.prefill = q
    st.markdown("---")

    def display_answer(ans):
        st.markdown(ans.get("answer", "No answer returned."))
        result = ans.get("result")
        if result and result.get("rows") and result.get("columns") and len(result["rows"]) > 1:
            df = pd.DataFrame(result["rows"], columns=result["columns"])
            st.dataframe(df, use_container_width=True, hide_index=True)

        has_reason   = ans.get("reason")
        has_action   = ans.get("action")
        has_evidence = ans.get("evidence")

        if has_reason or has_action or has_evidence:
            col_left, col_right = st.columns([3, 2])
            with col_left:
                if has_reason:
                    st.markdown(f"**Reason:** {has_reason}")
                if has_action:
                    st.info(f"**Suggested action:** {has_action}")
            with col_right:
                if has_evidence:
                    st.markdown("**Evidence:**")
                    for e in has_evidence:
                        st.caption(f"• {e['source']}: {e['detail']}")

        if ans.get("confidence"):
            st.progress(ans["confidence"], text=f"Confidence: {ans['confidence']*100:.0f}%")

    for entry in st.session_state.chat_history:
        with st.chat_message("user"): st.write(entry["question"])
        with st.chat_message("assistant"): display_answer(entry["answer"])

    prefill = st.session_state.pop("prefill", "")
    question = st.chat_input("Type your question here...")
    if not question and prefill:
        question = prefill
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
            st.session_state.chat_history = []
            st.rerun()
