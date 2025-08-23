import streamlit as st

st.title("Simple Test App")
st.write("Hello from Databricks Apps!")

name = st.text_input("Enter your name:")
if name:
    st.write(f"Hello, {name}!")

st.metric("Test Metric", "42", "Success")