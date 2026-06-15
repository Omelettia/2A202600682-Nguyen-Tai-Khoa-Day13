from __future__ import annotations

import time
from dataclasses import dataclass

from . import metrics
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text
from .tracing import get_client, observe


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


class LabAgent:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    # Disable auto-capture: the raw `message`/`user_id` args contain PII. We attach
    # redacted input/output explicitly below so traces stay PII-safe (same rule as logs).
    # run() is the root span; retrieval and the LLM call are nested child observations so
    # the Langfuse waterfall shows where time goes (e.g. the rag_slow stall in retrieve).
    @observe(capture_input=False, capture_output=False)
    def run(self, user_id: str, feature: str, session_id: str, message: str) -> AgentResult:
        client = get_client()
        client.update_current_trace(
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=["lab", feature, self.model],
            input={"feature": feature, "query_preview": summarize_text(message)},
        )

        started = time.perf_counter()

        # Child span: retrieval. During the rag_slow incident this bar shows the stall.
        with client.start_as_current_span(
            name="retrieve",
            input={"query_preview": summarize_text(message)},
        ) as span:
            docs = retrieve(message)
            span.update(output={"doc_count": len(docs)}, metadata={"doc_count": len(docs)})

        prompt = f"Feature={feature}\nDocs={docs}\nQuestion={message}"

        # Child generation: the LLM call carries model, token usage, and cost.
        with client.start_as_current_generation(
            name="llm_generate",
            model=self.model,
            input={"feature": feature},
        ) as generation:
            response = self.llm.generate(prompt)
            cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens)
            generation.update(
                output={"answer_preview": summarize_text(response.text)},
                usage_details={"input": response.usage.input_tokens, "output": response.usage.output_tokens},
                cost_details={"total": cost_usd},
            )

        quality_score = self._heuristic_quality(message, response.text, docs)
        latency_ms = int((time.perf_counter() - started) * 1000)

        client.update_current_span(
            output={"answer_preview": summarize_text(response.text)},
            metadata={"doc_count": len(docs), "quality_score": quality_score},
        )

        metrics.record_request(
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=response.text,
            latency_ms=latency_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        input_cost = (tokens_in / 1_000_000) * 3
        output_cost = (tokens_out / 1_000_000) * 15
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(token in answer.lower() for token in question.lower().split()[:3]):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)
