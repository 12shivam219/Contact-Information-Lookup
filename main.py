import streamlit as st
from utils import (
    RateLimiter,
    validate_domain,
    validate_company_name,
    search_clearbit,
    search_domain_info
)
from styles import apply_custom_styles

# Initialize rate limiter
rate_limiter = RateLimiter()

def main():
    # Page config must be the first Streamlit command
    st.set_page_config(
        page_title="Contact Information Lookup",
        page_icon="🔍",
        layout="wide"
    )

    # Apply custom styles
    apply_custom_styles()
    
    # Header
    st.title("🔍 Contact Information Lookup")
    st.markdown("""
    Find company and contact information using domain name or company details.
    Please use this tool responsibly and in accordance with applicable privacy laws.
    """)
    
    # Input form
    with st.form("search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            domain = st.text_input("Company Domain", 
                                 placeholder="example.com")
        
        with col2:
            company_name = st.text_input("Company Name",
                                       placeholder="Example Corp")
        
        submit_button = st.form_submit_button("Search")
    
    if submit_button:
        # Validate inputs
        domain_valid, domain_error = validate_domain(domain)
        name_valid, name_error = validate_company_name(company_name)
        
        if not domain_valid:
            st.error(domain_error)
        elif not name_valid:
            st.error(name_error)
        else:
            # Check rate limiting
            if not rate_limiter.can_make_request():
                st.error("Too many requests. Please wait a minute before trying again.")
                return
            
            rate_limiter.add_call()
            
            # Show loading state
            with st.spinner("Searching for company information..."):
                # Search using multiple APIs
                clearbit_info = search_clearbit(domain)
                domain_info = search_domain_info(domain)
                
                if clearbit_info or domain_info:
                    st.success("Information found!")
                    
                    # Display company information
                    with st.container():
                        st.markdown("### Company Information")
                        if clearbit_info:
                            st.markdown(f"""
                            <div class="company-info">
                                <p><strong>Name:</strong> {clearbit_info.get('name', 'N/A')}</p>
                                <p><strong>Domain:</strong> {clearbit_info.get('domain', 'N/A')}</p>
                                <p><strong>Logo:</strong> <img src="{clearbit_info.get('logo', '')}" height="30"/></p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        if domain_info:
                            st.markdown("### Domain Information")
                            st.json(domain_info)
                else:
                    st.warning("No information found for the provided domain and company name.")
    
    # Privacy Policy and Disclaimers
    with st.expander("Privacy Policy & Disclaimers"):
        st.markdown("""
        ### Privacy Policy
        - This tool only searches publicly available information
        - We do not store or retain any searched data
        - Use of this tool implies acceptance of these terms
        
        ### Data Sources
        - Company information is provided by Clearbit's API
        - Domain information is provided by WHOIS API
        
        ### Usage Guidelines
        - Respect rate limits and fair usage policies
        - Do not use this tool for unauthorized data collection
        - We are not responsible for the accuracy of the data
        """)
    
    # Footer
    st.markdown("""
    <div class="disclaimer">
    Made with ❤️ | Data provided by Clearbit and WHOIS API
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()