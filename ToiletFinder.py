import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(layout="wide")
st.title("🚻 Public Toilet Finder")
st.markdown("Find nearby public toilets in major European cities or based on your current location.")

# Initialize variables
lat, lon = None, None
city = None

st.markdown("### 📍 Detect your current location")

# GPS detection block
coords = None
if st.button("Use GPS", key="gps_button_main"):
    coords = streamlit_js_eval(
        js_expressions="""
        new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                resolve({ error: "Geolocation not supported by this browser." });
            } else {
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude });
                    },
                    (err) => {
                        resolve({ error: "Geolocation error: " + err.message });
                    }
                );
            }
        })
        """,
        key="get_position"
    )

# Always show raw response for debugging
st.markdown("#### 🛠️ Debug: Raw GPS Response")
st.write(coords)

# Handle GPS result
if coords and isinstance(coords, dict):
    if "latitude" in coords and "longitude" in coords:
        lat = coords["latitude"]
        lon = coords["longitude"]
        st.success(f"✅ GPS location detected: {lat:.4f}, {lon:.4f}")
    elif "error" in coords:
        st.error(f"⚠️ GPS error: {coords['error']}")
    else:
        st.error("❌ Could not get GPS location. Try allowing location access or use manual entry.")

# Manual fallback
if lat is None or lon is None:
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
st.markdown("### 🧪 Manual GPS override (for testing)")
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