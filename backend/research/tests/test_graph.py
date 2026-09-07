from django.test import SimpleTestCase

from research.agent.graph import build_research_graph
from research.agent.nodes.context import NodeContext
from research.models import ResearchJob


class GraphCompileTests(SimpleTestCase):
    def test_graph_compiles_without_constructing_paid_providers(self):
        job = ResearchJob(website_url="https://example.com", user_prompt="Research")
        graph = build_research_graph(NodeContext(job, llm=object(), embedding_model=object(), vector_store=object()))
        self.assertIsNotNone(graph)

