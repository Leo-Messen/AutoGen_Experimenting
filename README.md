# AutoGen Dynamic Tooling & Agents

## Dynamic Tooling 

`OpenAPIFunctionToolGenerator` contains code to generate AutoGen Function Tools from OpenAPI YAML specifications. You can find more information on OpenAPI here https://swagger.io/docs/specification/v3_0/basic-structure/

The method `openAPI_yaml_spec_to_functools(path, tool_names = None)` takes the path to your YAML file and the names of the tools (more on this next) to extract from that specification.

Some key values that must be defined within the specification are:
- `operationId` : maps to the name of the function tool
- `description` : maps to the description of the function tool

You must also make sure to set the correct base url, path, http method, and security schemas. Any parameters defined will be mapped to the arguments of the dynamically created function associated with the function tools generated.

## Dynamic Agents 

```
team:
  type: RoundRobinGroupChat
  max_messages: 20
  agents:
    - name: weather_agent
      description: An agent that has access to tools that can get the current weather conditions in a specific location.
      system_message: You have access to tools to retrieve weather data.
        Find the weather in the city specified in the context and report it.
        Use the correct units of measurement for temperature in the city specified.
      tools:
        weather_tools:
          - get_weather
          - get_city_coordinates
        city_tools:
          - travel_guide_tool

    - name: create_user_agent
      description: An agent that has access to tools to create a new user
      system_message: You have access to tools to create a new user.
        Your job is to retrieve all the required information from the user to create a new user using the provided tools.
      tools:
        create_user_tools:
          - USE_ALL_TOOLS
```

Agents can be dynamically configured using a YAML file. When defining tools for agents, the key (e.g. weather_tools) represents a specification of many tools, and the list under that key (e.g. get_weather, get_city_coordinates) represent the names of the tools that are used from that spec. A special USE_ALL_TOOLS item can be used which indicates that all of the tools in the defined specification are avaialable to the agent.
