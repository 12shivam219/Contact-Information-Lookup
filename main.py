import streamlit as st
from utils import (
    RateLimiter,
    validate_person_name,
    validate_company_name,
    search_person,
    search_company_info
)
from styles import apply_custom_styles

# Initialize rate limiter
rate_limiter = RateLimiter()

def get_confidence_color(score: str) -> str:
    """Return color based on confidence score"""
    colors = {
        'high': 'green',
        'medium': 'orange',
        'low': 'red'
    }
    return colors.get(score.lower(), 'gray')

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
    Find contact information for people based on their name and company affiliation.
    Please use this tool responsibly and in accordance with applicable privacy laws.
    """)

    # Input form
    with st.form("search_form"):
        col1, col2 = st.columns(2)

        with col1:
            person_name = st.text_input("Person's Name", 
                                    placeholder="John Doe")

        with col2:
            company_name = st.text_input("Company Name",
                                     placeholder="Example Corp")

        submit_button = st.form_submit_button("Search")

    if submit_button:
        # Validate inputs
        person_valid, person_error = validate_person_name(person_name)
        company_valid, company_error = validate_company_name(company_name)

        if not person_valid:
            st.error(person_error)
        elif not company_valid:
            st.error(company_error)
        else:
            # Check rate limiting
            if not rate_limiter.can_make_request():
                st.error("Too many requests. Please wait a minute before trying again.")
                return

            rate_limiter.add_call()

            # Show loading state
            with st.spinner("Searching for contact information..."):
                # Search using multiple APIs
                person_info = search_person(person_name, company_name)
                company_info = search_company_info(company_name)

                if person_info or company_info:
                    st.success("Information found!")

                    # Display person information
                    if person_info:
                        st.markdown("### Person Information")

                        # Get confidence information
                        confidence = person_info.get('confidence_score', 'low')
                        source = person_info.get('source', 'Unknown')
                        confidence_color = get_confidence_color(confidence)

                        # Display basic info
                        st.markdown(f"""
                        <div class="company-info">
                            <p><strong>Name:</strong> {person_info.get('name', 'N/A')}</p>
                            <p><strong>Company:</strong> {person_info.get('company', 'N/A')}</p>
                            <p><strong>Email:</strong> {person_info.get('email', 'N/A')}</p>
                            <p><strong>Position:</strong> {person_info.get('position', 'N/A')}</p>
                            <p><strong>Phone:</strong> {person_info.get('phone', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        # Display data reliability information
                        st.info(f"""
                        **Data Reliability Information:**
                        - Confidence Level: <span style='color: {confidence_color}'>{confidence.upper()}</span>
                        - Source: {source}
                        - Note: Contact information is gathered from publicly available sources and may need verification.
                        """)

                        # Display social profiles if available
                        if person_info.get('social_profiles'):
                            st.markdown("### Social Profiles")
                            for platform, url in person_info['social_profiles'].items():
                                st.markdown(f"- {platform.title()}: {url}")

                    # Display company information
                    if company_info:
                        st.markdown("### Company Information")
                        st.markdown(f"""
                        <div class="company-info">
                            <p><strong>Name:</strong> {company_info.get('name', 'N/A')}</p>
                            <p><strong>Domain:</strong> {company_info.get('domain', 'N/A')}</p>
                            <p><strong>Logo:</strong> <img src="{company_info.get('logo', '')}" height="30"/></p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("No information found for the provided person and company.")

    # Privacy Policy and Disclaimers
    with st.expander("Privacy Policy & Disclaimers"):
        st.markdown("""
        ### Privacy Policy
        - This tool only searches publicly available information
        - We do not store or retain any searched data
        - Use of this tool implies acceptance of these terms

        ### Data Sources
        - Company information is provided by Clearbit's API
        - Person information is aggregated from public sources
        - Contact details are found through public web searches
        - Data reliability is indicated by confidence scores

        ### Usage Guidelines
        - Respect rate limits and fair usage policies
        - Do not use this tool for unauthorized data collection
        - We are not responsible for the accuracy of the data
        - Always verify contact information before use
        """)

    # Footer
    st.markdown("""
    <div class="disclaimer">
    Made with ❤️ | Data provided by public APIs
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()