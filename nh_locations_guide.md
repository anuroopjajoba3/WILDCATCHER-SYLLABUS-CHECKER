# New Hampshire Locations Dataset Guide

## Option 1: USGS GNIS (Recommended)
The Geographic Names Information System has comprehensive location data for NH.

### Steps:
1. Visit: https://geonames.usgs.gov/domestic/download_data.htm
2. Download NH data file (New Hampshire feature names)
3. This gives you cities, towns, geographic features with coordinates

### Data includes:
- City/town names
- Latitude/longitude coordinates  
- Feature types (populated places, schools, etc.)
- Elevation data

## Option 2: US Census Bureau
### Steps:
1. Visit: https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html
2. Download "2023 Gazetteer Files" 
3. Get places file for New Hampshire
4. Contains incorporated places with lat/lon

## Option 3: OpenStreetMap Data
### Using Overpass API:
```python
import requests

# Example query for NH cities
overpass_url = "http://overpass-api.de/api/interpreter"
overpass_query = """
[out:json];
(
  node["place"~"^(city|town|village)$"]["admin_level"~"^(6|8)$"](bbox:42.697,-72.557,45.305,-70.610);
);
out;
"""

response = requests.get(overpass_url, params={'data': overpass_query})
data = response.json()
```

## Option 4: Quick Start with Major NH Cities
Here's a starter dataset of major NH locations:

```python
nh_major_cities = [
    {"name": "Manchester", "lat": 42.9956, "lon": -71.4548},
    {"name": "Nashua", "lat": 42.7654, "lon": -71.4676},
    {"name": "Concord", "lat": 43.2081, "lon": -71.5376},
    {"name": "Dover", "lat": 43.1979, "lon": -70.8737},
    {"name": "Rochester", "lat": 43.3042, "lon": -70.9759},
    {"name": "Salem", "lat": 42.7876, "lon": -71.2011},
    {"name": "Merrimack", "lat": 42.8651, "lon": -71.4990},
    {"name": "Londonderry", "lat": 42.8651, "lon": -71.3740},
    {"name": "Hudson", "lat": 42.7659, "lon": -71.4342},
    {"name": "Keene", "lat": 42.9342, "lon": -72.2781},
    {"name": "Portsmouth", "lat": 43.0718, "lon": -70.7626},
    {"name": "Laconia", "lat": 43.5276, "lon": -71.4703},
    {"name": "Claremont", "lat": 43.3767, "lon": -72.3465},
    {"name": "Lebanon", "lat": 43.6422, "lon": -72.2517},
    {"name": "Berlin", "lat": 44.4687, "lon": -71.1851}
]
```

## Recommended Approach for Your Project:

1. **Start Simple**: Use the major cities list above for initial development
2. **Expand Later**: Add USGS GNIS data for comprehensive coverage
3. **Structure**: Save as JSON/CSV for easy loading in your app

## Implementation Steps:

### 1. Create locations data file:
```bash
# In your project directory
touch nh_locations.json
```

### 2. Add the data structure:
```python
# locations.py
import json

class LocationManager:
    def __init__(self):
        self.locations = self.load_locations()
    
    def load_locations(self):
        # Load from JSON file or return default set
        return nh_major_cities  # from above
    
    def get_coordinates(self, city_name):
        for location in self.locations:
            if location["name"].lower() == city_name.lower():
                return location["lat"], location["lon"]
        return None
```

### 3. For API integration:
```python
def get_location_data(city_name):
    coords = location_manager.get_coordinates(city_name)
    if coords:
        lat, lon = coords
        # Use these coordinates for Google API calls
        return call_google_apis(lat, lon)
```

Would you like me to help you implement any of these approaches or set up the initial project structure?
