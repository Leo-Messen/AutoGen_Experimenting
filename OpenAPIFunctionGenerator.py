import requests
import inspect
from typing import Dict, Any, Callable
from urllib.parse import urljoin
from config import settings
from openapi_parser.enumeration import BaseLocation
from openapi_parser.specification import Security, SecurityType

from requests.models import Request

class OpenAPIFunctionGenerator:
    def __init__(self, base_url: str):
        """
        Initialize the function generator with a base URL.
        
        This allows us to create dynamic API call functions 
        for different endpoints while maintaining a consistent base.
        """
        self.base_url = base_url

    def create_api_function(
        self, 
        func_name,
        path: str, 
        http_method: str, 
        apikey_security : Security,
        required_params: list = None, 
        optional_params: list = None,
    ) -> Callable:
        """
        Dynamically create a function for making API calls.
        
        Args:
            path (str): The API endpoint path
            http_method (str): HTTP method (get, post, etc.)
            required_params (list): Parameters that must be provided
            optional_params (list): Parameters that can be optionally provided
            apikey_security (Security): Parameters that can be optionally provided
        
        Returns:
            Callable: A dynamically created function for the API endpoint
        """
        # Default to empty lists if not provided
        required_params = required_params or []
        optional_params = optional_params or []
        headers = {}
        
        # Create a signature with all possible parameters
        parameters = (
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation = param_type) for param, param_type in required_params] +
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation= param_type,default=None) for param, param_type in optional_params]
        )

        if apikey_security:
            if apikey_security.location == BaseLocation.QUERY:
                # Retrive API KEY and set it as a default parameter
                parameters.append(inspect.Parameter(apikey_security.name, inspect.Parameter.KEYWORD_ONLY, annotation=str ,default=settings.WEATHER_API_KEY))
            
            elif apikey_security.location == BaseLocation.HEADER:
                # Retrieve api key and add it to headers
                headers[apikey_security.name] = settings.WEATHER_API_KEY
        
        
        # The actual API call function to be returned
        def api_call_function(*args, **kwargs):
            # Validate required parameters are present
            bound_arguments = inspect.Signature(parameters).bind(*args, **kwargs)
            bound_arguments.apply_defaults()
            
            # Separate arguments into query parameters
            query_params = bound_arguments.arguments
            print(query_params)

            # Construct full URL
            full_url = urljoin(self.base_url, path)
            
            # Determine HTTP method dynamically
            request_method = getattr(requests, http_method.lower())
            
            # Make the API call
            try:
                response = request_method(full_url, params=query_params, headers = headers)
                response.raise_for_status()  # Raise an exception for bad responses
                return response.json()
            except requests.RequestException as e:
                print(f"API Call Error: {e}")
                raise
        
        # Set function metadata
        api_call_function.__name__ = func_name
        api_call_function.__signature__ = inspect.Signature(parameters)
        
        return api_call_function

# Demonstration
if __name__ == "__main__":
    # Your actual API key would go here
    API_KEY = settings.WEATHER_API_KEY
    BASE_URL = 'https://api.openweathermap.org'
    
    # Create the weather function
    generator = OpenAPIFunctionGenerator(BASE_URL)
    
    # Create the weather function with specific requirements
    get_weather = generator.create_api_function(
        path='/data/2.5/weather',
        func_name='get_weather',
        http_method='get',
        required_params=[('lat', float), ('lon', float)],
        optional_params=[('mode', str), ('units', str), ('lang',str)],
        apikey_security=Security(type=SecurityType.API_KEY, location=BaseLocation.QUERY, name='appid')
        
    )
    
    # Now you can call it like this
    weather_data = get_weather(
        lat=44.52, 
        lon=9.65, 
        units='metric'
    )
    print(inspect.signature(get_weather))
    print(weather_data)