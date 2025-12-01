import streamlit as st
import pandas as pd
import anthropic
import json
from io import BytesIO
# For Excel export.
import openpyxl
# Page config
st.set_page_config(page_title="AI Franchise Identifier", page_icon="🎯", layout="wide")

st.title("🎯 AI-Powered Franchise Identifier")
st.markdown("Analyze campaign text to automatically identify franchises using your master reference file.")

# Sidebar for API key
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Anthropic API Key", type="password", help="Enter your Claude API key")
    st.markdown("---")
    st.markdown("### How it works:")
    st.markdown("""
    1. Upload master file (Division/Brand/Franchise)
    2. Upload campaign data (with Campaign column)
    3. Select Division → Brand
    4. AI reads campaign text and identifies franchises
    5. Download with new FRANCHISE column
    """)

# Initialize session state
if 'master_df' not in st.session_state:
    st.session_state.master_df = None
if 'campaign_df' not in st.session_state:
    st.session_state.campaign_df = None

# File uploads
st.header("Step 1: Upload Files")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Master File")
    st.caption("Contains Division → Brand → Franchise mappings")
    master_file = st.file_uploader("Upload master file", type=['csv', 'xlsx', 'xls'], key="master")
    
    if master_file is not None:
        try:
            if master_file.name.endswith('.csv'):
                st.session_state.master_df = pd.read_csv(master_file)
            else:
                st.session_state.master_df = pd.read_excel(master_file)
            
            st.success(f"✅ Loaded: {len(st.session_state.master_df)} rows")
            
            with st.expander("Preview Master File"):
                st.dataframe(st.session_state.master_df.head(10))
        
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

with col2:
    st.subheader("📊 Campaign Data")
    st.caption("Contains campaigns to identify franchises for")
    campaign_file = st.file_uploader("Upload campaign data", type=['csv', 'xlsx', 'xls'], key="campaign")
    
    if campaign_file is not None:
        try:
            if campaign_file.name.endswith('.csv'):
                st.session_state.campaign_df = pd.read_csv(campaign_file)
            else:
                st.session_state.campaign_df = pd.read_excel(campaign_file)
            
            st.success(f"✅ Loaded: {len(st.session_state.campaign_df)} rows")
            
            with st.expander("Preview Campaign Data"):
                st.dataframe(st.session_state.campaign_df.head(10))
        
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

