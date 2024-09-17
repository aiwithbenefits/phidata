from __future__ import annotations

import asyncio
from typing import AsyncIterable

import fastapi_poe as fp
from modal import Image, App, asgi_app

# Import get_agent from your Phidata agent module
from original_agent_test import get_agent

class PhidataPoeBot(fp.PoeBot):
  def __init__(self):
      super().__init__()
      # Ensure required services are running
      self.ensure_pgvector_running()
      # Initialize the Phidata agent with desired tools and assistants
      self.agent = get_agent(
          llm_id="gpt-4o-mini",
          calculator=True,
          ddg_search=True,
          file_tools=True,
          finance_tools=True,
          data_analyst=True,
          python_assistant=True,
          research_assistant=True,
          investment_assistant=True,
          firecrawl_tools=True,
      )
      # Optionally, create an agent run if needed
      self.agent_run_id = self.agent.create_run()

  async def get_response(self, request: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
      # Extract the user's message from the request
      user_message = request.query[-1].content

      # Run the agent in a separate thread to avoid blocking
      loop = asyncio.get_event_loop()
      response_text = await loop.run_in_executor(None, self.run_agent, user_message)

      # Yield the response back to the user
      yield fp.PartialResponse(text=response_text)

  def run_agent(self, user_message: str) -> str:
      # This method runs the agent synchronously and collects the response
      response_text = ""
      for delta in self.agent.run(user_message):
          response_text += delta
      return response_text

  def ensure_pgvector_running(self):
      """Ensures that the PgVector Docker container is running."""
      import docker
      import time

      client = docker.from_env()
      try:
          container = client.containers.get("pgvector")
          if container.status != "running":
              print("Starting PgVector container...")
              container.start()
              # Give the database some time to start up
              time.sleep(10)
      except docker.errors.NotFound:
          print("PgVector container not found, creating and starting...")
          client.containers.run(
              "phidata/pgvector:16",
              name="pgvector",
              detach=True,
              ports={"5432/tcp": 5532},
              environment={
                  "POSTGRES_DB": "ai",
                  "POSTGRES_USER": "ai",
                  "POSTGRES_PASSWORD": "ai",
              },
          )
          # Give the database some time to start up
          time.sleep(15)

  async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
      # Return any specific settings for the bot
      return fp.SettingsResponse()

# Define the Modal image with required dependencies
REQUIREMENTS = [
    "fastapi-poe==0.0.48",
    "docker",
    "firecrawl",
    "phidata",
    "bs4",
    "duckduckgo-search",
    "exa-py",
    "nest-asyncio",
    "openai",
    "pgvector",
    "psycopg2-binary",  # Use psycopg2-binary instead of psycopg[binary]
    "pypdf",
    "sqlalchemy",
    "yfinance",
    "duckdb",
    "pandas",
    "matplotlib",
]
image = Image.debian_slim().pip_install(*REQUIREMENTS)


# Define the Modal stub
app = App("phidata-poe-bot")

@app.function(image=image)
@asgi_app()
def fastapi_app():
  bot = PhidataPoeBot()
  app = fp.make_app(bot, allow_without_key=True)
  return app
