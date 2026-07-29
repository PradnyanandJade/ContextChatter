import streamlit as st
import requests

st.set_page_config(
    page_title="ContextChatter",
    page_icon="💬",
    layout="wide"
)

URL = "http://localhost:8000"

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.title("💬 ContextChatter")
    st.divider()

    uploaded_file = st.file_uploader(
        "Upload Document",
        type=["pdf"],
    )

    if uploaded_file:
        if st.button("⬆ Upload", use_container_width=True):
            response = requests.post(
                f"{URL}/files/upload",
                files={
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type,
                    )
                },
            )

            if response.ok:
                st.success("Uploaded!")
                st.rerun()
            else:
                st.error(response.text)

    st.divider()

    st.subheader("📚 Documents")

    response = requests.get(f"{URL}/files")

    if response.ok:
        docs = response.json()

        if docs:
            selected_docs = []

            for doc in docs:
                col1, col2 = st.columns([4, 1])

                with col1:
                    checked = st.checkbox(
                        doc["filename"],
                        key=f"doc_{doc['document_id']}"
                    )

                    if checked:
                        selected_docs.append(doc["document_id"])

                with col2:
                    if st.button(
                        "🗑️",
                        key=f"delete_{doc['document_id']}",
                        help="Delete document"
                    ):
                        delete_response = requests.delete(
                            f"{URL}/files/{doc['document_id']}"
                        )

                        if delete_response.ok:
                            st.success("Document deleted.")
                            st.rerun()
                        else:
                            st.error(delete_response.text)

            st.session_state["selected_docs"] = selected_docs

        else:
            st.caption("No uploaded documents.")
    else:
        st.error("Couldn't fetch documents.")

    st.divider()


# -----------------------------
# Main Area
# -----------------------------


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask about your documents...")

if prompt:
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # Backend request
    response = requests.post(
        f"{URL}/chat",
        json={
            "query": prompt,
            "document_ids": st.session_state.get(
                "selected_docs",
                []
            ),
        },
    )

    answer = response.json()["answer"]

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )

    with st.chat_message("assistant"):
        st.markdown(answer)