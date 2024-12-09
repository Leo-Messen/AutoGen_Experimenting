from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.task import Console, TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat, Swarm
from autogen_ext.models import OpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool
from autogen_core.base import CancellationToken

import asyncio
import requests

from config import settings
from OpenAPIFunctionToolGenerator import OpenAPIFunctionToolGenerator

# Define a tool
async def get_weather(lat: float, lon: float) -> str:
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={settings.WEATHER_API_KEY}"
    response = requests.get(url)
    return response.json()

async def get_latitude_and_longitude_from_city(city: str):
    url = f'http://api.openweathermap.org/geo/1.0/direct?q={city}&limit={1}&appid={settings.WEATHER_API_KEY}'

    response = requests.get(url)
    response = response.json()[0]
    
    return {"lat": response["lat"], "lon": response["lon"]}

async def get_weather_from_city(city: str):
    url = f'http://api.openweathermap.org/geo/1.0/direct?q={city}&limit={1}&appid={settings.WEATHER_API_KEY}'

    response = requests.get(url)
    response = response.json()[0]
    
    lat = response["lat"]
    lon = response["lon"]

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={settings.WEATHER_API_KEY}"
    response = requests.get(url)
    return response.json()

async def call_api():
    return "Ok"

# Print the result.
async def weather_main() -> None:
    # Create a function tool.
    get_latitude_and_longitude_from_city_tool = FunctionTool(get_latitude_and_longitude_from_city, 
                                                            description="Receives a city name, and gets the latitude and longitude coordinates of that city.")
    get_weather_tool = FunctionTool(get_weather,
                                description="Receives latitude and longitude coordinates, and gets the current weather at that location.")
    
    get_weather_dynamic_tool = OpenAPIFunctionToolGenerator.openAPI_yaml_spec_to_functool('tools.yaml')
    
    get_weather_from_city_tool = FunctionTool(get_weather_from_city,
                                description="Receives a city name, and gets the current weather at that location.")

    # Define a model
    model = OpenAIChatCompletionClient(
            model="gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY,
            temperature=settings.MODEL_TEMPERATURE
        )
    
    # Define an agent
    weather_agent = AssistantAgent(
        name="weather_agent",
        model_client=model,
        tools=[get_weather_tool, get_latitude_and_longitude_from_city_tool],
        description="An agent that has access to tools that can get the current weather conditions in a specific location.",
        system_message="""You have access to tools to retrieve weather data.
        Find the weather in the city specified in the context and report it.
        Always handoff back to travel_agent when you have reported the weather.""",
        handoffs=["travel_agent"]
    )

    guide_agent = AssistantAgent(
        "guide_agent",
        model_client=model,
        description="A travel guide that can suggest things to do or places to visit, in a specific city or closely neighbouring areas, based on the user's prompt.",
        system_message=
        """You are a travel guide.
        Give between 4 and 10 ideas for places to visit, or things to do, in/around a city given by the user.
        Always handoff back to travel_agent after you have written your ideas.""",
        handoffs=["travel_agent"]
    )

    travel_agent = AssistantAgent(
        "travel_agent",
        model_client=model,
        description="A helpful assistant that can summarize interesting places to visit and the weather conditions at a specific travel destination.",
        system_message=
        """You are a helpful assistant that gathers information about what things to do, or places to visit, in a city given by the user.
        Gather information about the specified city by handing off to specialized agents:
        - weather_agent: for finding out the live weather in the city
        - guide_agent: for finding out what places you can visit in or around a city
        Do NOT use any of your own knowledge. Your job is purely to sumnmarize knowledge gained for other agents.
        When reporting on the weather, adopt a conversational tone. Don't go into too much detail. Focus on the aspects of the weather people care about like temperature, general conditions, how windy it is etc.
        Take into account the weather conditions when selecting information from the guide_agent. Omit guide_agents suggestions where the weather isn't suitable.
        Only handoff to one agent at a time.
        Use TERMINATE at the end of your message when you have fulfilled your task.""",
        handoffs=["weather_agent", "guide_agent"]
    )

    solo_weather_agent = AssistantAgent(
        name="weather_agent",
        model_client=model,
        tools=[get_weather_dynamic_tool, get_latitude_and_longitude_from_city_tool],
        description="An agent that has access to tools that can get the current weather conditions in a specific location.",
        system_message="""You have access to tools to retrieve weather data.
        Find the weather in the city specified in the context and report it.
        Use the correct units of measurement for temperature in the city specified.
        Use TERMINATE at the end of your message when you have fulfilled your task.""",
    )

    # Define termination condition
    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(max_messages=50)

    # Define a team
    # agent_team = Swarm([travel_agent, guide_agent, weather_agent], termination_condition=termination)
    agent_team = RoundRobinGroupChat([solo_weather_agent], termination_condition=termination)

    # Run the team and stream messages to the console
    # stream = agent_team.run_stream(task="I'm visiting London today and want to do some shopping and sightseeing. Do you have any suggestions for me?")
    stream = agent_team.run_stream(task="What's the weather like in Sheffield today?")
    await Console(stream)


# NOTE: if running this inside a Python script you'll need to use asyncio.run(main()).
asyncio.run(weather_main())