# Only proceed if both files are uploaded
if st.session_state.master_df is not None and st.session_state.campaign_df is not None:
    
    st.markdown("---")
    st.header("Step 2: Map Columns")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Master File Columns")
        division_col = st.selectbox("Division Column", 
                                    st.session_state.master_df.columns.tolist(),
                                    key="div_col_select")
        brand_col = st.selectbox("Brand Column", 
                                st.session_state.master_df.columns.tolist(),
                                key="brand_col_select")
        franchise_col = st.selectbox("Franchise Column", 
                                     st.session_state.master_df.columns.tolist(),
                                     key="franchise_col_select")
    
    with col2:
        st.subheader("Campaign Data Column")
        campaign_col = st.selectbox("Campaign Column (text to analyze)", 
                                   st.session_state.campaign_df.columns.tolist(),
                                   key="campaign_col_select")
        
        st.info("💡 AI will read this column to identify which franchise each campaign belongs to")
    
    # Filters
    st.markdown("---")
    st.header("Step 3: Filter by Division & Brand")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Get unique divisions
        divisions = sorted(st.session_state.master_df[division_col].dropna().unique().tolist())
        selected_division = st.selectbox("Select Division", divisions)
    
    with col2:
        # Filter brands by division
        if selected_division:
            filtered_brands = st.session_state.master_df[
                st.session_state.master_df[division_col] == selected_division
            ][brand_col].dropna().unique().tolist()
            filtered_brands = sorted(filtered_brands)
            
            selected_brand = st.selectbox("Select Brand", filtered_brands)
    
    # Show context
    if selected_division and selected_brand:
        st.markdown("---")
        st.header("Step 4: Review Context")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Available Franchises")
            st.info(f"**Division:** {selected_division}  \n**Brand:** {selected_brand}")
            
            # Show franchises for this division/brand
            master_filtered = st.session_state.master_df[
                (st.session_state.master_df[division_col] == selected_division) &
                (st.session_state.master_df[brand_col] == selected_brand)
            ]
            
            franchises_list = master_filtered[franchise_col].dropna().unique().tolist()
            
            st.markdown(f"**{len(franchises_list)} Franchises found:**")
            for franchise in franchises_list:
                st.markdown(f"- {franchise}")
            
            with st.expander("View Full Master Data"):
                st.dataframe(master_filtered, use_container_width=True)
        
        with col2:
            st.subheader("📊 Campaigns to Analyze")
            
            # Get unique campaign values
            unique_campaigns = st.session_state.campaign_df[campaign_col].dropna().unique().tolist()
            st.info(f"Found **{len(unique_campaigns)}** unique campaigns")
            
            with st.expander("View Sample Campaigns"):
                st.dataframe(
                    st.session_state.campaign_df[[campaign_col]].head(20),
                    use_container_width=True
                )
        
        # AI Analysis
        st.markdown("---")
        st.header("Step 5: AI Franchise Identification")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"""
            The AI will analyze the **campaign text** in your data and determine which of the 
            **{len(franchises_list)} franchises** each campaign belongs to by reading the campaign names/descriptions.
            """)
        
        with col2:
            if st.button("🤖 Identify Franchises", type="primary", use_container_width=True):
                if not api_key:
                    st.error("⚠️ Please enter your Anthropic API key in the sidebar")
                else:
                    with st.spinner("AI is analyzing campaign text..."):
                        try:
                            # Initialize Claude
                            client = anthropic.Anthropic(api_key=api_key)
                            
                            # Prepare unique campaigns for analysis
                            campaigns_to_analyze = st.session_state.campaign_df[campaign_col].dropna().unique().tolist()
                            
                            # Create prompt
                            prompt = f"""You are a data analysis expert specializing in franchise identification.

**Context:**
- Division: {selected_division}
- Brand: {selected_brand}

**Available Franchises (from master file):**
{json.dumps(franchises_list, indent=2)}

**Campaign Data to Analyze:**
{json.dumps(campaigns_to_analyze[:100], indent=2)}  
{"... (showing first 100 campaigns)" if len(campaigns_to_analyze) > 100 else ""}

**Task:**
Read each campaign name/description and intelligently determine which franchise it belongs to from the available franchises list above.

Look for:
- Brand names, abbreviations, or variations in the campaign text
- Keywords that indicate a specific franchise
- Context clues (franchises, products, brands within the LOreal umbrealla business, etc.)
- Misspellings or informal references

For campaigns that clearly match one of the available franchises, map them to that franchise name (use EXACT spelling from the available franchises list).

If a campaign doesn't match any franchise or is ambiguous, you can:
- Map to "Unknown" if truly unclear
- Make your best educated guess with lower confidence

Return ONLY valid JSON in this exact format:
{{
  "mappings": {{
    "campaign_text_1": "Franchise Name",
    "campaign_text_2": "Franchise Name",
    "campaign_text_3": "Unknown"
  }},
  "summary": {{
    "total_campaigns": number,
    "franchises_identified": {{
      "Franchise Name 1": count,
      "Franchise Name 2": count,
      "Unknown": count
    }},
    "confidence": "high/medium/low"
  }}
}}

IMPORTANT: Use the EXACT franchise names from the available franchises list above."""

                            # Call Claude API
                            message = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=8000,
                                messages=[{"role": "user", "content": prompt}]
                            )
                            
                            # Parse response
                            response_text = message.content[0].text
                            
                            # Try to extract JSON if wrapped in markdown
                            if "```json" in response_text:
                                response_text = response_text.split("```json")[1].split("```")[0].strip()
                            elif "```" in response_text:
                                response_text = response_text.split("```")[1].split("```")[0].strip()
                            
                            mapping_result = json.loads(response_text)
                            
                            # Store in session state (use strings, not Timestamp objects)
                            st.session_state.mapping_result = mapping_result
                            st.session_state.selected_brand = str(selected_brand)
                            st.session_state.selected_division = str(selected_division)
                            st.session_state.campaign_col_stored = str(campaign_col)
                            st.session_state.franchises_list = franchises_list
                            
                            st.success("✅ AI franchise identification complete!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            if 'response_text' in locals():
                                with st.expander("Debug: Raw Response"):
                                    st.code(response_text)
        
        # Display results if available
        if 'mapping_result' in st.session_state:
            st.markdown("---")
            st.header("Step 6: Review Identified Franchises")
            
            mappings = st.session_state.mapping_result['mappings']
            summary = st.session_state.mapping_result.get('summary', {})
            franchises_identified = summary.get('franchises_identified', {})
            
            # Summary metrics
            st.subheader("📊 Summary")
            cols = st.columns(len(franchises_identified) + 1)
            
            cols[0].metric("Total Campaigns", summary.get('total_campaigns', len(mappings)))
            
            for idx, (franchise, count) in enumerate(franchises_identified.items(), 1):
                if idx < len(cols):
                    cols[idx].metric(franchise, count)
            
            # Confidence
            confidence = summary.get('confidence', 'N/A')
            st.info(f"🎯 **AI Confidence:** {confidence.upper()}")
            
            # Show mappings table
            with st.expander("📋 View All Mappings", expanded=True):
                mapping_df = pd.DataFrame([
                    {
                        "Campaign": k, 
                        "Identified Franchise": v,
                        "Status": "✅" if v != "Unknown" else "❓"
                    } 
                    for k, v in mappings.items()
                ])
                st.dataframe(mapping_df, use_container_width=True, height=400)
            
            # Apply mappings
            st.markdown("---")
            st.header("Step 7: Apply to Data")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown("This will create a new **FRANCHISE** column in your campaign data based on the AI's analysis.")
            
            with col2:
                if st.button("✨ Apply Mappings", type="primary", use_container_width=True):
                    df_cleaned = st.session_state.campaign_df.copy()
                    
                    # Create new franchise column
                    df_cleaned['FRANCHISE'] = df_cleaned[campaign_col].map(mappings)
                    
                    # For campaigns not in mapping, mark as Unknown
                    df_cleaned['FRANCHISE'].fillna('Unknown', inplace=True)
                    
                    # Add metadata columns
                    df_cleaned['DIVISION'] = selected_division
                    df_cleaned['BRAND'] = selected_brand
                    df_cleaned['MAPPED_DATE'] = pd.Timestamp.now()
                    
                    st.session_state.df_cleaned = df_cleaned
                    st.success(f"✅ Mappings applied! New FRANCHISE column created.")
                    st.rerun()
            
            # Download section
            if 'df_cleaned' in st.session_state:
                st.markdown("---")
                st.header("Step 8: Download Results")
                
                with st.expander("📊 Preview Cleaned Data", expanded=True):
                    preview_cols = [campaign_col, 'FRANCHISE', 'DIVISION', 'BRAND']
                    available_cols = [col for col in preview_cols if col in st.session_state.df_cleaned.columns]
                    st.dataframe(st.session_state.df_cleaned[available_cols].head(30))
                
                # Export options
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # CSV download
                    csv = st.session_state.df_cleaned.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"franchises_identified_{selected_brand.replace(' ', '_')}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Excel download
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        st.session_state.df_cleaned.to_excel(writer, index=False, sheet_name='Identified Franchises')
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="📥 Download Excel",
                        data=excel_data,
                        file_name=f"franchises_identified_{selected_brand.replace(' ', '_')}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
                with col3:
                    # Mapping reference download
                    mapping_export = pd.DataFrame([
                        {
                            "Campaign": k, 
                            "Franchise": v, 
                            "Division": selected_division, 
                            "Brand": selected_brand
                        }
                        for k, v in mappings.items()
                    ])
                    mapping_csv = mapping_export.to_csv(index=False)
                    
                    st.download_button(
                        label="📥 Download Mappings",
                        data=mapping_csv,
                        file_name=f"mappings_{selected_brand.replace(' ', '_')}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                # Statistics
                st.markdown("---")
                st.subheader("📈 Statistics")
                
                franchise_counts = st.session_state.df_cleaned['FRANCHISE'].value_counts()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Franchise Distribution:**")
                    st.dataframe(franchise_counts.reset_index().rename(columns={'index': 'Franchise', 'FRANCHISE': 'Count'}))
                
                with col2:
                    st.markdown("**Coverage:**")
                    identified = (st.session_state.df_cleaned['FRANCHISE'] != 'Unknown').sum()
                    total = len(st.session_state.df_cleaned)
                    coverage = (identified / total * 100) if total > 0 else 0
                    
                    st.metric("Identified", f"{identified} / {total}")
                    st.metric("Coverage", f"{coverage:.1f}%")

else:
    st.info("👆 Please upload both the Master File and Campaign Data to continue")

# Footer
st.markdown("---")
st.markdown("Built with Streamlit & Claude AI | 🎯 AI-powered franchise identification from campaign text")