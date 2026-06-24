import sys
import os
from dotenv import load_dotenv

# Ensure the backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env variables
load_dotenv(override=True)

from src.graph.state import TransitOption, TravelMode
from src.tools.flights import get_airport_code

# Mock transit options from the test run
transit_options = [
    TransitOption(
        id="road_hyderabad_manali_0",
        origin="Hyderabad",
        destination="Manali",
        mode=TravelMode.DRIVING,
        duration_minutes=2138,
        estimated_price=30728,
        carrier="Self-Drive / Ride"
    ),
    TransitOption(
        id="road_manali_rishikesh_0",
        origin="Manali",
        destination="Rishikesh",
        mode=TravelMode.DRIVING,
        duration_minutes=598,
        estimated_price=7692,
        carrier="Self-Drive / Ride"
    ),
    TransitOption(
        id="road_rishikesh_dehradun_0",
        origin="Rishikesh",
        destination="Dehradun",
        mode=TravelMode.DRIVING,
        duration_minutes=67,
        estimated_price=605,
        carrier="Self-Drive / Ride"
    ),
    TransitOption(
        id="flight_dehradun_hyderabad_0",
        origin="Jolly Grant Airport - Dehradun (DED)",
        destination="Rajiv Gandhi International Airport (HYD)",
        mode=TravelMode.FLIGHT,
        duration_minutes=340,
        estimated_price=7475,
        carrier="IndiGo"
    )
]

def is_city_match(node: str, city: str) -> bool:
    n = node.lower().strip()
    c = city.lower().strip()
    
    # 1. Direct or substring matches
    if n == c or c in n or n in c:
        return True
        
    # 2. Match using airport code extraction
    import re
    
    n_iatas = re.findall(r'\(([a-z]{3})\)', n)
    c_iatas = re.findall(r'\(([a-z]{3})\)', c)
    
    c_code = get_airport_code(city).lower().strip()
    print(f"Matching node='{node}' with city='{city}'. c_code='{c_code}', n_iatas={n_iatas}")
    if n_iatas and c_code in n_iatas:
        return True
        
    n_code = get_airport_code(node).lower().strip()
    if c_iatas and n_code in c_iatas:
        return True
        
    # 3. Clean parenthesis fallbacks
    if "(" in n:
        n_clean = n.split("(")[0].strip()
        if n_clean == c or c in n_clean or n_clean in c:
            return True
    if "(" in c:
        c_clean = c.split("(")[0].strip()
        if n == c_clean or c_clean in n or n in c_clean:
            return True
            
    return False

def find_transit_path(start: str, end: str) -> list:
    from collections import deque
    queue = deque()
    
    # Enqueue initial segments
    for opt in transit_options:
        if is_city_match(opt.origin, start):
            queue.append((opt.destination, [opt]))
            
    visited = set()
    
    while queue:
        curr_city, path = queue.popleft()
        print(f"BFS Pop: curr_city='{curr_city}', path={[o.id for o in path]}")
        
        if is_city_match(curr_city, end):
            return path
            
        state_key = curr_city.lower().strip()
        if state_key in visited:
            continue
        visited.add(state_key)
        
        for opt in transit_options:
            if is_city_match(opt.origin, curr_city):
                if opt.destination.lower().strip() not in visited:
                    queue.append((opt.destination, path + [opt]))
                    
    return []

path = find_transit_path("Rishikesh", "Hyderabad")
print("\nFinal Path:")
for p in path:
    print(f"  {p.id}: {p.origin} -> {p.destination}")
