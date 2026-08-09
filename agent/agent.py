"""
Wanderpath Travel Agency - Master Agent Loop (MCP + Memory + RAG + Self-RAG)
=============================================================================
Combines:
- MCP Server Tool & Resource Access
- Short-Term Memory & Plan Scratchpad
- Promote-or-Drop Router & Semantic Memory
- Vector Store & Hybrid RAG Retrieval
- Self-RAG Verification Layer
"""

import asyncio
import json
import logging
import os
import pathlib
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import sys
import pathlib

# Ensure project root is dynamically added to sys.path
project_root = pathlib.Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- Now import your custom modules ---
from memory.short_term import ShortTermMemory
from memory.scratchpad import Scratchpad
from memory.stores import EpisodicStore, SemanticStore
from memory.routing import PromoteDropRouter
from memory.consolidation import ConsolidationEngine
from rag.vector_store import WanderpathVectorStore
from rag.architectures.retrievers import HybridSearchRAG
from rag.self_rag import SelfRAGVerifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("WanderpathMasterAgent")

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


class WanderpathAgentSystem:
    def __init__(self):
        # 1. Memory Subsystems
        self.scratchpad = Scratchpad()
        self.short_term_memory = ShortTermMemory(max_messages=8)
        self.episodic_store = EpisodicStore()
        self.semantic_store = SemanticStore()
        self.router = PromoteDropRouter(self.episodic_store)
        self.consolidation = ConsolidationEngine(self.episodic_store, self.semantic_store)

        # 2. RAG Subsystems
        self.vector_db = WanderpathVectorStore(collection_name="agent_rag_db", persist_dir="./rag/chroma_agent")
        self._init_corpus()
        self.hybrid_rag = HybridSearchRAG(self.vector_db, self.corpus_docs)
        self.verifier = SelfRAGVerifier()

    def _init_corpus(self):
        self.corpus_docs = [
            "Alpine Resort & Spa (Zermatt, Switzerland): Standard cancellation window is 14 days prior to check-in. Pre-spa fasting is 2 hours.",
            "Tokyo Grand Palace (Tokyo, Japan): Service animals accommodated across all suite tiers. Transit strike on Yamanote line scheduled for late 2026.",
            "Bali Sun & Sand Resort (Bali, Indonesia): Peak season packages in December are strictly non-refundable. Visa on Arrival required.",
        ]
        metadatas = [{"country": "Switzerland"}, {"country": "Japan"}, {"country": "Indonesia"}]
        ids = ["doc_1", "doc_2", "doc_3"]
        self.vector_db.ingest_documents(documents=self.corpus_docs, metadatas=metadatas, ids=ids)

    async def execute_query(
        self, session: ClientSession, http_client: httpx.AsyncClient, api_key: str, user_prompt: str, mcp_tools: list
    ) -> str:
        logger.info(f"\n🗣️ User Query: '{user_prompt}'")

        # 1. Update Short-Term Memory
        self.short_term_memory.add_message("user", user_prompt)

        # 2. RAG Retrieval Step (Unstructured Knowledge)
        retrieved = self.hybrid_rag.retrieve(user_prompt, top_k=1)
        rag_context = retrieved[0]["document"] if retrieved else "No relevant document found."
        logger.info(f"🔍 RAG Retrieved Context: '{rag_context}'")

        # 3. Format System Context (Scratchpad + Semantic Memory + RAG Context)
        active_semantic_facts = [f.fact_value for f in self.semantic_store.facts if f.status == "ACTIVE"]
        
        system_context = (
            f"{self.scratchpad.render_context_header()}\n"
            f"KNOWN SEMANTIC FACTS: {active_semantic_facts}\n"
            f"RETRIEVED KNOWLEDGE: {rag_context}\n"
        )

        # 4. Prepare API Call
        formatted_tools = [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}}
            for t in mcp_tools
        ]

        messages = [{"role": "system", "content": system_context}] + self.short_term_memory.get_transcript()

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "mistral-large-latest", "messages": messages, "tools": formatted_tools, "tool_choice": "auto"}

        # 5. Call LLM
        response = await http_client.post(MISTRAL_API_URL, headers=headers, json=payload, timeout=30.0)
        data = response.json()
        message = data["choices"][0]["message"]

        # 6. Execute MCP Tools if selected
        if message.get("tool_calls"):
            for call in message["tool_calls"]:
                tool_name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])
                logger.info(f"⚡ Executing Tool '{tool_name}' with args: {args}")
                
                result = await session.call_tool(tool_name, arguments=args)
                obs = result.content[0].text
                
                self.short_term_memory.add_message("assistant", obs)
                logger.info(f"📥 Server Observation: {obs}")
                return obs
        else:
            raw_answer = message.get("content", "")
            
            # 7. Self-RAG Verification Check
            verification = self.verifier.verify_rag_pipeline(user_prompt, [rag_context], raw_answer)
            logger.info(f"🛡️ Self-RAG Verification Status: {verification['status']}")
            
            self.short_term_memory.add_message("assistant", raw_answer)
            return raw_answer


async def main():
    load_dotenv()
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        logger.critical("MISTRAL_API_KEY missing from .env!")
        return

    agent_system = WanderpathAgentSystem()

    project_root = pathlib.Path(__file__).parent.parent.resolve()
    python_exec = project_root / "mcp_server" / ".venv" / "Scripts" / "python.exe"
    server_script = project_root / "mcp_server" / "server.py"

    server_params = StdioServerParameters(command=str(python_exec), args=[str(server_script), "--transport", "stdio"])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = (await session.list_tools()).tools

            async with httpx.AsyncClient() as http_client:
                # Query 1: Triggers MCP Tool + Scratchpad Update
                agent_system.scratchpad.set_goal("Verify booking and check hotel policy")
                await agent_system.execute_query(session, http_client, api_key, "Can you pull up itinerary 105?", mcp_tools)

                # Query 2: Triggers RAG Retrieval + Self-RAG Check
                await agent_system.execute_query(session, http_client, api_key, "What is the cancellation window in Zermatt?", mcp_tools)

    logger.info("Master Agent loop completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())