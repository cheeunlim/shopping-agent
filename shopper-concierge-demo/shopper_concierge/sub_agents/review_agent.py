#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from google.adk.agents import Agent
from ..prompts import instruction_review
from ..tools import query_reviews

review_agent = Agent(
  model="gemini-2.5-flash",
  name="review_agent",
  description=(
    "A review analysis expert for an e-commerce site. Analyzes reviews to "
    "answer questions about product quality, value, and experiences."
  ),
  instruction=instruction_review,
  tools=[query_reviews],
)
