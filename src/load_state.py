
import asyncio
import aioconsole
from AgentGenerator import AgentGenerator
from autogen_agentchat.ui import Console
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config import settings
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination, HandoffTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.base import Handoff
from autogen_core.tools import FunctionTool
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage, ToolCallExecutionEvent, ToolCallRequestEvent, ToolCallSummaryMessage
import json
import pprint

async def run():

    model = OpenAIChatCompletionClient(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=settings.MODEL_TEMPERATURE
            )
    
    def book_holiday(names:list[str], hotel:str, duration:int):
        return f"Holiday booked: {{ names : {names}, hotel: {hotel}, duration: {duration} days }}"
    # Create a lazy assistant agent that always hands off to the user.
    holiday_booking_agent = AssistantAgent(
        "holiday_booking_agent",
        model_client=model,
        handoffs=[Handoff(target="user", message="Transferring to user and waiting for input.")],
        system_message="""You are a specialized holiday booking agent responsible for processing vacation bookings. To successfully process a booking, you need:

Full list of all travelers' names
Hotel name
Duration of stay in days

Your workflow:

Once you have all required information, use the book_holiday tool to make the booking
If any required information is missing, end your message with "transfer: user"
After making a booking, provide confirmation to the kiosk agent
Keep responses professional and focused on the booking process""",

        tools = [FunctionTool(book_holiday, description="Book a holiday")]
    )
    def send_email(email:str, subject:str, body:str):
        return f"Email Sent!\n {{email : {email}, subject: {subject}, body: {body} }}"
    email_agent = AssistantAgent(
        "email_agent",
        model_client=model,
        handoffs=[Handoff(target="user", message="Transfer to user.")],
        system_message="""You are a specialized email agent responsible for helping users send emails. To successfully process an email request, you need:

Email address of the recipient
Subject line
Email body content

Your workflow:

Once you have all required information, use the book_email tool to send the email
If any required information is missing, end your message with "transfer: user"
After sending an email, provide confirmation to the kiosk agent
Keep responses clear and focused on the email task""",
        tools=[FunctionTool(send_email, description="Send email")]
    )

    kiosk_agent = AssistantAgent(
        "kiosk_agent",
        model_client=model,
        handoffs=[Handoff(target="user", message="Transfer to user.")],
        system_message="""You are a friendly and helpful kiosk agent acting as the first point of contact for users. Your role is to:

Greet users warmly and engage in natural conversation to understand their needs
Direct users to the appropriate specialized agent (email or holiday booking) based on their requirements
Keep track of and report on actions taken by other agents in the team
Handle conversation flow using these rules:

End messages with "transfer: user" when you need more information
End messages with "TERMINATE" when the user indicates they want to end the conversation
Report back any actions from other agents by saying "Action Report: [details of action]"



Remember to maintain a welcoming, professional tone while efficiently directing users to the right service."""
    )

    handoff_termination = HandoffTermination(target="user")
    text_termination = TextMentionTermination("TERMINATE")
    combined_termination =  text_termination | handoff_termination

    # user = UserProxyAgent("user", input_func=input)

    agent_team = SelectorGroupChat([kiosk_agent, email_agent, holiday_booking_agent],
                                    model, 
                                    termination_condition=combined_termination,
                                    allow_repeated_speaker = True)
    
    with open("state.json", "r") as f:
        team_state = json.load(f)

        await agent_team.load_state(team_state)

    stream = agent_team.run_stream(task = "I don't need anything else thank you!")

    result : TaskResult = None
    final_message: TextMessage = None

    async for message in stream:
        if isinstance(message, TaskResult):
            print("\n !!!!! Stop Reason !!!!! \n", message.stop_reason)
            result = message
        else:
            print(message)

    print("\n !!!! TaskResult !!!!", result)

    for message in reversed(result.messages):
        if message.type == 'TextMessage':
            final_message = message
            break

    print("\n\n !!!!! Final Message !!!!", final_message)
    # After termination of stream
    async with asyncio.Lock():
        state = await agent_team.save_state()
        with open("state.json", "w") as f:
            json.dump(state, f)


if __name__ == "__main__":
    asyncio.run(run())
