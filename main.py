"""
E-Waste Management System - Streamlit Application
Main application file with all UI components
"""

import time
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from functions import (
    initialize_database, search_by_barcode, search_by_name,
    get_all_centers, classify_product, get_disposal_guidelines,
    add_new_product, get_statistics
)

# Page configuration
st.set_page_config(
    page_title="E-Waste Management System",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #2c3e50;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #27ae60 0%, #2ecc71 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .recommendation-box {
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .recycle { background-color: #f39c12; color: white; }
    .refurbish { background-color: #27ae60; color: white; }
    .dispose { background-color: #e74c3c; color: white; }
    .hazard-high { background-color: #e74c3c; color: white; padding: 0.5rem; border-radius: 5px; }
    .hazard-medium { background-color: #f39c12; color: white; padding: 0.5rem; border-radius: 5px; }
    .hazard-low { background-color: #27ae60; color: white; padding: 0.5rem; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# Initialize database on first run
if 'db_initialized' not in st.session_state:
    initialize_database()
    st.session_state.db_initialized = True

# Header
st.markdown('<div class="main-header">♻️ E-Waste Disposal & Recycling Guide</div>', unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("🔧 Navigation")
page = st.sidebar.radio(
    "Choose a feature:",
    ["🔍 Product Search", "📍 Recycling Centers", "➕ Add Product", "📊 Statistics"]
)

# ── Map helpers (used only on Page 2) ─────────────────────────────────────────
_geolocator = Nominatim(user_agent="ewaste_management_app_v1")

@st.cache_data(show_spinner=False, ttl=3600)
def geocode_address(address: str, city: str, state: str):
    """
    Convert address → (lat, lng) using free Nominatim / OpenStreetMap.
    Falls back to city-only if full address fails. Returns None on failure.
    Cached for 1 hour to avoid re-hitting the API on every rerun.
    """
    queries = [
        f"{address}, {city}, {state}",
        f"{city}, {state}",
        city,
    ]
    for query in queries:
        try:
            time.sleep(1)           # Nominatim rate limit: 1 request / second
            loc = _geolocator.geocode(query, timeout=10)
            if loc:
                return (loc.latitude, loc.longitude)
        except (GeocoderTimedOut, GeocoderServiceError):
            continue
    return None


def build_centers_map(centers: list) -> folium.Map:
    """
    Geocode each center and return a folium map with clickable markers.
    Markers show center name, phone, hours, and accepted items in a popup.
    """
    fallback = (20.5937, 78.9629)   # center of India as safe default
    coords, marker_data = [], []

    progress = st.progress(0, text="Locating centers on map…")
    for i, center in enumerate(centers):
        progress.progress(
            (i + 1) / len(centers),
            text=f"Locating {center['center_name']}…"
        )
        latlon = geocode_address(
            center.get("address", ""),
            center.get("city", ""),
            center.get("state", ""),
        )
        if latlon:
            coords.append(latlon)
            marker_data.append((*latlon, center))
    progress.empty()

    # Map centered on average of all located centers (or fallback)
    if coords:
        clat = sum(c[0] for c in coords) / len(coords)
        clng = sum(c[1] for c in coords) / len(coords)
    else:
        clat, clng = fallback

    m = folium.Map(
        location=[clat, clng],
        zoom_start=10 if len(coords) == 1 else 6,
        tiles="OpenStreetMap",      # free, no API key needed
    )

    for lat, lng, c in marker_data:
        popup_html = f"""
            <div style="min-width:210px;font-family:sans-serif;font-size:13px;">
                <b style="font-size:14px;">♻️ {c['center_name']}</b>
                <hr style="margin:5px 0;">
                📞 {c['phone']}<br>
                🕒 {c['operating_hours']}<br>
                📍 {c['city']}, {c['state']}<br>
                <small>♻️ {c['accepted_items']}</small>
            </div>
        """
        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=270),
            tooltip=c["center_name"],
            icon=folium.Icon(color="green", icon="recycle", prefix="fa"),
        ).add_to(m)

    # Auto-fit viewport to all markers when more than one exists
    if len(coords) > 1:
        m.fit_bounds([
            [min(c[0] for c in coords), min(c[1] for c in coords)],
            [max(c[0] for c in coords), max(c[1] for c in coords)],
        ])

    return m


# ============================================================================
# PAGE 1: PRODUCT SEARCH
# ============================================================================
if page == "🔍 Product Search":
    st.header("🔍 Product Search & Recommendations")
    
    # Search options
    search_type = st.radio("Search by:", ["Barcode", "Product Name"], horizontal=True)
    
    if search_type == "Barcode":
        col1, col2 = st.columns([3, 1])
        with col1:
            barcode = st.text_input("Enter Barcode:", placeholder="e.g., 8901234567890")
        with col2:
            st.write("")
            st.write("")
            search_btn = st.button("🔍 Search", use_container_width=True)
        
        # Sample barcodes
        with st.expander("📝 Sample Barcodes to Try"):
            st.write("""
            - `8901234567890` - Samsung Galaxy S20
            - `5901234123457` - Dell XPS 13 Laptop
            - `4006381333931` - Apple iPhone 12
            - `0012345678905` - HP LaserJet Printer
            - `7501234567897` - Sony LED TV
            """)
        
        if search_btn and barcode:
            product = search_by_barcode(barcode)
            
            if product:
                st.success(f"✅ Product Found: **{product['product_name']}**")
                
                # Product details
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📦 Product Details")
                    st.write(f"**Category:** {product['category']}")
                    st.write(f"**Manufacturer:** {product['manufacturer']}")
                    st.write(f"**Barcode:** {product['barcode']}")
                    st.write(f"**Description:** {product['description']}")
                
                with col2:
                    st.subheader("♻️ Disposal Recommendation")
                    
                    # Recommendation box
                    rec_class = product['disposal_recommendation'].lower()
                    st.markdown(
                        f'<div class="recommendation-box {rec_class}">'
                        f'{product["disposal_recommendation"].upper()}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Hazard level
                    hazard = product['hazard_level'].lower().replace(' ', '-')
                    st.markdown(
                        f'<div class="hazard-{hazard}">⚠️ Hazard Level: {product["hazard_level"]}</div>',
                        unsafe_allow_html=True
                    )
                
                # Recyclable components
                if product['recyclable_components']:
                    st.subheader("🔧 Recyclable Components")
                    st.info(product['recyclable_components'])
                
                # Detailed guidelines — fixed: use session_state toggle so it
                # persists across reruns without the button disappearing
                if 'show_guidelines' not in st.session_state:
                    st.session_state.show_guidelines = False

                if st.button("📋 View Detailed Disposal Guidelines"):
                    st.session_state.show_guidelines = not st.session_state.show_guidelines

                if st.session_state.show_guidelines:
                    guidelines = get_disposal_guidelines(
                        product['category'],
                        product['disposal_recommendation']
                    )
                    
                    st.subheader("📋 Disposal Guidelines")
                    
                    with st.expander("🛠️ Preparation Steps", expanded=True):
                        for step in guidelines['preparation_steps']:
                            st.write(f"• {step}")
                    
                    with st.expander("🗑️ Items to Remove"):
                        if guidelines['what_to_remove']:
                            for item in guidelines['what_to_remove']:
                                st.write(f"• {item}")
                        else:
                            st.write("No specific items to remove.")
                    
                    with st.expander("📍 Where to Take"):
                        for location in guidelines['where_to_take']:
                            st.write(f"• {location}")
                    
                    with st.expander("💡 Additional Tips"):
                        for tip in guidelines['additional_tips']:
                            st.write(f"• {tip}")
            else:
                st.error(f"❌ Product with barcode '{barcode}' not found in database.")
                st.info("💡 You can add this product using the 'Add Product' page.")
    
    else:  # Search by name
        col1, col2 = st.columns([3, 1])
        with col1:
            search_name = st.text_input("Search Product Name:", placeholder="e.g., laptop, phone")
        with col2:
            st.write("")
            st.write("")
            search_btn = st.button("🔍 Search", use_container_width=True)
        
        if search_btn and search_name:
            products = search_by_name(search_name)
            
            if products:
                st.success(f"✅ Found {len(products)} product(s)")
                
                # Display as table
                df = pd.DataFrame(products)
                df = df[['product_name', 'category', 'disposal_recommendation', 'hazard_level', 'manufacturer']]
                df.columns = ['Product', 'Category', 'Recommendation', 'Hazard Level', 'Manufacturer']
                
                st.dataframe(df, use_container_width=True, height=400)
                
                # Select product for details
                selected_product = st.selectbox(
                    "Select a product to view details:",
                    options=[p['product_name'] for p in products]
                )
                
                if selected_product:
                    product = next(p for p in products if p['product_name'] == selected_product)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Category:** {product['category']}")
                        st.write(f"**Manufacturer:** {product['manufacturer']}")
                        st.write(f"**Barcode:** {product['barcode']}")
                    
                    with col2:
                        rec_class = product['disposal_recommendation'].lower()
                        st.markdown(
                            f'<div class="recommendation-box {rec_class}">'
                            f'{product["disposal_recommendation"].upper()}'
                            f'</div>',
                            unsafe_allow_html=True
                        )
            else:
                st.warning("No products found matching your search.")

# ============================================================================
# PAGE 2: RECYCLING CENTERS  (with free OpenStreetMap via Folium)
# ============================================================================
elif page == "📍 Recycling Centers":
    st.header("📍 Find Recycling Centers")

    col1, col2 = st.columns([3, 1])
    with col1:
        city_search = st.text_input("Search by City:", placeholder="e.g., Madurai")
    with col2:
        st.write("")
        st.write("")
        show_all = st.button("Show All", use_container_width=True)

    if city_search or show_all:
        centers = get_all_centers(city_search if city_search else None)

        if centers:
            st.success(f"✅ Found {len(centers)} recycling center(s)")

            # ── Interactive Map ────────────────────────────────────────────────
            st.subheader("🗺️ Map View")
            st.caption("Click any green marker to see contact info and hours.")
            map_obj = build_centers_map(centers)
            st_folium(map_obj, use_container_width=True, height=430)

            st.divider()

            # ── Detail Cards (original layout, unchanged) ──────────────────────
            st.subheader("📋 Center Details")
            for i, center in enumerate(centers, 1):
                with st.expander(f"📍 {center['center_name']}", expanded=(i == 1)):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**📧 Contact Information:**")
                        st.write(f"📞 Phone: {center['phone']}")
                        st.write(f"✉️ Email: {center['email']}")
                        st.write(f"🌐 Website: {center['website']}")

                    with col2:
                        st.write("**📍 Location:**")
                        st.write(f"{center['address']}")
                        st.write(f"{center['city']}, {center['state']} {center['zip_code']}")

                    st.write("**🕒 Operating Hours:**")
                    st.info(center['operating_hours'])

                    st.write("**♻️ Accepted Items:**")
                    st.success(center['accepted_items'])
        else:
            st.warning("No recycling centers found.")

# ============================================================================
# PAGE 3: ADD PRODUCT
# ============================================================================
elif page == "➕ Add Product":
    st.header("➕ Add New Product")
    
    with st.form("add_product_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            barcode = st.text_input("Barcode* (must be unique):", placeholder="1234567890123")
            product_name = st.text_input("Product Name*:", placeholder="Samsung Galaxy S21")
            category = st.selectbox(
                "Category*:",
                ["Smartphone", "Laptop", "Tablet", "Television", "Monitor", 
                 "Printer", "Camera", "Gaming", "Audio", "Peripherals", 
                 "Battery", "Storage", "E-Reader", "Appliance"]
            )
            manufacturer = st.text_input("Manufacturer:", placeholder="Samsung")
        
        with col2:
            disposal = st.selectbox(
                "Disposal Recommendation*:",
                ["Dispose", "Recycle", "Refurbish"]
            )
            hazard = st.selectbox(
                "Hazard Level*:",
                ["Low", "Medium", "High", "Very High"]
            )
            components = st.text_input(
                "Recyclable Components:",
                placeholder="Battery, Display, Circuit Board"
            )
            description = st.text_area(
                "Description:",
                placeholder="Product description..."
            )
        
        submit = st.form_submit_button("➕ Add Product", use_container_width=True)
        
        if submit:
            if not all([barcode, product_name, category]):
                st.error("❌ Please fill in all required fields (marked with *)")
            else:
                success = add_new_product(
                    barcode, product_name, category, disposal, hazard,
                    description, manufacturer, components
                )
                
                if success:
                    st.success(f"✅ Product '{product_name}' added successfully!")
                    st.balloons()
                else:
                    st.error("❌ Failed to add product. Barcode may already exist.")

# ============================================================================
# PAGE 4: STATISTICS
# ============================================================================
elif page == "📊 Statistics":
    st.header("📊 E-Waste Statistics & Information")
    
    stats = get_statistics()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Total Products", stats['total_products'])
    
    with col2:
        st.metric("📍 Recycling Centers", stats['total_centers'])
    
    with col3:
        st.metric("♻️ Should Recycle", stats['recycle_count'])
    
    with col4:
        st.metric("⚠️ High Hazard", stats['high_hazard_count'])
    
    st.write("")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Disposal Recommendations")
        if stats['disposal_stats']:
            disposal_df = pd.DataFrame(
                stats['disposal_stats'],
                columns=['Recommendation', 'Count']
            )
            st.bar_chart(disposal_df.set_index('Recommendation'))
    
    with col2:
        st.subheader("⚠️ Hazard Levels")
        if stats['hazard_stats']:
            hazard_df = pd.DataFrame(
                stats['hazard_stats'],
                columns=['Hazard Level', 'Count']
            )
            st.bar_chart(hazard_df.set_index('Hazard Level'))
    
    # Category breakdown
    st.subheader("📦 Products by Category")
    if stats['category_stats']:
        category_df = pd.DataFrame(
            stats['category_stats'],
            columns=['Category', 'Count']
        )
        st.dataframe(category_df, use_container_width=True)
    
    # E-Waste facts
    st.subheader("🌍 E-Waste Facts")
    
    facts_col1, facts_col2 = st.columns(2)
    
    with facts_col1:
        st.info("""
        **Environmental Impact:**
        - 50 million tons of e-waste generated annually worldwide
        - Only 20% is formally recycled
        - Improper disposal contaminates soil and water
        - E-waste contains toxic materials like lead and mercury
        """)
    
    with facts_col2:
        st.success("""
        **Recovery Potential:**
        - $62.5 billion worth of recoverable materials in e-waste
        - Contains gold, silver, copper, and rare earth metals
        - Recycling uses less energy than mining virgin materials
        - 1 million recycled laptops saves energy for 3,657 homes/year
        """)
    
    # Why it matters
    st.subheader("💡 Why Proper E-Waste Disposal Matters")
    
    with st.expander("🌱 Environmental Protection"):
        st.write("Prevents toxic materials from entering landfills and contaminating ecosystems.")
    
    with st.expander("♻️ Resource Recovery"):
        st.write("Recovers valuable metals like gold, silver, copper, and rare earth elements.")
    
    with st.expander("⚡ Energy Conservation"):
        st.write("Recycling uses less energy than mining and processing virgin materials.")
    
    with st.expander("🏥 Health Protection"):
        st.write("Reduces exposure to hazardous materials like lead, mercury, and cadmium.")
    
    with st.expander("💼 Economic Benefits"):
        st.write("Creates jobs and reduces the need for expensive raw material extraction.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #7f8c8d;'>"
    "©Cult"
    "</div>",
    unsafe_allow_html=True
)