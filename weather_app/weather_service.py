# weather_service.py
"""Weather API service layer."""

import httpx
from typing import Dict, Optional
from config import Config
from pathlib import Path


class WeatherServiceError(Exception):
    """Custom exception for weather service errors."""
    pass


class WeatherService:
    """Service for fetching weather data from OpenWeatherMap API."""
    
    def __init__(self):
        self.api_key = Config.API_KEY
        self.base_url = Config.BASE_URL
        self.timeout = Config.TIMEOUT
    
        # Validate API key at service initialization so imports don't crash
        if not self.api_key:
            # Defer raising a hard error until a network call is attempted,
            # but provide a helpful message here for developers.
            # We do not raise here to keep instantiation lightweight; callers
            # will get a descriptive error when calling `get_weather`.
            pass
    async def get_weather(self, city: str) -> Dict:
        """
        Fetch weather data for a given city.
        
        Args:
            city: Name of the city
            
        Returns:
            Dictionary containing weather data
            
        Raises:
            WeatherServiceError: If the request fails
        """
        if not city:
            raise WeatherServiceError("City name cannot be empty")
        # Check API key availability
        if not self.api_key:
            raise WeatherServiceError(
                "Missing OpenWeather API key. Please set OPENWEATHER_API_KEY in a .env file or environment variables."
            )
        
        # Build request parameters
        params = {
            "q": city,
            "appid": self.api_key,
            "units": Config.UNITS,
        }
        
        try:
            # Make async HTTP request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                
                # Check for HTTP errors
                if response.status_code == 404:
                    raise WeatherServiceError(
                        f"City '{city}' not found. Please check the spelling."
                    )
                elif response.status_code == 401:
                    raise WeatherServiceError(
                        "Invalid API key. Please check your configuration."
                    )
                elif response.status_code >= 500:
                    raise WeatherServiceError(
                        "Weather service is currently unavailable. "
                        "Please try again later."
                    )
                elif response.status_code != 200:
                    raise WeatherServiceError(
                        f"Error fetching weather data: {response.status_code}"
                    )
                
                # Parse JSON response
                data = response.json()
                return data
                
        except httpx.TimeoutException:
            raise WeatherServiceError(
                "Request timed out. Please check your internet connection."
            )
        except httpx.NetworkError:
            raise WeatherServiceError(
                "Network error. Please check your internet connection."
            )
        except httpx.HTTPError as e:
            raise WeatherServiceError(f"HTTP error occurred: {str(e)}")
        except Exception as e:
            raise WeatherServiceError(f"An unexpected error occurred: {str(e)}")
    
    async def get_weather_by_coordinates(
        self, 
        lat: float, 
        lon: float
    ) -> Dict:
        """
        Fetch weather data by coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dictionary containing weather data
        """
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": Config.UNITS,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            raise WeatherServiceError(f"Error fetching weather data: {str(e)}")

    async def get_hourly_forecast(self, lat: float, lon: float) -> Dict:
        """Fetch hourly forecast (next 48 hours) using One Call API.

        Returns the JSON response with hourly data.
        """
        onecall_url = "https://api.openweathermap.org/data/2.5/onecall"
        params = {
            "lat": lat,
            "lon": lon,
            "exclude": "minutely,daily,alerts,current",
            "appid": self.api_key,
            "units": Config.UNITS,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(onecall_url, params=params)
                if response.status_code != 200:
                    raise WeatherServiceError(f"Error fetching forecast: {response.status_code}")
                return response.json()
        except httpx.TimeoutException:
            raise WeatherServiceError("Forecast request timed out.")
        except Exception as e:
            raise WeatherServiceError(f"Error fetching forecast: {str(e)}")
        
    async def get_weather_by_coords(self, lat, lon):
        url = f"{self.base_url}?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
        return await self._make_request(url)
