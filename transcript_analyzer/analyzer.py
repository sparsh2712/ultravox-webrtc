from typing import TypedDict, List, Dict, Any
import re
import json
import os
from dotenv import load_dotenv
# Core LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.func import entrypoint, task

load_dotenv()

class ConversationState(TypedDict):
    transcript: str
    messages: List[Dict[str, Any]]
    current_prompt: str
    analysis: Dict[str, Any]
    active_agent: str
    transcript_path: str

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
                "content": f"Please analyze this conversation transcript:\n\n{formatted_transcript}\n\nCurrent system prompt:\n\n{state['current_prompt']}"
            }
        ]
        
        return {
            **state,
            "messages": messages,
            "analysis": {}
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
    
    def _save_analysis_results_func(self, state):
        """Save analysis results to a JSON file"""
        transcript_path = state["transcript_path"]
        
        # Extract the directory path and filename
        directory = os.path.dirname(transcript_path)
        filename = os.path.basename(transcript_path)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # Get the analysis data
        analysis_data = state.get("analysis", {})
        
        # Path to the JSON file
        json_path = os.path.join(directory, "call_analysis.json")
        
        # Create or update the JSON file
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
        else:
            data = {}
        
        # Add or update the analysis for this transcript
        data[filename_without_ext] = analysis_data
        
        # Save the updated JSON
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return state

    def _build_graph(self):
        # Create the main workflow graph
        graph = StateGraph(ConversationState)
        graph.add_node("preprocess", self._preprocess_transcript_func)
        graph.add_node("analyze", self._analyze_transcript)
        graph.add_node("save_results", self._save_analysis_results_func)

        graph.add_edge(START, "preprocess")
        graph.add_edge("preprocess", "analyze")
        graph.add_edge("analyze", "save_results")
        graph.add_edge("save_results", END)

        return graph.compile()
    
    def _analyze_transcript(self, state):
        """Analyze the transcript using the LLM"""
        system_message = {
            "role": "system",
            "content": (
                "You are an expert in financial sales conversation analysis. "
                "Analyze this conversation transcript and provide a structured analysis with the following format:"
                "\n\n"
                "1. First identify 2-3 key strengths of the agent in the conversation\n"
                "2. Then identify 2-3 specific issues where the agent could improve\n"
                "3. For each issue, provide a specific example from the transcript\n"
                "4. For each issue, provide a specific recommendation for improvement\n"
                "\n"
                "Keep your analysis concise and focused on the most important points. Format your response "
                "as a clean JSON object with the following structure:"
                "\n\n"
                "{\n"
                "  \"strengths\": [\"strength 1\", \"strength 2\"],\n"
                "  \"issues\": [\n"
                "    {\n"
                "      \"issue\": \"Description of issue 1\",\n"
                "      \"example\": \"Specific example from transcript\",\n"
                "      \"recommendation\": \"How to improve\"\n"
                "    },\n"
                "    {\n"
                "      \"issue\": \"Description of issue 2\",\n"
                "      \"example\": \"Specific example from transcript\",\n"
                "      \"recommendation\": \"How to improve\"\n"
                "    }\n"
                "  ]\n"
                "}"
                "\n\n"
                "Focus on identifying issues in the conversation where the agent failed to properly address user needs. "
                "Look for misunderstandings, missing context, or prompt limitations. "
                "Pay special attention to opportunities to collect key information about the client's "
                "investment preferences, risk tolerance, and financial goals. "
                "The transcripts may be incomplete with breaks, so make reasonable inferences about context."
            )
        }
        
        # Create a new list with the system message and existing messages
        messages = [system_message] + state["messages"]
        
        # Invoke the model to analyze the transcript
        response = self.model.invoke(messages)
        
        # Try to parse the response as JSON
        try:
            # Try to find JSON in the response
            content = response.content
            # Look for JSON pattern (between curly braces)
            json_match = re.search(r'(\{.*\})', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                analysis_data = json.loads(json_str)
            else:
                # If no JSON pattern found, try parsing the whole content
                analysis_data = json.loads(content)
                
        except json.JSONDecodeError:
            # If parsing fails, use the raw text and note the issue
            analysis_data = {
                "error": "Failed to parse response as JSON",
                "raw_analysis": response.content
            }
        
        # Add the model's response to the messages
        new_message = {"role": "assistant", "content": response.content}
        updated_messages = state["messages"] + [new_message]
        
        return {
            **state,
            "messages": updated_messages,
            "analysis": analysis_data
        }

    def analyze_transcript(self, transcript_path: str, current_prompt: str) -> Dict[str, Any]:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = f.read()
            
        initial_state = {
            "transcript": transcript,
            "current_prompt": current_prompt,
            "messages": [],
            "analysis": {},
            "active_agent": "",
            "transcript_path": transcript_path
        }

        result = self.app.invoke(initial_state)
        return result["analysis"]

if __name__ == "__main__":
    import os
    
    # Set the transcript path directly as a variable
    text_file_path = "/Users/sparsh/Desktop/ultravox-webrtc/transcripts/2025-04-08/test_call.txt"
    
    # Check if the file exists
    if not os.path.exists(text_file_path):
        print(f"Error: File {text_file_path} not found")
        exit(1)
    
    # Load current prompt from prompt.txt or use default
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            current_prompt = f.read()
    except FileNotFoundError:
        current_prompt = "You are a helpful AI assistant."
        print("Warning: prompt.txt not found, using default prompt")
    
    # Get API key from environment or use a default value
    api_key = os.environ.get("GOOGLE_API_KEY", "your-api-key-here")
    
    analyzer = TranscriptAnalyzer(api_key)
    result = analyzer.analyze_transcript(text_file_path, current_prompt)
    
    print(f"Analysis completed and saved to {os.path.dirname(text_file_path)}/call_analysis.json")