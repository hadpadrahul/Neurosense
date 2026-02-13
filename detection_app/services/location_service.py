import requests
import math

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

# Configuration
SEARCH_RADIUS_KM = 30  # Default search radius in kilometers

def find_nearby_specialists(lat, lon, radius_km=SEARCH_RADIUS_KM):
    """
    Query Overpass API for neurologists and hospitals within radius_km.
    Returns a sorted list of dictionaries.
    """
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return []

    # Overpass QL Query
    # We look for nodes/ways/relations with tags indicating neurology or general hospitals
    # We fetch a slightly larger area (radius * 1000 meters) to filter precisely later
    radius_meters = radius_km * 1000
    
    query = f"""
    [out:json];
    (
      node["healthcare"="specialist"]["speciality"~"neurology",i](around:{radius_meters},{lat},{lon});
      node["name"~"Parkinson",i](around:{radius_meters},{lat},{lon});
      node["name"~"Movement.*Disorder",i](around:{radius_meters},{lat},{lon});
      node["amenity"="hospital"]["name"~"Neuro",i](around:{radius_meters},{lat},{lon});
      node["amenity"="clinic"]["name"~"Neuro",i](around:{radius_meters},{lat},{lon});
      node["amenity"="clinic"]["healthcare:speciality"~"neurology",i](around:{radius_meters},{lat},{lon});
      node["amenity"="hospital"](around:{radius_meters},{lat},{lon});
    );
    out center;
    """
    
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    try:
        response = requests.post(overpass_url, data={'data': query}, timeout=10)
        if response.status_code != 200:
            print(f"Overpass API Error: {response.status_code}")
            return []
            
        data = response.json()
        elements = data.get('elements', [])
        
        results = []
        for el in elements:
            # Get coordinates (node has lat/lon, way/relation has center info in 'center')
            el_lat = el.get('lat') or el.get('center', {}).get('lat')
            el_lon = el.get('lon') or el.get('center', {}).get('lon')
            
            if not el_lat or not el_lon:
                continue
                
            dist = haversine(lat, lon, el_lat, el_lon)
            
            # Filter strictly by radius (Overpass 'around' is generic)
            if dist > radius_km:
                continue
                
            tags = el.get('tags', {})
            name = tags.get('name', 'Unknown Medical Center')
            
            # Prioritize clean names
            if "neurology" in tags.get("speciality", "").lower():
                type_label = "Neurologist"
            elif "hospital" in tags.get("amenity", "").lower():
                type_label = "Hospital"
            else:
                type_label = "Clinic"

            # Create entry
            results.append({
                "name": name,
                "lat": el_lat,
                "lon": el_lon,
                "distance_km": round(dist, 2),
                "type": type_label,
                "address": tags.get("addr:street", "") or tags.get("addr:city", "")
            })
            
        # Sort by distance
        results.sort(key=lambda x: x['distance_km'])
        
        # Limit to reasonable number
        return results[:15]
        
    except Exception as e:
        print(f"Location Service Exception: {e}")
        return []
