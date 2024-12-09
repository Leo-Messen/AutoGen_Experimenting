import requests
import inspect
from typing import Dict, Any, Callable
from urllib.parse import urljoin
from config import settings
from openapi_parser.enumeration import BaseLocation
from openapi_parser.specification import Security, SecurityType
from openapi_parser import parse, enumeration

from requests.models import Request
from autogen_core.components.tools import FunctionTool

class OpenAPIFunctionToolGenerator:
    @staticmethod
    def _get_required_params(operation):
        queryParams = operation.parameters
        requiredParams = [(qp.name, qp.schema.type) for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY and qp.required == True]

        for i in range(len(requiredParams)):
            if requiredParams[i][1].value == 'number':
                requiredParams[i] = (requiredParams[i][0],float)
            elif requiredParams[i][1].value == 'string':
                requiredParams[i] = (requiredParams[i][0],str)
        
        return requiredParams

    @staticmethod
    def _get_optional_params(operation):
        queryParams = operation.parameters
        optionalParams = [(qp.name, qp.schema.type) for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY and qp.required == False]

        for i in range(len(optionalParams)):
            if optionalParams[i][1].value == 'number':
                optionalParams[i] = (optionalParams[i][0],float)
            elif optionalParams[i][1].value == 'string':
                optionalParams[i] = (optionalParams[i][0],str)
        
        return optionalParams
    
    @staticmethod
    def openAPI_yaml_spec_to_functool(path) -> FunctionTool:
        specification = parse('tools.yaml')
        http_method = specification.paths[0].operations[0].method.value
        operationId = specification.paths[0].operations[0].operation_id
        security_schemas = specification.security_schemas['ApiKeyAuth']

        tool_desc = specification.paths[0].description
        
        rqP = OpenAPIFunctionGenerator._get_required_params(specification.paths[0].operations[0])
        optP = OpenAPIFunctionGenerator._get_optional_params(specification.paths[0].operations[0])

        tool_func = OpenAPIFunctionGenerator._create_api_function(
                                path=specification.paths[0].url,
                                base_url=specification.servers[0].url,
                                func_name=operationId,
                                http_method=http_method,
                                required_params=rqP,
                                optional_params=optP,
                                apikey_security = security_schemas
                )

        return FunctionTool(tool_func, tool_desc, name=operationId)
        

    @staticmethod
    def _create_api_function(
        func_name,
        base_url : str,
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
        def api_call_function(**kwargs):
            # Validate required parameters are present
            bound_arguments = inspect.Signature(parameters).bind(**kwargs)
            bound_arguments.apply_defaults()
            
            # Separate arguments into query parameters
            query_params = bound_arguments.arguments

            # Construct full URL
            full_url = urljoin(base_url, path)
            
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
        
        # Set function metadata to help with tool use
        api_call_function.__name__ = func_name
        api_call_function.__signature__ = inspect.Signature(parameters)

        return api_call_function

# Demonstration
if __name__ == "__main__":
    # Your actual API key would go here
    API_KEY = settings.WEATHER_API_KEY
    BASE_URL = 'https://api.openweathermap.org'
        
    # Create the weather function with specific requirements
    get_weather_generated = OpenAPIFunctionGenerator.openAPI_yaml_spec_to_functool('tools.yaml')
