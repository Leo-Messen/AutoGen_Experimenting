import requests
import inspect
import pprint
from typing import Dict, Any, Callable
from urllib.parse import urljoin
from config import settings
from openapi_parser.enumeration import BaseLocation, DataType, ParameterLocation
from openapi_parser.specification import Security, SecurityType
from openapi_parser import parse

from requests.models import Request
from autogen_core.components.tools import FunctionTool

class OpenAPIFunctionToolGenerator:
    @staticmethod
    def _get_query_params(operation, required: bool):
        queryParams = operation.parameters
        params = [(qp.name, qp.schema.type) for qp in queryParams if qp.location == ParameterLocation.QUERY and qp.required == required]

        for i in range(len(params)):                
            match params[i][1]:
                case DataType.NUMBER:
                    params[i] = (params[i][0],float)
                case DataType.STRING:
                    params[i] = (params[i][0],str)
                case DataType.INTEGER:
                    params[i] = (params[i][0],int)
                case DataType.BOOLEAN:
                    params[i] = (params[i][0],bool)

        return params
    
    @staticmethod
    def _get_path_params(operation, required: bool):
        pathParams = operation.parameters
        params = [(pp.name, pp.schema.type) for pp in pathParams if pp.location == ParameterLocation.HEADER and pp.required == required]

        for i in range(len(params)):                
            match params[i][1]:
                case DataType.NUMBER:
                    params[i] = (params[i][0],float)
                case DataType.STRING:
                    params[i] = (params[i][0],str)
                case DataType.INTEGER:
                    params[i] = (params[i][0],int)
                case DataType.BOOLEAN:
                    params[i] = (params[i][0],bool)

        return params
    
    @staticmethod
    def _get_body_params(body, required: bool):
        if body == None:
            return []
        
        body_properties = body.content[0].schema.properties
        required_properties = body.content[0].schema.required

        if required == True:
            params = [(bp.name, bp.schema.type) for bp in body_properties if bp.name in required_properties]
        else:
            params = [(bp.name, bp.schema.type) for bp in body_properties if bp.name not in required_properties]

        for i in range(len(params)):                
            match params[i][1]:
                case DataType.NUMBER:
                    params[i] = (params[i][0],float)
                case DataType.STRING:
                    params[i] = (params[i][0],str)
                case DataType.INTEGER:
                    params[i] = (params[i][0],int)
                case DataType.BOOLEAN:
                    params[i] = (params[i][0],bool)

        return params

    @staticmethod
    def openAPI_yaml_spec_to_functools(path) -> FunctionTool:
        tools = []

        specification = parse(path)

        security_schemas = None
        if 'ApiKeyAuth' in specification.security_schemas.keys():
            security_schemas = specification.security_schemas['ApiKeyAuth']

        for path in specification.paths:
            for operation in path.operations:
                http_method = operation.method.value
                operationId = operation.operation_id

                body = operation.request_body

                tool_desc = operation.description
            
                rqQueryParams = OpenAPIFunctionToolGenerator._get_query_params(operation, True)
                optQueryParams = OpenAPIFunctionToolGenerator._get_query_params(operation, False)
                
                rqBodyParams = OpenAPIFunctionToolGenerator._get_body_params(body, True)
                optBodyParams = OpenAPIFunctionToolGenerator._get_body_params(body, False)

                rqPathParams = OpenAPIFunctionToolGenerator._get_path_params(operation, True)
                optPathParams = OpenAPIFunctionToolGenerator._get_path_params(operation, False)

                tool_func = OpenAPIFunctionToolGenerator._create_api_function(
                                        path = path.url,
                                        base_url = specification.servers[0].url,
                                        func_name = operationId,
                                        http_method = http_method,
                                        required_query_params = rqQueryParams,
                                        optional_query_params = optQueryParams,
                                        required_body_params = rqBodyParams,
                                        optional_body_params = optBodyParams,
                                        required_path_params = rqPathParams,
                                        optional_path_params = optPathParams,
                                        apikey_security = security_schemas
                        )

                tools.append(FunctionTool(tool_func, tool_desc, name=operationId))

        return tools

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

            # Should error if it can't retrieve the API Key

        # Separate arguments into query parameters and request data
        query_params = [x[0] for x in OpenAPIFunctionToolGenerator._join_lists(required_query_params, optional_query_params)]
        body_params = [x[0] for x in OpenAPIFunctionToolGenerator._join_lists(required_body_params, optional_body_params)]
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
    # weather_tools = OpenAPIFunctionToolGenerator.openAPI_yaml_spec_to_functools('weather_tool.yaml')
    
    user_tools = OpenAPIFunctionToolGenerator.openAPI_yaml_spec_to_functools('create_user_tool.yaml')
    
    print([(wt.name, wt.description, inspect.signature(wt._func)) for wt in user_tools])
    print(user_tools)