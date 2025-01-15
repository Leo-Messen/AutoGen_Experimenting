
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
import json

async def run():

    model = OpenAIChatCompletionClient(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=settings.MODEL_TEMPERATURE
            )
    # Create a lazy assistant agent that always hands off to the user.
    lazy_agent = AssistantAgent(
        "lazy_assistant",
        model_client=model,
        handoffs=[Handoff(target="user", message="Transfer to user.")],
        system_message="Always transfer to user when you don't know the answer. Respond 'TERMINATE' when task is complete.",
    )

    lazy_agent2 = AssistantAgent(
        "lazy_manager",
        model_client=model,
        handoffs=[Handoff(target="lazy_agent", message="Transfer to lazy_agent.")],
        system_message="Always transfer to lazy_assistant when you don't know the answer. Respond 'TERMINATE' when task is complete.",
    )

    # Define a termination condition that checks for handoff message targetting helper and text "TERMINATE".
    handoff_termination = HandoffTermination(target="user")
    text_termination = TextMentionTermination("TERMINATE")
    combined_termination = handoff_termination | text_termination

    # Create a single-agent team.
    # lazy_agent_team = RoundRobinGroupChat([lazy_agent], termination_condition=combined_termination)
    lazy_agent_team = SelectorGroupChat([lazy_agent, lazy_agent2],model, termination_condition=combined_termination)

    # Run the team and stream to the console.
    task = "Can I ask the manager what is the weather in New York?"

    await Console(lazy_agent_team.run_stream(task=task))
    
    await Console(lazy_agent_team.run_stream(task=f"The weather in New York is bad."))

async def run2():
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
        handoffs=[Handoff(target="user", message="Transfer to user.")],
        system_message="""
        Your job is to book holidays for users based on their input.
        Always transfer to user when you don't have enough information. 
        Add 'TERMINATE' to the end of your message when you are able to book a holiday.
        You need to know who is going, to what hotel and for how long in order to book a holiday.""",
        tools = [FunctionTool(book_holiday, description="Book a holiday")]
    )
    def send_email(email:str, subject:str, body:str):
        return f"Email Sent!\n {{email : {email}, subject: {subject}, body: {body} }}"
    email_agent = AssistantAgent(
        "email_agent",
        model_client=model,
        handoffs=[Handoff(target="user", message="Transfer to user.")],
        system_message="""
        Your job is to send emails based on user input.
        Always transfer to user when you don't have enough information. 
        Add 'TERMINATE' to the end your message when you are able to sucessfully write an email.
        You need to know an email address, subject and body to generate an email.""",
        tools=[FunctionTool(send_email, description="Send email")]
    )

    kiosk_agent = AssistantAgent(
        "kiosk_agent",
        model_client=model,
        handoffs=[Handoff(target="user", message="Transfer to user.")],
        system_message="""
        Your job is to have a friendly and professional chat with the user and find out if your team members can be of assistance booking a holiday or sending an email.
        You should handoff to 'user' when you ask them a question."""
    )

    handoff_termination = HandoffTermination(target="user")
    text_termination = TextMentionTermination("TERMINATE")
    combined_termination =  text_termination | handoff_termination

    # user = UserProxyAgent("user", input_func=input)

    agent_team = SelectorGroupChat([kiosk_agent, email_agent, holiday_booking_agent],
                                    model, 
                                    termination_condition=combined_termination,
                                    allow_repeated_speaker = True)

    # Run the team and stream to the console.
    task = "Hello! Can you please help me with something"

    while True:
        # Run the conversation and stream to the console.
        stream = agent_team.run_stream(task=task)        

        await Console(stream)

        # After termination of stream
        state = await agent_team.save_state()
        print(state)
        # Get the user response.
        task = await aioconsole.ainput("Enter your feedback (type 'exit' to leave): ")

        if task.lower().strip() == "exit":
            break

async def run3():
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
        handoffs=[Handoff(target="user", message="Transfer to user.")],
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
End messages with "terminate" when the user indicates they want to end the conversation
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

    # Run the team and stream to the console.
    task = "Hello! How are you today?"

    # Run the conversation and stream to the console.
    stream = agent_team.run_stream(task=task)        

    await Console(stream)

    # After termination of stream
    state = await agent_team.save_state()
    with open("state.json", "w") as f:
        json.dump(state, f)
    
if __name__ == "__main__":
    # asyncio.run(run())
    asyncio.run(run3())

