import requests
import inspect
from typing import Dict, Any, Callable
from openapi_parser.enumeration import BaseLocation, DataType, ParameterLocation
from openapi_parser.specification import Security, SecurityType, OAuthFlowType
from openapi_parser import parse

from requests.models import Request
from autogen_core.tools import FunctionTool

import typing

class FunctionToolGenerator:
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
    def _get_path_params(operation):
        pathParams = operation.parameters
        params = [(pp.name, pp.schema.type) for pp in pathParams if pp.location == ParameterLocation.PATH]

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
    def _get_header_params(operation, required: bool):
        headerParams = operation.parameters
        params = [(hp.name, hp.schema.type) for hp in headerParams if hp.location == ParameterLocation.HEADER and hp.required == required]

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
    def openAPI_yaml_spec_to_functools(path, tool_names = None) -> FunctionTool:
        functools = []

        specification = parse(path)

        security_schemas = specification.security_schemas
        
        global_security = []
        if len(specification.security) > 0:
            # Just assuming only one security type for now
            for key in specification.security[0].keys():
                if key in security_schemas.keys():
                    global_security.append(security_schemas[key])

        for path in specification.paths:
            for operation in path.operations:
                operationId = operation.operation_id
                if tool_names != None and operationId not in tool_names:
                    continue
                
                http_method = operation.method.value

                body = operation.request_body

                tool_desc = operation.description
            
                rqQueryParams = FunctionToolGenerator._get_query_params(operation, True)
                optQueryParams = FunctionToolGenerator._get_query_params(operation, False)
                
                rqBodyParams = FunctionToolGenerator._get_body_params(body, True)
                optBodyParams = FunctionToolGenerator._get_body_params(body, False)

                rqHeaderParams = FunctionToolGenerator._get_header_params(operation, True)
                optHeaderParams = FunctionToolGenerator._get_header_params(operation, False)

                pathParams = FunctionToolGenerator._get_path_params(operation)

                # check for operation level security
                security = []
                if len(operation.security) > 0:
                    for key in operation.security[0].keys():
                        if key in security_schemas.keys():
                            security.append(security_schemas[key])
                # if no operation level security use global security
                else:
                    security = global_security

                tool_func = FunctionToolGenerator._create_api_function(
                                        path = path.url,
                                        base_url = specification.servers[0].url,
                                        func_name = operationId,
                                        http_method = http_method,
                                        required_query_params = rqQueryParams,
                                        optional_query_params = optQueryParams,
                                        path_params = pathParams,
                                        required_body_params = rqBodyParams,
                                        optional_body_params = optBodyParams,
                                        required_header_params=rqHeaderParams,
                                        optional_header_params=optHeaderParams,
                                        security_schemas = security
                        )

                functools.append(FunctionTool(tool_func, tool_desc, name=operationId))

        return functools

    @staticmethod
    def _create_api_function(
        func_name,
        base_url : str,
        path: str, 
        http_method: str, 
        security_schemas : list[Security] = [],
        required_query_params: list = [], 
        optional_query_params: list = [],
        path_params: list = [], 
        required_body_params: list = [], 
        optional_body_params: list = [],
        required_header_params: list = [], 
        optional_header_params: list = []
        
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
        
        # Create a signature with all possible parameters
        parameters = (
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation = param_type) for param, param_type in required_query_params] +
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation = param_type) for param, param_type in path_params] +
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation = param_type) for param, param_type in required_body_params] +
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation = param_type) for param, param_type in required_header_params] +
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation= param_type,default=None) for param, param_type in optional_query_params] +
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation= param_type,default=None) for param, param_type in optional_body_params] +
            [inspect.Parameter(param, inspect.Parameter.KEYWORD_ONLY, annotation= param_type,default=None) for param, param_type in optional_header_params]
        )
        
        apikey_security = None
        token_security = None

        for security_object in security_schemas:
            if security_object.type == SecurityType.API_KEY:
                # Retrieve API key for this service
                apikey_security = security_object
                apikey = "dummy key"

                # Should error if it can't retrieve the API Key
            if security_object.type == SecurityType.OAUTH2 and OAuthFlowType.CLIENT_CREDENTIALS in security_object.flows.keys():
                token_security = security_object

                # Get client credentials from somewhere
                client_id = "dummy id"
                client_secret = "dummy secret"

                # Trigger some code to get auth token using client credentials flow
                token = "dummy token" 
                
        # Separate arguments into query parameters and request data
        query_params = [x[0] for x in FunctionToolGenerator._join_lists(required_query_params, optional_query_params)]
        body_params = [x[0] for x in FunctionToolGenerator._join_lists(required_body_params, optional_body_params)]
        header_params = [x[0] for x in FunctionToolGenerator._join_lists(required_header_params, optional_header_params)]

        # The actual API call function to be returned
        def api_call_function(**kwargs):
            # Validate required parameters are present
            bound_arguments = inspect.Signature(parameters).bind(**kwargs)
            # applies default values to optional parameters
            # bound_arguments.apply_defaults()
            

            supplied_args = bound_arguments.arguments

            requestQueryParams = {}
            requestBodyParams = {}
            requestHeaderParams = {}

            for key in supplied_args.keys():
                if key in query_params:
                   requestQueryParams[key] = supplied_args[key]

                elif key in body_params:
                    requestBodyParams[key] = supplied_args[key]
                
                elif key in header_params:
                    requestHeaderParams[key] = supplied_args[key]
            
            # Construct full URL
            full_url = base_url.rstrip("/") + path

            # Add path params
            for param, _ in path_params:
                # Replace path param in url with value
                full_url = full_url.replace("{"+param+"}", str(supplied_args[param])) 

            if apikey_security:
                if apikey_security.location == BaseLocation.QUERY:
                    # Retrive API KEY and set it as a default parameter
                    requestQueryParams[apikey_security.name] = apikey
                
                elif apikey_security.location == BaseLocation.HEADER:
                    # Retrieve api key and add it to headers
                    requestHeaderParams[apikey_security.name] = apikey
            
            if token_security:
                requestHeaderParams['Authorization'] = "Bearer " + token

            # Determine HTTP method dynamically
            if http_method.lower() == 'get':
                try:
                    response = requests.get(full_url, params=requestQueryParams, headers = requestHeaderParams)
                    response.raise_for_status()  # Raise an exception for bad responses
                    return response.json()
                except requests.RequestException as e:
                    print(f"API Call Error: {e}")
                    raise

            elif http_method.lower() == "post":
                try:
                    response = requests.post(full_url, params=requestQueryParams, headers = requestHeaderParams, data=requestBodyParams)
                    response.raise_for_status()  # Raise an exception for bad responses
                    return response.json()
                except requests.RequestException as e:
                    print(f"API Call Error: {e}")
                    raise
        
        # Set function signature to help with tool use
        api_call_function.__signature__ = inspect.Signature(parameters)

        annotations = {}
        for var in parameters:
            annotations[var.name] = var.annotation
        api_call_function.__annotations__ = annotations

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