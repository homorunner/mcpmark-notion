import asyncio
import os
from dotenv import load_dotenv
from src.factory import MCPServiceFactory
from fastmcp import Client
from fastmcp.client.transports import StdioTransport, StreamableHttpTransport
from typing import Any

class Server:
    def __init__(self):
        load_dotenv(dotenv_path=".mcp_env", override=False)

        self.task_manager = MCPServiceFactory.create_task_manager("notion")
        self.state_manager = MCPServiceFactory.create_state_manager("notion")
        # 作为一个例子，只加载第一个task
        self.task = self.task_manager.discover_all_tasks()[0]


    async def set_up(self):
        # setup mcp
        os.environ['NOTION_TOKEN'] = os.environ['EVAL_NOTION_API_KEY']
        mcp_transport = StdioTransport(command='notion-mcp-server', args=[])
        print('using auth ', os.environ['EVAL_NOTION_API_KEY'])
        # mcp_transport = StreamableHttpTransport(url='https://mcp.notion.com/mcp')
        # mcp_transport.headers = {
        #     'Authorization': 'Bearer ' + os.environ['EVAL_NOTION_API_KEY'],
        #     'Notion-Version': '2022-06-28',
        # }
        self.mcp_client = Client(mcp_transport)
        await self.mcp_client.__aenter__()

        for tool in await self.mcp_client.list_tools():
            print(tool.name, " : ", tool.description)
        
        await asyncio.to_thread(
            self.state_manager.set_up,
            self.task
        )
    
    async def call_mcp(self, tool_name: str, tool_arguments: dict[str, Any] = {}) -> str:
        result = await self.mcp_client.call_tool(tool_name, tool_arguments)
        return result.content[0].text

    async def clean_up(self):
        await asyncio.to_thread(
            self.state_manager.clean_up,
            self.task
        )

        if self.mcp_client:
            self.mcp_client.__aexit__()

if __name__ == "__main__": # just for test
    server = Server()
    asyncio.run(server.set_up())

    get_self_result = asyncio.run(server.call_mcp('API-get-self', []))
    print(f'{get_self_result=}')

    asyncio.run(server.clean_up())

