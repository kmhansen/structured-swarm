import json

from swarm import Agent

from pydantic import BaseModel, Field

class Location(BaseModel):
    city: str
    country: str = Field(..., description="Country name. Must be in the local language of the city, e.g., Danmark for Lyngby.")
 
def get_weather(location: Location, time: str="now"):
    """Get the current weather in a given location.."""
    location = Location.model_validate(location)
    return json.dumps({"city": location.city, "country": location.country, "temperature": "65", "time": time})


def send_email(recipient, subject, body):
    print("Sending email...")
    print(f"To: {recipient}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    return "Sent!"


weather_agent = Agent(
    name="Weather Agent",
    instructions="You are a helpful agent.",
    functions=[get_weather, send_email],
)
