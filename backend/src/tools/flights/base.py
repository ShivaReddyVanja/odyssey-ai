from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field
from src.graph.state import TransitOption

class FlightProvider(ABC):
    @abstractmethod
    def search_flights(self, origin: str, destination: str, start_date: str) -> List[TransitOption]:
        """
        Abstract method to search for flight options.
        """
        pass

class NearestAirportResolution(BaseModel):
    airport_city: str = Field(..., description="The name of the nearest city with a major commercial airport.")
    iata_code: str = Field(..., description="The 3-letter IATA code of that nearest major commercial airport.")

class AirportDetails(BaseModel):
    airport_city: str = Field(..., description="The city or region name of the airport.")
    iata_code: str = Field(..., description="The 3-letter IATA code of that airport.")
    distance_km: float = Field(..., description="Approximate driving distance in km from the target city.")

class CandidateAirportsResolution(BaseModel):
    airports: List[AirportDetails] = Field(..., description="List of up to 3 nearest commercial airports.")

class SelectedAirport(BaseModel):
    airport_city: str = Field(..., description="The city name of the selected best airport.")
    iata_code: str = Field(..., description="The 3-letter IATA code of the selected airport.")
    reasoning: str = Field(..., description="Brief explanation of why this airport is selected.")
