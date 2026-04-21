import streamlit as st
from api_client import ask_question
from config import CURRENCY_SYMBOL

st.title("Ask a question")
st.caption("Ask anything about your business in plain English.")

# ── SUGGESTED QUESTIONS ──────────────────────────────────
st.markdown("**Suggested questions:**")
suggestions = [
    "Why is profit down this month?",
    "Which products sell best?",
    "Which campaign is wasting money?",
    "How many months of cash runway do I have?",
    "Who are my best customers?",
    "Which channel drives the most revenue?",
]
cols = st.columns(3)
for i, q in enumerate(suggestions):
    if cols[i % 3].button(q, key=f"suggest_{i}"):
        st.session_state.chat_input = q

st.markdown("---")

# ── CHAT HISTORY ─────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for entry in st.session_state.chat_history:
    with st.chat_message("user"):
        st.write(entry["question"])
    with st.chat_message("assistant"):
        _render_answer(entry["answer"]) if False else _display_answer(entry["answer"])

def _display_answer(ans):
    st.write(ans["answer"])
    col1, col2 = st.columns(2)
    with col1:
        if ans.get("reason"):
            st.markdown(f"**Reason:** {ans['reason']}")
        if ans.get("action"):
            st.info(f"**Suggested action:** {ans['action']}")
    with col2:
        if ans.get("evidence"):
            st.markdown("**Evidence:**")
            for e in ans["evidence"]:
                st.caption(f"• {e['source']}: {e['detail']}")
    if ans.get("confidence"):
        st.progress(ans["confidence"], text=f"Confidence: {ans['confidence']*100:.0f}%")

# Re-render history properly
st.session_state.chat_history  # just access to trigger rerun awareness

for entry in st.session_state.chat_history:
    with st.chat_message("user"):
        st.write(entry["question"])
    with st.chat_message("assistant"):
        _display_answer(entry["answer"])

# ── INPUT ────────────────────────────────────────────────
prefill = st.session_state.pop("chat_input", "")
question = st.chat_input("Type your question here...")

if not question and prefill:
    question = prefill

if question:
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = ask_question(question)
        if answer:
            _display_answer(answer)
            st.session_state.chat_history.append({
                "question": question,
                "answer":   answer
            })
        else:
            st.error("Could not get an answer. Check the backend connection.")

# ── CLEAR HISTORY ────────────────────────────────────────
if st.session_state.chat_history:
    if st.button("Clear conversation"):
        st.session_state.chat_history = []
        st.rerun()
