from openapi_parser import parse, enumeration
import pprint
import inspect
import types
from OpenAPIFunctionGenerator import OpenAPIFunctionGenerator
from config import settings


def get_required_params(operation):
    queryParams = operation.parameters
    requiredParams = [(qp.name, qp.schema.type) for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY and qp.required == True]

    for i in range(len(requiredParams)):
        if requiredParams[i][1].value == 'number':
            requiredParams[i] = (requiredParams[i][0],float)
        elif requiredParams[i][1].value == 'string':
            requiredParams[i] = (requiredParams[i][0],str)
    
    return requiredParams


def get_optional_params(operation):
    queryParams = operation.parameters
    optionalParams = [(qp.name, qp.schema.type) for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY and qp.required == False]

    for i in range(len(optionalParams)):
        if optionalParams[i][1].value == 'number':
            optionalParams[i] = (optionalParams[i][0],float)
        elif optionalParams[i][1].value == 'string':
            optionalParams[i] = (optionalParams[i][0],str)
    
    return optionalParams

specification = parse('tools.yaml')

# pprint.pp(specification)

url = specification.servers[0].url + specification.paths[0].url
operation = specification.paths[0].operations[0].method
queryParams = specification.paths[0].operations[0].parameters
queryParamNames = [qp.name for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY]
queryParamTypes = [qp.schema.type for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY]
operationId = specification.paths[0].operations[0].operation_id

requiredParams = [qp.name for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY and qp.required == True] 
optionalParams = [qp.name for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY and qp.required == False] 

security_schemas = specification.security_schemas['ApiKeyAuth']
# print(url, operation.value, queryParamNames, operationId, security_schemas, sep='\n')

fg = OpenAPIFunctionGenerator(specification.servers[0].url)
rqP = get_required_params(specification.paths[0].operations[0])
# print('rqp', rqP)
get_weather_dynamic = fg.create_api_function(
                        path=specification.paths[0].url,
                        func_name=operationId,
                        http_method=operation.value,
                        required_params=rqP,
                        optional_params=get_optional_params(specification.paths[0].operations[0]),
                        apikey_security = security_schemas
        )
# print(inspect.signature(get_weather_dynamic))

# Now you can call it like this
# weather_data = get_weather_dynamic(
#     lat=44.52, 
#     lon=9.65, 
#     units = "metric"
#     )

# print(inspect.signature(get_weather_dynamic))
# print(weather_data)

