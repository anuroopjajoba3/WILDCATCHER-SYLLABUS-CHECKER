"""
user_location.py - Implementation of userLocation class from domain model
"""

class UserLocation:
    """
    Represents a geographical location with coordinates and name.
    Matches the userLocation class in your domain diagram.
    """
    
    def __init__(self, latitude: float, longitude: float, name: str):
        self.latitude = latitude
        self.longitude = longitude
        self.name = name
    
    def __str__(self):
        return f"{self.name} ({self.latitude}, {self.longitude})"
    
    def __repr__(self):
        return f"UserLocation(latitude={self.latitude}, longitude={self.longitude}, name='{self.name}')"
    
    @classmethod
    def from_dict(cls, location_data: dict):
        """Create UserLocation from dictionary data (e.g., from JSON file)"""
        return cls(
            latitude=location_data['latitude'],
            longitude=location_data['longitude'],
            name=location_data['name']
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'name': self.name
        }
