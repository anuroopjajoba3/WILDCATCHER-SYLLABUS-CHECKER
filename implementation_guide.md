# Implementation Guide for NH Air Quality App
# Based on your Domain Class Diagram

## 1. Project Structure Setup

```
nh-air-quality-app/
├── src/
│   ├── models/
│   │   ├── user_location.py
│   │   ├── user.py
│   │   └── allergy_info.py
│   ├── services/
│   │   ├── gps.py
│   │   ├── google_maps.py
│   │   └── app.py
│   ├── data/
│   │   └── nh_locations.json
│   └── utils/
├── tests/
├── main.py
└── requirements.txt
```

## 2. Implementation Based on Your Classes

### userLocation Class
```python
# src/models/user_location.py
class UserLocation:
    def __init__(self, latitude: float, longitude: float, name: str):
        self.latitude = latitude
        self.longitude = longitude
        self.name = name
    
    @classmethod
    def from_name(cls, location_name: str):
        """Create UserLocation from NH location name"""
        # Load from nh_locations.json
        pass
```

### allergyInfo Class
```python
# src/models/allergy_info.py
class AllergyInfo:
    def __init__(self):
        self.plants = []
    
    def get_user_allergies(self, user):
        """Get allergies from user input"""
        self.plants = user.allergies.split(',')
        return self.plants
    
    def check_allergen(self, plant: str) -> str:
        """Check if plant is in user's allergy list"""
        return plant if plant in self.plants else None
```

### GPS Class
```python
# src/services/gps.py
import json
from models.user_location import UserLocation

class GPS:
    def __init__(self):
        self.nh_locations = self.load_nh_locations()
    
    def load_nh_locations(self):
        """Load NH locations from JSON file"""
        with open('src/data/nh_locations.json', 'r') as f:
            return json.load(f)
    
    def get_current_coordinates(self, location_name: str) -> UserLocation:
        """Get coordinates for NH location by name"""
        for location in self.nh_locations:
            if location['name'].lower() == location_name.lower():
                return UserLocation(
                    latitude=location['latitude'],
                    longitude=location['longitude'], 
                    name=location['name']
                )
        return None
```

### googleMaps Class
```python
# src/services/google_maps.py
import requests
import os
from models.user_location import UserLocation

class GoogleMaps:
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.air_quality_url = "https://airquality.googleapis.com/v1/currentConditions:lookup"
        self.pollen_url = "https://pollen.googleapis.com/v1/forecast:lookup"
    
    def get_air_quality(self, user_location: UserLocation):
        """Get air quality data from Google API"""
        headers = {'X-Goog-Api-Key': self.api_key}
        data = {
            "location": {
                "latitude": user_location.latitude,
                "longitude": user_location.longitude
            }
        }
        response = requests.post(self.air_quality_url, json=data, headers=headers)
        return response.json()
    
    def get_pollen_info(self, user_location: UserLocation, allergy_info):
        """Get pollen data from Google API"""
        headers = {'X-Goog-Api-Key': self.api_key}
        data = {
            "location": {
                "latitude": user_location.latitude,
                "longitude": user_location.longitude
            },
            "days": 1
        }
        response = requests.post(self.pollen_url, json=data, headers=headers)
        return response.json()
```

## 3. Getting Started Steps

### Step 1: Set up your environment
```bash
# Create project directory
mkdir nh-air-quality-app
cd nh-air-quality-app

# Initialize Poetry
poetry init
poetry add requests python-dotenv

# Create directory structure
mkdir -p src/{models,services,data,utils}
mkdir tests
```

### Step 2: Get Google API Keys
1. Go to Google Cloud Console
2. Enable these APIs:
   - Air Quality API
   - Maps Platform Weather API
3. Create API key and save to .env file:
```
GOOGLE_API_KEY=your_api_key_here
```

### Step 3: Use the NH locations dataset
- Copy the `nh_locations_starter.json` I created
- Place it in `src/data/nh_locations.json`

## 4. Expanding the Dataset

### For comprehensive NH locations:
1. **USGS GNIS** (recommended for complete dataset):
   - Visit: https://geonames.usgs.gov/domestic/download_data.htm
   - Download NH geographic names file
   - Contains thousands of NH locations

2. **US Census Gazetteer Files**:
   - Visit: https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html
   - Download places file for New Hampshire

### Processing larger datasets:
```python
# Script to convert USGS data to your format
import pandas as pd

def process_usgs_data(file_path):
    # Read USGS file (pipe-delimited)
    df = pd.read_csv(file_path, sep='|')
    
    # Filter for populated places in NH
    nh_places = df[
        (df['STATE_ALPHA'] == 'NH') & 
        (df['FEATURE_CLASS'] == 'Populated Place')
    ]
    
    # Convert to your format
    locations = []
    for _, row in nh_places.iterrows():
        locations.append({
            'name': row['FEATURE_NAME'],
            'latitude': row['PRIM_LAT_DEC'],
            'longitude': row['PRIM_LONG_DEC'],
            'type': 'place',
            'county': row['COUNTY_NAME']
        })
    
    return locations
```

## 5. Testing Your Setup

Create a simple test to verify everything works:

```python
# test_location_lookup.py
from src.services.gps import GPS
from src.services.google_maps import GoogleMaps

# Test location lookup
gps = GPS()
location = gps.get_current_coordinates("Manchester")
print(f"Found: {location.name} at {location.latitude}, {location.longitude}")

# Test API (with your API key)
google_maps = GoogleMaps()
air_data = google_maps.get_air_quality(location)
print(f"Air quality data: {air_data}")
```

This gives you a solid foundation that matches your domain model and can be expanded as needed!
