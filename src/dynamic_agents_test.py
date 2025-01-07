from dataclasses import dataclass
import asyncio

from autogen_core import AgentId, BaseAgent, MessageContext, SingleThreadedAgentRuntime

from AgentGenerator import AgentGenerator
from autogen_agentchat.ui import Console


@dataclass
class MyMessageType:
    content: str


class MyAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("MyAgent")

    async def on_message_impl(self, message: MyMessageType, ctx: MessageContext) -> None:
        print(f"Received message: {message.content}")  # type: ignore


async def run():
    # runtime = SingleThreadedAgentRuntime()
    # await MyAgent.register(runtime, "my_agent", lambda: MyAgent())
    # agent_id = AgentId("my_agent", "default")
    # runtime.start()  # Start processing messages in the background.
    # await runtime.send_message(MyMessageType("Hello, World!"), agent_id)
    # await runtime.stop()  # Stop processing messages in the background.
    
    agent_team = AgentGenerator.generate_agents('agent_team_specs/agent_spec2.yaml')

    # stream = await agent_team.run(task="Hello from Doncaster!")

    # print(stream)
    
    stream = agent_team.run_stream(task="Hello from Doncaster!")

    async for m in stream:
        print(m)

if __name__ == "__main__":
    asyncio.run(run())