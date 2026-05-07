import streamlit as st
from api_client import ask_question

def show():
    st.title("Ask a question")
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
