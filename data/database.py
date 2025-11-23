"""
Database module for FoodLink LA
Handles loading resources and basic queries
"""

import json
import math
from typing import List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from models.schemas import Resource, Hours


class ResourceDatabase:
    """Manages food resource data"""
    
    def __init__(self, data_file: str = "data/resources.json"):
        """Initialize database with resource data file"""
        self.data_file = Path(data_file)
        self.resources: List[Resource] = []
        self.load_resources()
    
    def load_resources(self) -> None:
        """Load resources from JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                
            # Parse resources into Pydantic models
            for resource_data in data.get('resources', []):
                # Convert hours dict to Hours objects
                hours_dict = {}
                for day, hours_data in resource_data['hours'].items():
                    hours_dict[day] = Hours(**hours_data)
                
                resource_data['hours'] = hours_dict
                resource = Resource(**resource_data)
                self.resources.append(resource)
            
            print(f"✅ Loaded {len(self.resources)} resources from {self.data_file}")
        
        except FileNotFoundError:
            print(f"⚠️  Warning: Resource file {self.data_file} not found")
            self.resources = []
        except Exception as e:
            print(f"❌ Error loading resources: {e}")
            self.resources = []
    
    def get_all_resources(self) -> List[Resource]:
        """Get all resources"""
        return self.resources
    
    def get_resource_by_id(self, resource_id: str) -> Optional[Resource]:
        """Get a specific resource by ID"""
        for resource in self.resources:
            if resource.id == resource_id:
                return resource
        return None
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        Returns distance in miles
        """
        # Radius of Earth in miles
        R = 3959.0
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return round(distance, 2)
    
    def is_open_now(self, resource: Resource) -> bool:
        """Check if a resource is currently open"""
        now = datetime.now()
        day_name = now.strftime('%A').lower()
        
        if day_name not in resource.hours:
            return False
        
        day_hours = resource.hours[day_name]
        
        if day_hours.status != "open":
            return False
        
        if not day_hours.open or not day_hours.close:
            return False
        
        try:
            # Parse time strings (format: "HH:MM")
            open_time = datetime.strptime(day_hours.open, "%H:%M").time()
            close_time = datetime.strptime(day_hours.close, "%H:%M").time()
            current_time = now.time()
            
            return open_time <= current_time <= close_time
        except Exception:
            return False
    
    def search_resources(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        max_distance_miles: float = 5.0,
        dietary_needs: Optional[List[str]] = None,
        open_now: bool = False,
        resource_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Resource]:
        """
        Search for resources based on criteria
        
        Args:
            lat: User's latitude
            lon: User's longitude
            max_distance_miles: Maximum distance in miles
            dietary_needs: List of dietary requirements (e.g., ["vegan", "gluten-free"])
            open_now: Only show resources open right now
            resource_types: Filter by resource type (e.g., ["food_pantry", "meal_service"])
            limit: Maximum number of results
        
        Returns:
            List of matching resources, sorted by distance
        """
        results = []
        
        for resource in self.resources:
            # Check if open now (if required)
            if open_now and not self.is_open_now(resource):
                continue
            
            # Check resource type filter
            if resource_types and resource.type not in resource_types:
                continue
            
            # Check dietary needs
            if dietary_needs:
                # Check if resource offers at least one of the dietary options
                has_dietary_match = any(
                    need.lower() in [opt.lower() for opt in resource.dietary_options]
                    for need in dietary_needs
                )
                if not has_dietary_match:
                    continue
            
            # Calculate distance if location provided
            distance = None
            if lat is not None and lon is not None:
                distance = self.calculate_distance(lat, lon, resource.lat, resource.lon)
                
                # Skip if too far
                if distance > max_distance_miles:
                    continue
            
            # Create a copy with computed fields
            resource_copy = resource.model_copy()
            resource_copy.distance_miles = distance
            resource_copy.is_open_now = self.is_open_now(resource)
            
            results.append(resource_copy)
        
        # Sort by distance (if location provided)
        if lat is not None and lon is not None:
            results.sort(key=lambda r: r.distance_miles if r.distance_miles else float('inf'))
        
        return results[:limit]
    
    def get_resources_by_target_population(self, population: str) -> List[Resource]:
        """Get resources that serve a specific population"""
        return [r for r in self.resources if r.target_population == population or r.target_population == "general"]
    
    def format_resource_for_display(self, resource: Resource) -> str:
        """Format a resource for text display"""
        lines = [
            f"📍 **{resource.name}**",
            f"Address: {resource.address}",
            f"Phone: {resource.phone}",
        ]
        
        if resource.distance_miles is not None:
            lines.append(f"Distance: {resource.distance_miles} miles")
        
        if resource.is_open_now is not None:
            status = "🟢 OPEN NOW" if resource.is_open_now else "🔴 Currently Closed"
            lines.append(status)
        
        # Today's hours
        today = datetime.now().strftime('%A').lower()
        if today in resource.hours:
            day_hours = resource.hours[today]
            if day_hours.status == "open" and day_hours.open and day_hours.close:
                lines.append(f"Today's Hours: {day_hours.open} - {day_hours.close}")
        
        lines.append(f"Offerings: {', '.join(resource.offerings[:3])}")
        
        if resource.dietary_options:
            lines.append(f"Dietary Options: {', '.join(resource.dietary_options)}")
        
        if resource.requirements and resource.requirements.lower() != "no restrictions":
            lines.append(f"⚠️ Requirements: {resource.requirements}")
        
        if resource.notes:
            lines.append(f"Note: {resource.notes[:100]}...")
        
        return "\n".join(lines)


# Global database instance
_db_instance: Optional[ResourceDatabase] = None


def get_database() -> ResourceDatabase:
    """Get or create the global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ResourceDatabase()
    return _db_instance
