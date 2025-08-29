import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("🚻 Public Toilet Finder")
st.markdown("Find nearby public toilets in major European cities or based on your current location.")

# Initialize variables
lat, lon = None, None

# Location mode toggle
mode = st.radio("Choose location mode:", ["GPS", "Manual"], horizontal=True)

# GPS detection block
if mode == "GPS":
    st.markdown("### 📍 Detect your current location")

    # Inject HTML/JS block
    components.html(
        """
        <script>
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const coords = {
                    lat: position.coords.latitude,
                    lon: position.coords.longitude
                };
                window.parent.postMessage(coords, "*");
            },
            (error) => {
                window.parent.postMessage({ error: error.message }, "*");
            }
        );
        </script>
        """,
        height=0
    )

    # Listen for GPS data via query params
    raw_coords = st.query_params

    # Debug output
    st.markdown("#### 🛠️ Debug: Raw GPS Response")
    st.write(raw_coords)

    # Extract lat/lon if available
    if "lat" in raw_coords and "lon" in raw_coords:
        try:
            lat = float(raw_coords["lat"][0])
            lon = float(raw_coords["lon"][0])
            st.success(f"✅ GPS location detected: {lat:.4f}, {lon:.4f}")
        except ValueError:
            st.error("❌ Invalid GPS data received.")
    elif "error" in raw_coords:
        st.error(f"⚠️ GPS error: {raw_coords['error'][0]}")
    else:
        st.info("Waiting for GPS data...")

# Manual fallback
if mode == "Manual" or (lat is None and lon is None):
    st.markdown("### 🏙️ Manual location input")
    city = st.text_input("Enter a city (e.g. London, Paris, Rome):", key="city_input")

    def get_coordinates(city_name):
        geolocator = Nominatim(user_agent="toilet_finder", timeout=5)
        try:
            location = geolocator.geocode(city_name)
            if location:
                return location.latitude, location.longitude
        except Exception as e:
            st.error(f"Geocoding failed: {e}")
        return None, None

    if city:
        lat, lon = get_coordinates(city)
        if lat and lon:
            st.success(f"📍 Coordinates for {city}: {lat:.4f}, {lon:.4f}")
        else:
            st.error("❌ Could not find coordinates for that city.")

    # Manual override for testing
    st.markdown("### 🧪 Manual GPS override (optional)")
    manual_lat = st.text_input("Latitude", value="", key="manual_lat")
    manual_lon = st.text_input("Longitude", value="", key="manual_lon")

    if manual_lat and manual_lon:
        try:
            lat = float(manual_lat)
            lon = float(manual_lon)
            st.info(f"📍 Using manual coordinates: {lat:.4f}, {lon:.4f}")
        except ValueError:
            st.warning("Invalid manual coordinates. Please enter valid numbers.")

# Radius slider
radius = st.slider("Search radius (meters)", min_value=500, max_value=5000, value=1500, step=100)

# Query Overpass API
def query_toilets(lat, lon, radius):
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node["amenity"="toilets"](around:{radius},{lat},{lon});
    );
    out body;
    """
    try:
        response = requests.post(overpass_url, data=query, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("elements", [])
    except Exception as e:
        st.error(f"Error querying Overpass API: {e}")
        return []

# Display map
def display_map(toilets, lat, lon):
    m = folium.Map(location=[lat, lon], zoom_start=15)

    folium.Marker(
        location=[lat, lon],
        popup="You are here",
        icon=folium.Icon(color="green", icon="user")
    ).add_to(m)

    for toilet in toilets:
        name = toilet.get("tags", {}).get("name", "Public Toilet")
        t_lat, t_lon = toilet["lat"], toilet["lon"]
        distance = geodesic((lat, lon), (t_lat, t_lon)).meters
        popup_text = f"""
        {name}<br>
        {round(distance)}m away<br>
        <a href='https://www.google.com/maps/dir/?api=1&destination={t_lat},{t_lon}' target='_blank'>Navigate</a>
        """
        folium.Marker(
            location=[t_lat, t_lon],
            popup=popup_text,
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

    st_folium(m, width=700, height=500)

# Trigger search and map display
if lat and lon:
    toilets = query_toilets(lat, lon, radius)
    if toilets:
        st.write(f"🚽 Found {len(toilets)} public toilets nearby.")
        display_map(toilets, lat, lon)
    else:
        st.warning("😕 No public toilets found nearby. Try a different location or increase the search radius.")