"""
MCP Server Builder using service definitions
"""

from agents.mcp.server import MCPServerStdio, MCPServerStreamableHttp, MCPServerStreamableHttpParams
from src.services import get_service_definition


def build_mcp_server(service_name: str, service_config: dict):
    """
    Create MCP server from service definition.
    
    Args:
        service_name: Name of the service
        service_config: Runtime configuration with sensitive values
        
    Returns:
        MCP server instance
    """
    definition = get_service_definition(service_name)
    mcp_config = definition.get("mcp_server")
    
    if not mcp_config:
        raise ValueError(f"Service {service_name} has no MCP server configuration")
    
    server_type = mcp_config["type"]
    
    if server_type == "stdio":
        # Build stdio server parameters
        params = {
            "command": mcp_config["command"],
            "args": list(mcp_config["args"]),  # Make a copy
        }
        
        # Handle special config requirements
        if "requires_config" in mcp_config:
            requirements = mcp_config["requires_config"]
            
            # Handle environment variables
            if "env" in requirements:
                params["env"] = {}
                for key, template in requirements["env"].items():
                    # Replace placeholders with actual values
                    params["env"][key] = template.format(**service_config)
            
            # Handle args that need to be appended
            if "args_append" in requirements:
                for arg_template in requirements["args_append"]:
                    params["args"].append(arg_template.format(**service_config))
        
        return MCPServerStdio(
            params=params,
            client_session_timeout_seconds=mcp_config.get("timeout", 120),
            cache_tools_list=mcp_config.get("cache_tools", True)
        )
    
    elif server_type == "http":
        # Build HTTP server parameters
        headers = {}
        
        # Handle special config requirements
        if "requires_config" in mcp_config:
            requirements = mcp_config["requires_config"]
            
            # Handle headers that need config values
            if "headers" in requirements:
                for key, template in requirements["headers"].items():
                    headers[key] = template.format(**service_config)
        
        params = MCPServerStreamableHttpParams(
            url=mcp_config["url"],
            headers=headers,
            timeout_seconds=mcp_config.get("timeout", 30)
        )
        
        return MCPServerStreamableHttp(
            params=params,
            cache_tools_list=mcp_config.get("cache_tools", True),
            name=f"{service_name.title()} MCP Server",
            client_session_timeout_seconds=mcp_config.get("timeout", 120)
        )
    
    else:
        raise ValueError(f"Unknown MCP server type: {server_type}")