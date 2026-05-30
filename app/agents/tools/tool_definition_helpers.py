from typing import List, Dict, Any
from .definitions import AGENT_TOOLS

class ToolDefinitions:
    """Tool definitions for Claude function calling"""
    
    @classmethod
    def get_tools(cls) -> List[Dict[str, Any]]:
        """Get all tool definitions for Claude function calling"""
        return AGENT_TOOLS
    
    @classmethod
    def get_tools_description(cls) -> str:
        """Get human-readable description of all tools for system prompt"""
        return "\n".join([f"- {t['name']}: {t['description']}" for t in AGENT_TOOLS])
    
    @classmethod
    def get_tool_names(cls) -> List[str]:
        """Get list of all tool names"""
        return [t["name"] for t in AGENT_TOOLS]
    
    @classmethod
    def get_tool_by_name(cls, name: str) -> Dict[str, Any]:
        """Get a specific tool definition by name"""
        for tool in AGENT_TOOLS:
            if tool["name"] == name:
                return tool
        raise ValueError(f"Tool '{name}' not found")