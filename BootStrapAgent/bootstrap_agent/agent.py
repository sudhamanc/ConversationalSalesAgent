import json
import os
from typing import Optional, Dict, List, Any
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv

# Try importing Google ADK dependencies (may not be available in test environments)
try:
    import vertexai
    from google.adk.agents import Agent
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models import LlmRequest, LlmResponse
    from google.adk.tools import agent_tool, google_search
    from google.genai import types
    HAS_GOOGLE_ADK = True
except (ImportError, ModuleNotFoundError):
    HAS_GOOGLE_ADK = False
    # Stub classes for testing without dependencies
    class Agent:
        pass
    class CallbackContext:
        pass
    class types:
        class GenerateContentConfig:
            def __init__(self, **kwargs):
                pass
        class SafetySetting:
            def __init__(self, **kwargs):
                pass
        class HarmCategory:
            HARM_CATEGORY_DANGEROUS_CONTENT = 0
            HARM_CATEGORY_HARASSMENT = 0
            HARM_CATEGORY_HATE_SPEECH = 0
            HARM_CATEGORY_SEXUALLY_EXPLICIT = 0
        class HarmBlockThreshold:
            BLOCK_LOW_AND_ABOVE = 0


# ==================== BASE AGENT CLASSES (Exported from Arun's base_agent_standalone.py) ====================

class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentContext:
    """Shared context across agents"""
    conversation_id: str
    user_id: Optional[str] = None
    session_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentMessage:
    """Message structure for agent communication"""
    sender: str
    receiver: str
    content: Dict[str, Any]
    message_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None


@dataclass
class Tool:
    """Tool definition for agent capabilities"""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: callable


class BaseAgent(ABC):
    """
    Base Agent Class following Google ADK patterns
    
    All specialized agents inherit from this class to ensure:
    - Consistent logging
    - State management
    - Tool registration
    - Message handling
    - Observability hooks
    """
    
    def __init__(self, 
                 agent_id: str,
                 agent_name: str,
                 description: str,
                 context: AgentContext):
        """
        Initialize base agent
        
        Args:
            agent_id: Unique identifier for the agent
            agent_name: Human-readable name
            description: Agent's purpose and capabilities
            context: Shared context object
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.description = description
        self.context = context
        self.status = AgentStatus.IDLE
        self.tools: Dict[str, Tool] = {}
        self.memory: List[Dict[str, Any]] = []
        
        # Setup logging
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self._setup_logging()
        
        # Register tools
        self._register_tools()
        
        self.logger.info(f"Initialized {agent_name} (ID: {agent_id})")
    
    def _setup_logging(self):
        """Configure agent-specific logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f'%(asctime)s - {self.agent_name} - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    @abstractmethod
    def _register_tools(self):
        """Register agent-specific tools - must be implemented by subclasses"""
        pass
    
    def register_tool(self, tool: Tool):
        """
        Register a tool with the agent
        
        Args:
            tool: Tool instance to register
        """
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a registered tool
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found in {self.agent_name}")
        
        tool = self.tools[tool_name]
        self.logger.info(f"Executing tool: {tool_name} with params: {kwargs}")
        
        try:
            result = tool.function(**kwargs)
            self.logger.info(f"Tool {tool_name} executed successfully")
            return {
                "status": "success",
                "tool": tool_name,
                "result": result
            }
        except Exception as e:
            self.logger.error(f"Tool {tool_name} failed: {str(e)}")
            return {
                "status": "error",
                "tool": tool_name,
                "error": str(e)
            }
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method - must be implemented by subclasses
        
        Args:
            input_data: Input data for the agent
            
        Returns:
            Processing result
        """
        pass
    
    def update_status(self, status: AgentStatus):
        """Update agent status"""
        old_status = self.status
        self.status = status
        self.logger.info(f"Status changed: {old_status.value} -> {status.value}")
    
    def add_to_memory(self, entry: Dict[str, Any]):
        """
        Add entry to agent memory
        
        Args:
            entry: Memory entry to store
        """
        entry['timestamp'] = datetime.now().isoformat()
        entry['agent_id'] = self.agent_id
        self.memory.append(entry)
        
    def get_memory(self, filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve agent memory
        
        Args:
            filter_type: Optional type filter
            
        Returns:
            List of memory entries
        """
        if filter_type:
            return [m for m in self.memory if m.get('type') == filter_type]
        return self.memory
    
    async def send_message(self, 
                          receiver: str, 
                          content: Dict[str, Any],
                          message_type: str = "request") -> AgentMessage:
        """
        Send message to another agent (A2A protocol)
        
        Args:
            receiver: Target agent ID
            content: Message content
            message_type: Type of message
            
        Returns:
            AgentMessage instance
        """
        message = AgentMessage(
            sender=self.agent_id,
            receiver=receiver,
            content=content,
            message_type=message_type,
            correlation_id=self.context.conversation_id
        )
        
        self.logger.info(f"Sending {message_type} to {receiver}")
        self.add_to_memory({
            'type': 'message_sent',
            'receiver': receiver,
            'message_type': message_type,
            'content': content
        })
        
        return message
    
    async def receive_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Receive and handle message from another agent
        
        Args:
            message: Incoming message
            
        Returns:
            Response to the message
        """
        self.logger.info(f"Received {message.message_type} from {message.sender}")
        self.add_to_memory({
            'type': 'message_received',
            'sender': message.sender,
            'message_type': message.message_type,
            'content': message.content
        })
        
        return await self._handle_message(message)
    
    @abstractmethod
    async def _handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming message - must be implemented by subclasses"""
        pass
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current agent state for observability
        
        Returns:
            Current state snapshot
        """
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'status': self.status.value,
            'tools': list(self.tools.keys()),
            'memory_size': len(self.memory),
            'context': {
                'conversation_id': self.context.conversation_id,
                'user_id': self.context.user_id
            }
        }
    
    def __repr__(self):
        return f"<{self.agent_name} (ID: {self.agent_id}, Status: {self.status.value})>"


# ==================== Arun's sub-agent code ====================

# configure logging __name__
custom_logger = logging.getLogger(__name__)
custom_logger.info("Initializing root agent...")

load_dotenv()

agent_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
custom_logger.info(f"setting the agent model to {agent_model}")


# Only setup root_agent if Google ADK is available
if HAS_GOOGLE_ADK:
    try:
        from .sub_agents.test.test_agent import test_agent_simple
        
        # The orchestrator will rely on its sub_agents.
        root_agent = Agent(
            name="adk_agent",
            model=agent_model,
    instruction="""You are the orchestrator for a multi-agent system. Your primary responsibility is to understand the user's intent and delegate the task to the most appropriate sub-agent or tool. You must ensure a single, coherent resolution path and enforce privacy by never exposing sensitive information.
- For simple tests, delegate to the `test_agent_simple`.
""",
    description="The main orchestrator for all conversations. It determines the user’s intent and delegates to the appropriate sub-agent or tool.",
    sub_agents=[
        test_agent_simple,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        top_p=0.1,
        top_k=10,
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
        ],
    ),
        )
    except (ImportError, ModuleNotFoundError):
        root_agent = None
        custom_logger.warning("Could not initialize root_agent - Google ADK dependencies not available")
else:
    root_agent = None
    custom_logger.info("Google ADK not available - root_agent not initialized")
