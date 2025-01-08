import yaml

with open('agent_team_specs/agent_spec.yaml') as file:
            team_spec = yaml.load(file, Loader=yaml.Loader)
            print(team_spec, end='\n\n')
            agents = []
            for agent in team_spec['team']['agents']:
                agent_tools = []
                print(agent['tools'],end='\n\n')

                if 'tools' in agent.keys():
                    for tool_spec in agent['tools'].keys():
                        tool_names = agent['tools'][tool_spec]
                        print(tool_spec, tool_names,end='\n\n')


