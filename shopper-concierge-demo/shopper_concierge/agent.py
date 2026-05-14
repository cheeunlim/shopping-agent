#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .prompts import instruction_shop
from .sub_agents.research_agent import research_agent
from .sub_agents.review_agent import review_agent
from .sub_agents.vibe_agent import vibe_agent
from .tools import find_shopping_items, query_reviews

root_agent = Agent(
  model="gemini-2.5-flash",
  name="shop_agent",
  description="A shopper's concierge for an e-commerce site",
  instruction=instruction_shop,
  tools=[
    AgentTool(agent=research_agent),
    AgentTool(agent=review_agent),
    AgentTool(agent=vibe_agent),
    find_shopping_items,
    query_reviews,
  ],
)