#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from google.adk.agents import Agent
from ..prompts import instruction_vibe

vibe_agent = Agent(
  model="gemini-2.5-flash",
  name="vibe_agent",
  description=(
    "A vibe search expert for an e-commerce site. Analyzes images and "
    "queries to generate search keywords for similar vibe products."
  ),
  instruction=instruction_vibe,
  tools=[],
)
