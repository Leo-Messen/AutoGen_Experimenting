from openapi_parser import parse, enumeration
import pprint
import inspect
import types
from config import settings


def get_required_params(body):
    body_properties = body.content[0].schema.properties
    required_properties = body.content[0].schema.required
        
    required = [(bp.name, bp.schema.type) for bp in body_properties if bp.name in required_properties]

    for i in range(len(required)):
        if required[i][1].value == 'number':
            required[i] = (required[i][0],float)
        elif required[i][1].value == 'string':
            required[i] = (required[i][0],str)
    
    return required


def get_optional_params(body):
    body_properties = body.content[0].schema.properties
    required_properties = body.content[0].schema.required
        
    optional = [(bp.name, bp.schema.type) for bp in body_properties if bp.name not in required_properties]

    for i in range(len(optional)):
        if optional[i][1].value == 'number':
            optional[i] = (optional[i][0],float)
        elif optional[i][1].value == 'string':
            optional[i] = (optional[i][0],str)
    
    return optional

specification = parse('tool_specs/create_user_tool.yaml')

pprint.pp(specification)

url = specification.servers[0].url + specification.paths[0].url
operation = specification.paths[0].operations[0].method
queryParams = specification.paths[0].operations[0].parameters
queryParamNames = [qp.name for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY]
queryParamTypes = [qp.schema.type for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY]
operationId = specification.paths[0].operations[0].operation_id

requiredParams = [qp.name for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY and qp.required == True] 
optionalParams = [qp.name for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY and qp.required == False] 

# body = specification.paths[0].operations[0].request_body
# body_properties = body.content[0].schema.properties
# requiredBody = [p.name for p in body_properties if p.name in body.content[0].schema.required] 

description = specification.paths[0].description
