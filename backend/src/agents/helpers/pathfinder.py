import re
from typing import List
from collections import deque
from src.graph.state import TransitOption
from src.tools.flights import get_airport_code, resolve_nearest_airport

def normalize_city_name(name: str) -> str:
    n = name.lower().strip()
    # Replace known alias words/substrings
    replacements = {
        "madras": "chennai",
        "trivandrum": "thiruvananthapuram",
        "cochin": "kochi",
        "vasco da gama": "goa",
        "kulu": "kullu"
    }
    for old, new in replacements.items():
        n = n.replace(old, new)
    return n

def is_city_match(node: str, city: str) -> bool:
    n = normalize_city_name(node)
    c = normalize_city_name(city)
    
    # 1. Direct or substring matches
    if n == c or c in n or n in c:
        return True
        
    # 2. Match using airport code extraction
    n_iatas = re.findall(r'\(([a-z]{3})\)', n)
    c_iatas = re.findall(r'\(([a-z]{3})\)', c)
    
    def is_primary_airport_city(city_name: str) -> bool:
        try:
            info = resolve_nearest_airport(city_name)
            airport_city = normalize_city_name(info.airport_city)
            target_city = normalize_city_name(city_name)
            return target_city in airport_city or airport_city in target_city
        except Exception:
            return False
    
    c_code = get_airport_code(city).lower().strip()
    if n_iatas and c_code in n_iatas and is_primary_airport_city(city):
        return True
        
    n_code = get_airport_code(node).lower().strip()
    if c_iatas and n_code in c_iatas and is_primary_airport_city(node):
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

def find_transit_path(start: str, end: str, transit_options: List[TransitOption]) -> List[TransitOption]:
    queue = deque()
    
    # Enqueue initial segments
    for opt in transit_options:
        if is_city_match(opt.origin, start):
            queue.append((opt.destination, [opt]))
            
    visited = set()
    
    while queue:
        curr_city, path = queue.popleft()
        
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
                    
    # Fallback 1: ID prefix matches
    s_key = start.lower().strip().replace(' ', '_')
    e_key = end.lower().strip().replace(' ', '_')
    for opt in transit_options:
        opt_id = opt.id.lower()
        if s_key in opt_id and e_key in opt_id:
            if opt_id.find(s_key) < opt_id.find(e_key):
                return [opt]
                
    # Fallback 2: Direct match
    for opt in transit_options:
        if is_city_match(opt.origin, start) and is_city_match(opt.destination, end):
            return [opt]
            
    return []
