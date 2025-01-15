import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config import settings
from autogen_agentchat.teams import RoundRobinGroupChat, Swarm, SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination

from FunctionToolGenerator import FunctionToolGenerator


class AgentGenerator:
    @staticmethod
    def generate_agents(path: str):

        # Define a model
        model = OpenAIChatCompletionClient(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=settings.MODEL_TEMPERATURE
            )
    
        with open(path) as file:
            team_spec = yaml.load(file, Loader=yaml.Loader)

            agents = []

            for agent_spec in team_spec['team']['agents']:
                agent_tools = []

                if 'tools' in agent_spec.keys():
                    for tool_spec in agent_spec['tools'].keys():
                        tool_names = agent_spec['tools'][tool_spec]

                        if tool_names[0] == 'USE_ALL_TOOLS':
                            agent_tools += AgentGenerator._get_tools(tool_spec)
                        else:
                            agent_tools += AgentGenerator._get_tools(tool_spec, tool_names)
                # TODO : For now it's just using an agent chat agent but in the future it should use our custom core agents
                # with the correct message handling behaviour           
                agent = AssistantAgent(
                    agent_spec['name'],
                    system_message=agent_spec['system_message'],
                    model_client=model,
                    tools=agent_tools
                )

                agents.append(agent)

        # TODO: Remove this into its own function with Custom Core agents integration
        termmination_condition = TextMentionTermination("TERMINATE") 
        if 'max_messages' in team_spec['team'].keys():
            max_messages = team_spec['team']['max_messages']
            termmination_condition = termmination_condition | MaxMessageTermination(max_messages=max_messages)

        team_type = team_spec['team']['type']
        if team_type == 'RoundRobinGroupChat':
            agent_team = RoundRobinGroupChat(agents, termination_condition = termmination_condition)
        
        elif team_type == 'SelectorGroupChat':
            agent_team = SelectorGroupChat(agents, model_client=model, termination_condition = termmination_condition)
            
        return agent_team
    
    @staticmethod
    def _get_tools(tool_spec, tool_names = None):
        if tool_spec == 'weather_tools':
           return FunctionToolGenerator.openAPI_yaml_spec_to_functools('tool_specs/weather_tool.yaml', tool_names)
        elif tool_spec == 'create_user_tool':
           return FunctionToolGenerator.openAPI_yaml_spec_to_functools('tool_specs/create_user_tool.yaml', tool_names)

# Demonstration
if __name__ == "__main__":
        
    team = AgentGenerator.generate_agents('agent_team_specs/agent_spec2.yaml')