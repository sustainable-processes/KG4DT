import json

from backend.app.config import Config
from backend.app.utils.graphdb_handler import GraphDBHandler
from backend.app.utils.model_agent import ModelAgent

graphdb_handler = GraphDBHandler(Config)
entity = graphdb_handler.query()
context = json.load(open("./backend/app/cases/hydrogenation/context.json", "r"))
model_agent = ModelAgent(entity, context)
print(model_agent.to_scipy_model()[1])