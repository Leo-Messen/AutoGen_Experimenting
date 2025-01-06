import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config import settings
from autogen_agentchat.teams import RoundRobinGroupChat, Swarm
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination

from OpenAPIFunctionToolGenerator import OpenAPIFunctionToolGenerator


class AgentGenerator:
    @staticmethod
    def generate_agents(path: str) -> list:

        # Define a model
        model = OpenAIChatCompletionClient(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=settings.MODEL_TEMPERATURE
            )
    
        with open(path) as config_file_str:
            team_spec = yaml.load(config_file_str, Loader=yaml.Loader)
            print(team_spec)
            agents = []
            for agent in team_spec['team']['agents']:
                agent_tools = []

                if 'tools' in agent.keys():
                    for tool in agent['tools']:
                        agent_tools += AgentGenerator._get_tools(tool)
                agents.append(AssistantAgent(
                    agent['name'],
                    system_message=agent['system_message'],
                    model_client=model,
                    tools=agent_tools
                ))
        
        termmination_condition = TextMentionTermination("TERMINATE") 
        if 'max_messages' in team_spec['team'].keys():
            max_messages = team_spec['team']['max_messages']
            termmination_condition = termmination_condition | MaxMessageTermination(max_messages=max_messages)

        team_type = team_spec['team']['type']
        if team_type == 'RoundRobinGroupChat':
            agent_team = RoundRobinGroupChat(agents, termination_condition = termmination_condition)
        

        return agent_team
    
    @staticmethod
    def _get_tools(tool_name):
        if tool_name == 'weather_tools':
           return OpenAPIFunctionToolGenerator.openAPI_yaml_spec_to_functools('tool_specs/weather_tool.yaml')
        elif tool_name == 'create_user_tool':
           return OpenAPIFunctionToolGenerator.openAPI_yaml_spec_to_functools('tool_specs/create_user_tool.yaml')

