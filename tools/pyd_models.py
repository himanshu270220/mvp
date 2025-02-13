from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class ActivityDetail(BaseModel):
    type: Literal["activity"] = Field(
        "activity",
        description="The type identifier for activity entries. Must be set to 'activity'."
    )
    title: str = Field(
        ...,
        description="The name or title of the specific activity or attraction."
    )
    description: str = Field(
        ...,
        description="A detailed description explaining what the activity entails and what visitors can expect."
    )
    duration: str = Field(
        ...,
        description="The length of time the activity takes, specified in hours or minutes."
    )
    image: str = Field(
        ...,
        description="The URL link to an image representing this specific activity."
    )

class HotelDetail(BaseModel):
    type: Literal["hotel"] = Field(
        "hotel",
        description="The type identifier for hotel entries. Must be set to 'hotel'."
    )
    title: str = Field(
        ...,
        description="The name of the hotel or accommodation property."
    )
    description: str = Field(
        ...,
        description="A detailed description of the hotel, including its features, amenities, and location benefits."
    )
    rating: float = Field(
        ...,
        description="The hotel's rating on a scale of 0 to 5 stars, can include decimals for precise ratings.",
        ge=0,
        le=5
    )
    image: str = Field(
        ...,
        description="The URL link to an image of the hotel, typically showing the exterior or rooms."
    )

class ItineraryDay(BaseModel):
    active: bool = Field(
        ...,
        description="A flag indicating if this day's itinerary is currently available or bookable."
    )
    description: str = Field(
        ...,
        description="A brief summary describing the theme or main focus of this day's activities."
    )
    details: List[ActivityDetail | HotelDetail] = Field(
        ...,
        description="A chronological list of all activities and hotel arrangements scheduled for this day."
    )

class TravelPackage(BaseModel):
    name: str = Field(
        ...,
        description="The primary title of the travel package that captures its essence and destination."
    )
    subtitle: str = Field(
        ...,
        description="A short, engaging description that highlights the key appeal of the package."
    )
    image: str = Field(
        ...,
        description="The URL link to the main hero image representing the entire travel package."
    )
    duration: int = Field(
        ...,
        description="The total number of days included in the travel package.",
        gt=0
    )
    itinerary_detail: List[ItineraryDay] = Field(
        ...,
        description="A comprehensive day-by-day breakdown of all activities and accommodations in the package."
    )