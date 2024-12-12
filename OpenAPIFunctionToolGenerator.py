import requests
import inspect
import pprint
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
    def _get_required_query_params(operation):
        queryParams = operation.parameters
        requiredParams = [(qp.name, qp.schema.type) for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY and qp.required == True]

        for i in range(len(requiredParams)):
            if requiredParams[i][1].value == 'number':
                requiredParams[i] = (requiredParams[i][0],float)
            elif requiredParams[i][1].value == 'string':
                requiredParams[i] = (requiredParams[i][0],str)
        
        return requiredParams

    @staticmethod
    def _get_optional_query_params(operation):
        queryParams = operation.parameters
        optionalParams = [(qp.name, qp.schema.type) for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY and qp.required == False]

        for i in range(len(optionalParams)):
            if optionalParams[i][1].value == 'number':
                optionalParams[i] = (optionalParams[i][0],float)
            elif optionalParams[i][1].value == 'string':
                optionalParams[i] = (optionalParams[i][0],str)
        
        return optionalParams
    
    @staticmethod
    def _get_required_body_params(body):
        if body == None:
            return []
        
        body_properties = body.content[0].schema.properties
        required_properties = body.content[0].schema.required
            
        required = [(bp.name, bp.schema.type) for bp in body_properties if bp.name in required_properties]

        for i in range(len(required)):
            if required[i][1].value == 'number':
                required[i] = (required[i][0],float)
            elif required[i][1].value == 'string':
                required[i] = (required[i][0],str)
        
        return required

    @staticmethod
    def _get_optional_body_params(body):
        if body == None:
            return []
        
        body_properties = body.content[0].schema.properties
        required_properties = body.content[0].schema.required
            
        optional = [(bp.name, bp.schema.type) for bp in body_properties if bp.name not in required_properties]

        for i in range(len(optional)):
            if optional[i][1].value == 'number':
                optional[i] = (optional[i][0],float)
            elif optional[i][1].value == 'string':
                optional[i] = (optional[i][0],str)
        
        return optional

    @staticmethod
    def openAPI_yaml_spec_to_functool(path) -> FunctionTool:
        specification = parse(path)
        
        http_method = specification.paths[0].operations[0].method.value
        operationId = specification.paths[0].operations[0].operation_id

        security_schemas = None
        if 'ApiKeyAuth' in specification.security_schemas.keys():
            security_schemas = specification.security_schemas['ApiKeyAuth']

        body = specification.paths[0].operations[0].request_body

        tool_desc = specification.paths[0].description
        
        rqP = OpenAPIFunctionToolGenerator._get_required_query_params(specification.paths[0].operations[0])
        optP = OpenAPIFunctionToolGenerator._get_optional_query_params(specification.paths[0].operations[0])
        
        rqBodyParams = OpenAPIFunctionToolGenerator._get_required_body_params(body)
        optBodyParams = OpenAPIFunctionToolGenerator._get_optional_body_params(body)

        tool_func = OpenAPIFunctionToolGenerator._create_api_function(
                                path = specification.paths[0].url,
                                base_url = specification.servers[0].url,
                                func_name = operationId,
                                http_method = http_method,
                                required_query_params = rqP,
                                optional_query_params = optP,
                                required_body_params = rqBodyParams,
                                optional_body_params = optBodyParams,
                                apikey_security = security_schemas
                )

        return FunctionTool(tool_func, tool_desc, name=operationId)
    
    @staticmethod
    def openAPI_yaml_spec_to_func(path) -> Callable:
        specification = parse(path)

        http_method = specification.paths[0].operations[0].method.value
        operationId = specification.paths[0].operations[0].operation_id

        security_schemas = None
        if 'ApiKeyAuth' in specification.security_schemas.keys():
            security_schemas = specification.security_schemas['ApiKeyAuth']

        body = specification.paths[0].operations[0].request_body

        tool_desc = specification.paths[0].description
        
        rqP = OpenAPIFunctionToolGenerator._get_required_query_params(specification.paths[0].operations[0])
        optP = OpenAPIFunctionToolGenerator._get_optional_query_params(specification.paths[0].operations[0])
        
        rqBodyParams = OpenAPIFunctionToolGenerator._get_required_body_params(body)
        optBodyParams = OpenAPIFunctionToolGenerator._get_optional_body_params(body)

        tool_func = OpenAPIFunctionToolGenerator._create_api_function(
                                path = specification.paths[0].url,
                                base_url = specification.servers[0].url,
                                func_name = operationId,
                                http_method = http_method,
                                required_query_params = rqP,
                                optional_query_params = optP,
                                required_body_params = rqBodyParams,
                                optional_body_params = optBodyParams,
                                apikey_security = security_schemas
                )

        return tool_func

    @staticmethod
    def _create_api_function(
        func_name,
        base_url : str,
        path: str, 
        http_method: str, 
        apikey_security : Security = None,
        required_query_params: list = [], 
        optional_query_params: list = [],
        required_body_params: list = [], 
        optional_body_params: list = [],
        headers : Dict = {}
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
        headers = {}
        
        # Create a signature with all possible parameters
        parameters = (
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation = param_type) for param, param_type in required_query_params] +
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation = param_type) for param, param_type in required_body_params] +
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation= param_type,default=None) for param, param_type in optional_query_params] +
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation= param_type,default=None) for param, param_type in optional_body_params]
        )

        if apikey_security:
            # Retrieve API key for this service
            apikey = settings.WEATHER_API_KEY

        # Separate arguments into query parameters and request data
        query_params = [x[0] for x in OpenAPIFunctionToolGenerator._join_lists(required_query_params, optional_query_params)]
        body_params = [x[0] for x in OpenAPIFunctionToolGenerator._join_lists(required_body_params, optional_body_params)]
        print("QB PARAMS:", query_params, body_params)
        # Construct full URL
        full_url = urljoin(base_url, path)
        
        # The actual API call function to be returned
        def api_call_function(**kwargs):
            # Validate required parameters are present
            bound_arguments = inspect.Signature(parameters).bind(**kwargs)
            # applies default values to optional parameters
            # bound_arguments.apply_defaults()
            

            supplied_args = bound_arguments.arguments

            requestQueryParams = {}
            requestBodyParams = {}

            for key in supplied_args.keys():
                if key in query_params:
                   requestQueryParams[key] = supplied_args[key]

                elif key in body_params:
                    requestBodyParams[key] = supplied_args[key]
                   

            print("Bound_arguments: ", supplied_args)
            
            if apikey_security:
                if apikey_security.location == BaseLocation.QUERY:
                    # Retrive API KEY and set it as a default parameter
                    requestQueryParams[apikey_security.name] = apikey
                
                elif apikey_security.location == BaseLocation.HEADER:
                    # Retrieve api key and add it to headers
                    headers[apikey_security.name] = apikey
            
            # Determine HTTP method dynamically
            if http_method.lower() == 'get':
                try:
                    response = requests.get(full_url, params=requestQueryParams, headers = headers)
                    response.raise_for_status()  # Raise an exception for bad responses
                    return response.json()
                except requests.RequestException as e:
                    print(f"API Call Error: {e}")
                    raise

            elif http_method.lower() == "post":
                try:
                    response = requests.post(full_url, params=requestQueryParams, headers = headers, data=requestBodyParams)
                    response.raise_for_status()  # Raise an exception for bad responses
                    return response.json()
                except requests.RequestException as e:
                    print(f"API Call Error: {e}")
                    raise
        
        # Set function signature to help with tool use
        api_call_function.__signature__ = inspect.Signature(parameters)
        print("Signature: ", api_call_function.__signature__)
        return api_call_function

    def _join_lists(l1: list, l2 : list) -> list:
        if l1 == None and l2 == None:
            return []
        elif l2 == None:
            return l1
        elif l1 == None:
            return l2
        else:
            return l1 + l2
# Demonstration
if __name__ == "__main__":
        
    # Create the weather function with specific requirements
    get_weather_generated = OpenAPIFunctionToolGenerator.openAPI_yaml_spec_to_functool('weather_tool.yaml')
    
    createUser = OpenAPIFunctionToolGenerator.openAPI_yaml_spec_to_func('create_user_tool.yaml')
    
    response = createUser(name = "Leo", job = "Consultant", salary = 20000)
    print("response:\n",response)
