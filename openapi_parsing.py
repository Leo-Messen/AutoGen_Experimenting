from openapi_parser import parse, enumeration
import pprint
import inspect
import types

specification = parse('tools.yaml')

pprint.pp(specification)

url = specification.servers[0].url + specification.paths[0].url
operation = specification.paths[0].operations[0].method
queryParams = specification.paths[0].operations[0].parameters
queryParamNames = [qp.name for qp in queryParams if qp.location == enumeration.ParameterLocation.QUERY]
operationId = specification.paths[0].operations[0].operation_id
print(url, operation, queryParamNames, operationId, sep='\n')

