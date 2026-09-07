from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from research.agent.nodes.answer import finalize_node, generate_answer_node, validate_answer_node
from research.agent.nodes.context import NodeContext
from research.agent.nodes.crawl import (
    analyze_request_node,
    decide_more_crawling_node,
    plan_crawl_node,
    process_documents_node,
    scrape_pages_node,
    validate_url_node,
)
from research.agent.nodes.rag import grade_documents_node, index_documents_node, retrieve_documents_node, rewrite_query_node
from research.agent.routing.conditions import route_after_crawl_decision, route_after_grading, route_after_validation
from research.agent.state import ResearchState


def build_research_graph(context: NodeContext):
    graph = StateGraph(ResearchState)
    graph.add_node("validate_url", partial(validate_url_node, context=context))
    graph.add_node("analyze_request", partial(analyze_request_node, context=context))
    graph.add_node("plan_crawl", partial(plan_crawl_node, context=context))
    graph.add_node("scrape_pages", partial(scrape_pages_node, context=context))
    graph.add_node("process_documents", partial(process_documents_node, context=context))
    graph.add_node("index_documents", partial(index_documents_node, context=context))
    graph.add_node("retrieve_documents", partial(retrieve_documents_node, context=context))
    graph.add_node("grade_documents", partial(grade_documents_node, context=context))
    graph.add_node("rewrite_query", partial(rewrite_query_node, context=context))
    graph.add_node("decide_more_crawling", partial(decide_more_crawling_node, context=context))
    graph.add_node("generate_answer", partial(generate_answer_node, context=context))
    graph.add_node("validate_answer", partial(validate_answer_node, context=context))
    graph.add_node("finalize", partial(finalize_node, context=context))

    graph.add_edge(START, "validate_url")
    graph.add_edge("validate_url", "analyze_request")
    graph.add_edge("analyze_request", "plan_crawl")
    graph.add_edge("plan_crawl", "scrape_pages")
    graph.add_edge("scrape_pages", "process_documents")
    graph.add_edge("process_documents", "index_documents")
    graph.add_edge("index_documents", "retrieve_documents")
    graph.add_edge("retrieve_documents", "grade_documents")
    graph.add_conditional_edges(
        "grade_documents",
        lambda state: route_after_grading(state, context.agent_config),
        {
            "generate_answer": "generate_answer",
            "rewrite_query": "rewrite_query",
            "decide_more_crawling": "decide_more_crawling",
        },
    )
    graph.add_edge("rewrite_query", "retrieve_documents")
    graph.add_conditional_edges(
        "decide_more_crawling",
        route_after_crawl_decision,
        {"plan_crawl": "plan_crawl", "generate_answer": "generate_answer"},
    )
    graph.add_edge("generate_answer", "validate_answer")
    graph.add_conditional_edges(
        "validate_answer",
        route_after_validation,
        {"generate_answer": "generate_answer", "finalize": "finalize"},
    )
    graph.add_edge("finalize", END)
    return graph.compile()
