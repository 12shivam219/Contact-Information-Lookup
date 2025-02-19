import streamlit as st

def apply_custom_styles():
    """Apply custom CSS styles to the Streamlit app"""
    st.markdown("""
        <style>
        .main {
            padding: 2rem;
        }
        .stAlert {
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
        .company-info {
            padding: 1.5rem;
            border-radius: 5px;
            background-color: #f8f9fa;
            margin: 1rem 0;
        }
        .disclaimer {
            font-size: 0.8rem;
            color: #6c757d;
            margin-top: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)
