import streamlit as st

def show_demo_disclaimer():
    """Display demo usage disclaimer"""
    st.warning("""
    ⚠️ **Demo Usage Notice**
    
    This is a demonstration application with usage limits to manage costs:
    - **Purpose**: Technical showcase of OCI AI Language Services
    - **Usage**: Limited to prevent excessive API costs
    - **Not for production**: Please use responsibly for demo purposes only
    
    For production translation needs, consider implementing your own instance.
    """)

def show_usage_limits():
    """Show current usage limits"""
    st.info("""
    📊 **Current Demo Limits**
    - Daily translations: 100 per day
    - Monthly translations: 1,000 per month
    - Character limit: ~5,000 characters per translation
    
    These limits help keep the demo free and available for everyone.
    """)
