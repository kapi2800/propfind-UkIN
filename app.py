"""
PropFind Uttarakhand v5.0 - Production Ready
- No emojis, uses Remix Icon CDN
- English to Hindi translation helper
- Clean, deployment-ready code
"""

import streamlit as st
import pandas as pd
from scraper_core import PropertyScraperCore
import time
import urllib.parse

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="PropFind Uttarakhand",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# CSS & ICONS
# ============================================
st.markdown("""
<link href="https://cdn.jsdelivr.net/npm/remixicon@3.5.0/fonts/remixicon.css" rel="stylesheet">
<style>
    .block-container { padding-top: 1.5rem; max-width: 98%; }
    header[data-testid="stHeader"] { height: 0; }
    
    /* Header styling */
    .app-title {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 5px;
    }
    .app-title i { font-size: 28px; color: #4f46e5; }
    .app-title span { font-size: 26px; font-weight: 700; }
    
    /* Button alignment */
    div.stButton > button { margin-top: 1.5rem; }
    
    /* Secondary button style */
    .secondary-btn button {
        background: transparent !important;
        border: 1px solid #e2e8f0 !important;
        color: #64748b !important;
    }
    
    /* Translate link */
    .translate-link {
        font-size: 12px; color: #6366f1; text-decoration: none;
        display: inline-flex; align-items: center; gap: 4px;
    }
    .translate-link:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# ============================================
# SESSION STATE
# ============================================
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = []
if 'clipboard' not in st.session_state:
    st.session_state.clipboard = []

# ============================================
# DATA MAPPINGS
# ============================================
DISTRICTS = {
    "01": "अल्मोड़ा (ALMORA)",
    "02": "बागेश्वर (BAGESHWAR)",
    "03": "चम्पावत (CHAMPAWAT)",
    "04": "देहरादून (DEHRADUN)",
    "05": "पौड़ी गढ़वाल (PAURI)",
    "06": "चमोली (CHAMOLI)",
    "07": "हरिद्वार (HARIDWAR)",
    "08": "नैनीताल (NAINITAL)",
    "09": "टिहरी गढ़वाल (TEHRI)",
    "10": "पिथौरागढ़ (PITHORAGARH)",
    "11": "रुद्रप्रयाग (RUDRAPRAYAG)",
    "12": "उधम सिंह नगर (U S NAGAR)",
    "13": "उत्तरकाशी (UTTARKASHI)",
}

SRO_BY_DISTRICT = {
    "01": {"01": "अल्मोड़ा (ALMORA)", "02": "रानीखेत (RANIKHET)", "03": "द्वाराहाट (DWARAHAT)"},
    "02": {"01": "बागेश्वर (BAGESHWAR)", "02": "कपकोट (KAPKOT)"},
    "03": {"01": "चम्पावत (CHAMPAWAT)", "02": "लोहाघाट (LOHAGHAT)", "03": "टनकपुर (TANAKPUR)"},
    "04": {"01": "देहरादून (DEHRADUN)", "02": "ऋषिकेश (RISHIKESH)", "03": "विकासनगर (VIKASNAGAR)", "04": "डोईवाला (DOIWALA)"},
    "05": {"01": "पौड़ी (PAURI)", "02": "कोटद्वार (KOTDWAR)", "03": "श्रीनगर (SRINAGAR)"},
    "06": {"01": "चमोली (CHAMOLI)", "02": "कर्णप्रयाग (KARNAPRAYAG)", "03": "जोशीमठ (JOSHIMATH)"},
    "07": {"01": "हरिद्वार (HARIDWAR)", "02": "रुड़की (ROORKEE)", "03": "लक्सर (LAKSAR)"},
    "08": {"01": "हल्द्वानी (HALDWANI)", "02": "नैनीताल (NAINITAL)", "03": "रामनगर (RAMNAGAR)", "04": "भीमताल (BHIMTAL)"},
    "09": {"01": "टिहरी (TEHRI)", "02": "नरेंद्रनगर (NARENDRANAGAR)", "03": "घनसाली (GHANSALI)"},
    "10": {"01": "पिथौरागढ़ (PITHORAGARH)", "02": "धारचूला (DHARCHULA)", "03": "बेरीनाग (BERINAG)"},
    "11": {"01": "रुद्रप्रयाग (RUDRAPRAYAG)", "02": "ऊखीमठ (UKHIMATH)"},
    "12": {"01": "बाजपुर (BAZPUR)", "02": "जसपुर (JASPUR)", "03": "काशीपुर (KASHIPUR)", "04": "खटीमा (KHATIMA)", "05": "सितारगंज (SITARGANJ)", "06": "रुद्रपुर (RUDRAPUR)"},
    "13": {"01": "उत्तरकाशी (UTTARKASHI)", "02": "भटवाड़ी (BHATWARI)", "03": "पुरोला (PUROLA)"},
}

# ============================================
# HEADER
# ============================================
st.title("PropFind")
st.caption("Property Search Engine | संपत्ति खोज इंजन")

# Disclaimer
st.warning("""
**Disclaimer**: This tool is for **educational and research purposes only**. 
No data is stored or collected. Not for commercial use.
""")

# ============================================
# CLIPBOARD
# ============================================
if st.session_state.clipboard:
    with st.expander(f"Saved Records ({len(st.session_state.clipboard)})", expanded=False):
        clip_df = pd.DataFrame(st.session_state.clipboard)
        st.dataframe(clip_df, use_container_width=True, hide_index=True)
        col_a, col_b, _ = st.columns([1, 1, 4])
        with col_a:
            csv_clip = clip_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download", csv_clip, "saved_records.csv", use_container_width=True)
        with col_b:
            if st.button("Clear", use_container_width=True):
                st.session_state.clipboard = []
                st.rerun()

st.divider()

# ============================================
# SEARCH FORM
# ============================================
# Row 1: Search Type Toggle
type_col, spacer = st.columns([2, 10])
with type_col:
    search_type = st.radio("Search By", ["Buyer", "Seller"], horizontal=True, label_visibility="collapsed", key="search_type")

# Row 2: Search Fields
col1, col2, col3, col4, col5, col6 = st.columns([3.5, 2.5, 2.5, 1.5, 1.5, 2])

with col1:
    name_input = st.text_input(f"{search_type} Name", placeholder="Enter name in Hindi or English...", key="name_input")
    # Translation helper link
    if name_input.strip():
        encoded_name = urllib.parse.quote(name_input)
        translate_url = f"https://translate.google.com/?sl=en&tl=hi&text={encoded_name}&op=translate"
        st.markdown(f'<a href="{translate_url}" target="_blank" class="translate-link"><i class="ri-translate"></i> Translate to Hindi</a>', unsafe_allow_html=True)

with col2:
    district_id = st.selectbox(
        "District",
        options=[""] + list(DISTRICTS.keys()),
        format_func=lambda x: "-- Select District --" if x == "" else DISTRICTS[x],
        index=0,
        key="district"
    )

with col3:
    sro_options = SRO_BY_DISTRICT.get(district_id, {}) if district_id else {}
    sro_id = st.selectbox(
        "SRO Office",
        options=[""] + list(sro_options.keys()) if sro_options else [""],
        format_func=lambda x: "-- Select SRO --" if x == "" else sro_options.get(x, x),
        index=0,
        disabled=not district_id,
        key="sro"
    )

with col4:
    year_options = [None] + list(range(2026, 2008, -1))
    from_year = st.selectbox("From", options=year_options, format_func=lambda x: "-- Year --" if x is None else str(x), index=0, key="from_year")

with col5:
    to_year = st.selectbox("To", options=year_options, format_func=lambda x: "-- Year --" if x is None else str(x), index=0, key="to_year")

with col6:
    search_btn = st.button(f"Search {search_type}s", type="primary", use_container_width=True, key="search_btn")

# Row 3: Action buttons
if st.session_state.scraped_data:
    btn_col1, btn_col2, _ = st.columns([1, 1, 10])
    with btn_col1:
        if st.button("New Search", use_container_width=True):
            st.session_state.scraped_data = []
            st.rerun()
    with btn_col2:
        st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
        if st.button("Clear Results", use_container_width=True, key="clr_results"):
            st.session_state.scraped_data = []
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# SEARCH EXECUTION
# ============================================
years_list = []
if from_year and to_year:
    years_list = [str(y) for y in range(min(from_year, to_year), max(from_year, to_year) + 1)]

if search_btn:
    if not name_input.strip():
        st.warning("Please enter a name to search")
    elif not district_id or not sro_id:
        st.warning("Please select District and SRO Office")
    elif not from_year or not to_year:
        st.warning("Please select year range")
    else:
        st.session_state.scraped_data = []
        
        progress = st.progress(0, text=f"Searching {search_type.lower()}s...")
        scraper = PropertyScraperCore(search_type=search_type.lower())
        
        for idx, year in enumerate(years_list):
            progress.progress(idx / len(years_list), text=f"Searching {year}...")
            
            for update in scraper.scrape_year(district_id, sro_id, year, name_input):
                if update["status"] == "data":
                    for rec in update["data"]:
                        rec["Year"] = year
                        rec["_id"] = f"{year}_{rec.get('RegNo', '')}_{rec.get('RegDate', '')}"
                    st.session_state.scraped_data.extend(update["data"])
                elif update["status"] == "error":
                    st.error(f"Error in {year}: {update['message']}")
        
        progress.progress(1.0, text="Search complete!")
        time.sleep(0.5)
        progress.empty()
        
        if st.session_state.scraped_data:
            st.success(f"Found {len(st.session_state.scraped_data)} records")
        else:
            st.info("No records found for this search")

# ============================================
# RESULTS TABLE
# ============================================
if st.session_state.scraped_data:
    st.divider()
    
    # Highlight controls
    hl_col1, hl_col2, hl_col3 = st.columns([1.5, 3, 4])
    with hl_col1:
        enable_hl = st.checkbox("Highlight", value=False)
    with hl_col2:
        hl_text = st.text_input("Match text", placeholder="e.g., Ram, S/O...", label_visibility="collapsed", disabled=not enable_hl)
    with hl_col3:
        hl_field = st.radio("Field", ["All", "Buyer", "Seller", "Village"], horizontal=True, label_visibility="collapsed", disabled=not enable_hl)
    
    # Prepare DataFrame
    df = pd.DataFrame(st.session_state.scraped_data)
    display_cols = ["Year", "RegDate", "RegNo", "Village", "Buyer", "Seller", "Amount", "MarketValue", "_id"]
    df = df[[c for c in display_cols if c in df.columns]]
    
    # Add save checkbox column
    df.insert(0, "Save", False)
    
    # Show data editor
    edited_df = st.data_editor(
        df,
        column_config={
            "Save": st.column_config.CheckboxColumn("Save", default=False, width="small"),
            "_id": None,
            "Amount": st.column_config.NumberColumn("Amount", format="₹%d"),
            "MarketValue": st.column_config.NumberColumn("Market Val", format="₹%d"),
        },
        disabled=[c for c in df.columns if c != "Save"],
        hide_index=True,
        use_container_width=True,
        height=450
    )
    
    # Process saves
    saved_rows = edited_df[edited_df["Save"] == True]
    if not saved_rows.empty:
        new_items = saved_rows.drop(columns=["Save"]).to_dict('records')
        existing_ids = {item.get("_id") for item in st.session_state.clipboard}
        added = 0
        for item in new_items:
            if item.get("_id") not in existing_ids:
                st.session_state.clipboard.append(item)
                added += 1
        if added > 0:
            st.toast(f"Added {added} records to clipboard!")
            time.sleep(0.8)
            st.rerun()

    # Download all results
    st.divider()
    csv_all = df.drop(columns=["Save", "_id"], errors='ignore').to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download All Results (CSV)",
        data=csv_all,
        file_name=f"propfind_{name_input}_{from_year}-{to_year}.csv",
        mime="text/csv"
    )

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.caption("PropFind | Educational & Non-Commercial Use Only | No data stored")
