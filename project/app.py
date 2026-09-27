{"role": message["role"], "content": message["content"]}:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question about your knowledge base..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.
