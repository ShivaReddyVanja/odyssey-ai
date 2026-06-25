from typing_extensions import TypedDict
from typing import Dict, Any, List, Literal, Optional, Union
from pydantic import BaseModel,Field
from enum import Enum

class TravelMode(str,Enum):
    FLIGHT = "flight"
    TRAIN = "train"
    BUS = "bus"
    CAR_RENTAL = "car_rental"
    WALKING = "walking"
    DRIVING = "driving"
    TRANSIT = "transit"  # local public transport

class Location(BaseModel):
    name:str
    address:str
    latitude:float
    longitude:float

class PlaceCategory(str,Enum):
    FOOD = "food"
    STAY = "stay"
    SIGHTSEEING = "sightseeing"

class Place(BaseModel):
    type: Literal["place"] = "place"
    id:str
    name:str
    category:PlaceCategory
    location:Location
    rating:Optional[float]
    cost_estimate:Optional[float]
    description:str
    photo_url:Optional[str] = None
    destination:Optional[str] = None

class TransitOption(BaseModel):
    type: Literal["transit"] = "transit"
    id: str = Field(..., description="UUID of the transit option")
    origin:str = Field(..., description="Name of the origin place")
    destination:str = Field(..., description="Name of the destination")
    departure_time: Optional[str] = Field(None, description="Scheduled departure time (e.g. ISO format or HH:MM)")
    arrival_time: Optional[str] = Field(None, description="Scheduled arrival")
    mode: TravelMode
    duration_minutes : int = Field(...,description="Number of minutes required for travel")
    estimated_price: int = Field(..., description="Estimated price for the travel")
    carrier: Optional[str] = Field(None, description="Carrier, airline, or operator name")

# Union of Place and Transit for DayPlan timeline
ScheduleItem = Union[Place, TransitOption]

class DayPlan(BaseModel):
    day_number:int
    date:str
    schedule: List[ScheduleItem] = Field(default_factory=list)


class FullItinerary(BaseModel):
    destination:str
    duration_days:int
    theme:str
    start_date:str
    days:List[DayPlan]

    

class DestinationAllocation(BaseModel):
    destination: str = Field(..., description="Name of the city or destination")
    duration_days: int = Field(..., description="Number of days allocated to this destination")

class AgentState(TypedDict):
    user_prompt:str
    parsed_parameters: Dict[str,Any]
    clarification_questions: List[str]
    clarification_response: Dict[str,str]
    is_validated: bool

    planned_destinations: List[DestinationAllocation]
    transit:List[TransitOption]
    accommodation:List[Place]
    food:List[Place]
    activities:List[Place]
    final_itinerary: Optional[FullItinerary]
