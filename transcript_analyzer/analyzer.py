from typing import TypedDict, List, Dict, Any
import re

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.func import entrypoint, task

from langgraph_supervisor import create_supervisor

class ConversationState(TypedDict):
    transcript: str
    messages: List[Dict[str, Any]]
    current_prompt: str
    analysis: Dict[str, Any]
    improved_prompt: str
    active_agent: str

class TranscriptAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.2,
            google_api_key=api_key,
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )
        self.app = self._build_graph()
        
    def _preprocess_transcript_func(self, state):
        """Preprocess the transcript into a structured format"""
        transcript = state["transcript"]
        
        # Parse transcript into structured conversation
        structured_conversation = self._parse_transcript(transcript)
        
        # Format the structured conversation for analysis
        formatted_transcript = self._format_conversation(structured_conversation)
        
        messages = [
            {
                "role": "user",
                "content": f"Please analyze this conversation transcript and help improve the system prompt:\n\n{formatted_transcript}\n\nCurrent system prompt:\n\n{state['current_prompt']}"
            }
        ]
        
        return {
            **state,
            "messages": messages,
            "analysis": {},
            "improved_prompt": "",
            "active_agent": "analysis_supervisor"
        }
    
    def _parse_transcript(self, transcript):
        """Parse the transcript format where lines alternate between USER and AGENT"""
        conversation = []
        current_speaker = None
        current_message = ""
        
        lines = transcript.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line indicates a speaker change
            if line.startswith("USER:"):
                # Save previous message if exists
                if current_speaker and current_message:
                    conversation.append({"role": current_speaker, "text": current_message.strip()})
                
                # Start new user message
                current_speaker = "user"
                current_message = line[6:].strip()
            elif line.startswith("AGENT:"):
                # Save previous message if exists
                if current_speaker and current_message:
                    conversation.append({"role": current_speaker, "text": current_message.strip()})
                
                # Start new agent message
                current_speaker = "agent"
                current_message = line[7:].strip()
            else:
                # Continue current message
                if current_speaker:
                    current_message += " " + line
        
        # Add the last message
        if current_speaker and current_message:
            conversation.append({"role": current_speaker, "text": current_message.strip()})
            
        return conversation
    
    def _format_conversation(self, structured_conversation):
        """Format the structured conversation for better analysis"""
        formatted = ""
        for entry in structured_conversation:
            speaker = "USER" if entry["role"] == "user" else "AGENT"
            formatted += f"{speaker}: {entry['text']}\n\n"
        return formatted
    
    def _postprocess_results_func(self, state):
        """Extract improved prompt and analysis from the completed state"""
        # Extract improved prompt if not already set
        if not state.get("improved_prompt"):
            for message in reversed(state["messages"]):
                if message["role"] == "assistant":
                    content = message["content"].lower()
                    if "improved prompt" in content or "system prompt" in content:
                        # Extract the prompt from code blocks if present
                        if "```" in message["content"]:
                            parts = message["content"].split("```")
                            if len(parts) >= 3:
                                state["improved_prompt"] = parts[1].strip()
                            else:
                                # Extract text between lines that look like headers and footers
                                matches = re.findall(r"(?:improved prompt:?|system prompt:?|suggested prompt:?)(.*?)(?:\n\n|$)", 
                                                    message["content"], re.DOTALL | re.IGNORECASE)
                                if matches:
                                    state["improved_prompt"] = matches[0].strip()
                                else:
                                    state["improved_prompt"] = message["content"]
                        else:
                            # Extract text after "Improved Prompt:" if present
                            matches = re.findall(r"(?:improved prompt:?|system prompt:?|suggested prompt:?)(.*?)(?:\n\n|$)", 
                                               message["content"], re.DOTALL | re.IGNORECASE)
                            if matches:
                                state["improved_prompt"] = matches[0].strip()
                            else:
                                state["improved_prompt"] = message["content"]
                        break
        
        # Extract analysis insights
        analysis = {}
        for message in state["messages"]:
            if message["role"] == "assistant" and "analysis" in message["content"].lower():
                analysis["general_insights"] = message["content"]
                break
        
        # If we still don't have an improved prompt, use a fallback extraction
        if not state.get("improved_prompt"):
            for message in reversed(state["messages"]):
                if message["role"] == "assistant":
                    # Last resort - take the last assistant message
                    state["improved_prompt"] = message["content"]
                    break
        
        state["analysis"] = analysis
        return state

    def _build_graph(self):
        conversation_analyst = self._create_conversation_analyst()
        prompt_engineer = self._create_prompt_engineer()
        issue_detector = self._create_issue_detector()

        workflow = create_supervisor(
            [conversation_analyst, prompt_engineer, issue_detector],
            model=self.model,
            prompt=(
                "You are a team supervisor managing a conversation analysis team. "
                "Your goal is to improve the system prompt based on conversation transcripts. "
                "For analyzing user intents and agent responses, use conversation_analyst. "
                "For detecting issues in conversations, use issue_detector. "
                "For improving the system prompt, use prompt_engineer."
                "\n\n"
                "Important context: This transcript is from a financial services voice agent "
                "selling investment products. The transcript may be incomplete or have breaks, "
                "so focus on understanding the context from what is available."
            ),
            supervisor_name='analysis_supervisor'
        )

        graph = StateGraph(ConversationState)
        graph.add_node("preprocess", self._preprocess_transcript_func)
        graph.add_node("analysis_team", workflow)
        graph.add_node("postprocess", self._postprocess_results_func)

        graph.add_edge(START, "preprocess")
        graph.add_edge("preprocess", "analysis_team")
        graph.add_edge("analysis_team", "postprocess")
        graph.add_edge("postprocess", END)

        return graph.compile()

    def _create_conversation_analyst(self):
        @tool
        def analyze_user_intent(transcript: str) -> str:
            """Analyze user intentions, needs, and expectations from the conversation"""
            return "User intent analysis results"

        @tool
        def analyze_agent_responses(transcript: str) -> str:
            """Analyze how well the agent responded to user queries and identify missed opportunities"""
            return "Agent response analysis results"
            
        @tool
        def identify_key_moments(transcript: str) -> str:
            """Identify critical moments in the conversation where the agent should have acted differently"""
            return "Key moments analysis"

        analyst = create_react_agent(
            model=self.model,
            tools=[analyze_user_intent, analyze_agent_responses, identify_key_moments],
            name="conversation_analyst",
            prompt=(
                "You are an expert in financial sales conversation analysis. "
                "Identify patterns, intents, and the effectiveness of responses in voice conversations. "
                "Focus on understanding where the agent missed user intent, provided incomplete answers, "
                "or failed to ask follow-up questions. "
                "Pay special attention to opportunities to collect key information about the client's "
                "investment preferences, risk tolerance, and financial goals. "
                "The transcripts may be incomplete with breaks, so make reasonable inferences about context."
            )
        )

        return analyst

    def _create_issue_detector(self):
        @task
        def analyze_issues(messages):
            system_message = {
                "role": "system",
                "content": (
                    "Identify issues in the conversation where the agent failed to properly address user needs. "
                    "Look for misunderstandings, missing context, or prompt limitations. "
                    "Specifically identify: "
                    "1. Instances where the agent provided potentially inaccurate information (hallucinations) "
                    "2. Missed opportunities to ask follow-up questions "
                    "3. Moments where the agent failed to build rapport "
                    "4. Points where the agent did not collect key information about the client's needs "
                    "The transcripts may be incomplete with breaks, so make reasonable inferences about context."
                )
            }
            msg = self.model.invoke([system_message] + messages)
            return msg

        @entrypoint()
        def issue_detector(state):
            issues = analyze_issues(state['messages']).content
            new_message = {"role": "assistant", "content": issues}
            messages = state['messages'] + [new_message]
            return {"messages": messages}

        issue_detector.name = "issue_detector"
        return issue_detector

    def _create_prompt_engineer(self):
        @tool
        def suggest_prompt_improvements(current_prompt: str, analysis: str) -> str:
            """Suggest specific improvements to the system prompt based on conversation analysis"""
            return "Prompt improvement suggestions"

        @tool
        def generate_improved_prompt(current_prompt: str, analysis: str) -> str:
            """Generate a complete improved system prompt incorporating all suggested improvements"""
            return "Improved system prompt"

        engineer = create_react_agent(
            model=self.model,
            tools=[suggest_prompt_improvements, generate_improved_prompt],
            name="prompt_engineer",
            prompt=(
                "You are an expert prompt engineer for financial services voice agents. "
                "Your task is to improve the system prompt based on the analysis of the conversation transcript. "
                "Focus on addressing user intents and agent responses. "
                "The improved prompt should:"
                "\n1. Make the agent more inquisitive about the person they're talking to"
                "\n2. Help develop a consistent persona for the agent"
                "\n3. Guide the agent to gather key information about investment preferences"
                "\n4. Add guardrails to prevent hallucination and inaccurate information"
                "\n5. Handle incomplete or broken transcripts by maintaining context"
            )
        )

        return engineer

    def analyze_transcript(self, transcript: str, current_prompt: str) -> Dict[str, Any]:
        initial_state = {
            "transcript": transcript,
            "current_prompt": current_prompt,
            "messages": [],
            "analysis": {},
            "improved_prompt": "",
            "active_agent": ""
        }

        result = self.app.invoke(initial_state)

        return {
            "analysis": result["analysis"],
            "improved_prompt": result["improved_prompt"]
        }