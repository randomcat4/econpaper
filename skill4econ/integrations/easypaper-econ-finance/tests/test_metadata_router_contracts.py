import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI

from src.agents.metadata_agent.models import PaperGenerationResult, PaperMetaData, PlanResult
from src.agents.metadata_agent.router import create_metadata_router


def _app(agent):
    app = FastAPI()
    app.include_router(create_metadata_router(agent))
    return app


def _client(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


def _metadata_payload(**overrides):
    payload = {
        "title": "Router Paper",
        "idea_hypothesis": "h",
        "method": "m",
        "data": "d",
        "experiments": "e",
        "references": [],
        "compile_pdf": False,
        "save_output": False,
        "output_dir": "/tmp/out",
        "template_path": "/tmp/template.zip",
        "target_pages": 8,
        "enable_planning": True,
        "enable_exemplar": True,
        "artifacts_prefix": "prefix",
    }
    payload.update(overrides)
    return payload


def _plan_result(**overrides) -> PlanResult:
    payload = {
        "paper_plan": {"title": "Router Paper", "sections": []},
        "ref_pool_snapshot": {"core_refs": [], "discovered_refs": []},
        "metadata_input": {
            "title": "Router Paper",
            "idea_hypothesis": "h",
            "method": "m",
            "data": "d",
            "experiments": "e",
        },
        "template_path": "/tmp/template.zip",
        "target_pages": 8,
        "artifacts_prefix": "prefix",
    }
    payload.update(overrides)
    return PlanResult(**payload)


@pytest.mark.asyncio
async def test_prepare_plan_route_forwards_request_contract():
    agent = MagicMock()
    agent.prepare_plan = AsyncMock(return_value=_plan_result())

    async with _client(_app(agent)) as client:
        response = await client.post("/metadata/prepare-plan", json=_metadata_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["paper_plan"]["title"] == "Router Paper"
    agent.prepare_plan.assert_awaited_once()
    kwargs = agent.prepare_plan.await_args.kwargs
    assert kwargs["metadata"].title == "Router Paper"
    assert kwargs["template_path"] == "/tmp/template.zip"
    assert kwargs["target_pages"] == 8
    assert kwargs["enable_planning"] is True
    assert kwargs["enable_exemplar"] is True
    assert kwargs["save_output"] is False
    assert kwargs["output_dir"] == "/tmp/out"
    assert kwargs["artifacts_prefix"] == "prefix"


@pytest.mark.asyncio
async def test_prepare_plan_route_maps_agent_exception_to_500():
    agent = MagicMock()
    agent.prepare_plan = AsyncMock(side_effect=RuntimeError("boom"))

    async with _client(_app(agent)) as client:
        response = await client.post("/metadata/prepare-plan", json=_metadata_payload())

    assert response.status_code == 500
    assert "boom" in response.json()["detail"]


@pytest.mark.asyncio
async def test_generate_stream_route_forwards_defaults_and_events():
    async def fake_generate_paper(*, progress_callback=None, **kwargs):
        assert kwargs["metadata"].title == "Router Paper"
        assert kwargs["compile_pdf"] is False
        assert kwargs["save_output"] is False
        assert kwargs["template_path"] == "/tmp/template.zip"
        assert kwargs["target_pages"] == 8
        assert kwargs["enable_planning"] is True
        assert kwargs["enable_exemplar"] is True
        assert kwargs["feedback_timeout"] == 300.0
        assert kwargs["artifacts_prefix"] == "prefix"
        await progress_callback({"type": "phase_start", "phase": "planning", "message": "start"})

    agent = MagicMock()
    agent.generate_paper = AsyncMock(side_effect=fake_generate_paper)

    async with _client(_app(agent)) as client:
        response = await client.post("/metadata/generate/stream", json=_metadata_payload())

    assert response.status_code == 200
    events = [line.removeprefix("data: ") for line in response.text.splitlines() if line.startswith("data: ")]
    created = json.loads(events[0])
    progress = json.loads(events[1])
    assert created["type"] == "task_created"
    assert progress["task_id"] == created["task_id"]
    assert progress["type"] == "phase_start"
    agent.generate_paper.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_from_plan_stream_route_passes_equivalent_plan_result():
    received = {}

    async def fake_execute_generation(*, progress_callback=None, **kwargs):
        received.update(kwargs)
        await progress_callback({"type": "phase_complete", "phase": "body", "message": "done"})

    agent = MagicMock()
    agent.execute_generation = AsyncMock(side_effect=fake_execute_generation)
    plan = _plan_result()

    async with _client(_app(agent)) as client:
        response = await client.post(
            "/metadata/generate-from-plan/stream",
            json=plan.model_dump(mode="json"),
        )

    assert response.status_code == 200
    assert isinstance(received["plan_result"], PlanResult)
    assert received["plan_result"].model_dump(mode="json") == plan.model_dump(mode="json")
    assert received["enable_review"] is True
    assert received["max_review_iterations"] == 3
    assert received["compile_pdf"] is True
    assert "feedback_queue" in received
    events = [line.removeprefix("data: ") for line in response.text.splitlines() if line.startswith("data: ")]
    created = json.loads(events[0])
    progress = json.loads(events[1])
    assert progress["task_id"] == created["task_id"]


@pytest.mark.asyncio
async def test_generate_from_plan_stream_rejects_invalid_plan_before_execution():
    agent = MagicMock()
    agent.execute_generation = AsyncMock()

    async with _client(_app(agent)) as client:
        response = await client.post("/metadata/generate-from-plan/stream", json={"metadata_input": {}})

    assert response.status_code == 422
    agent.execute_generation.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_from_plan_stream_rejects_planning_failure_before_execution():
    agent = MagicMock()
    agent.execute_generation = AsyncMock()
    plan = _plan_result(paper_plan={}, errors=["planning failed"])

    async with _client(_app(agent)) as client:
        response = await client.post(
            "/metadata/generate-from-plan/stream",
            json=plan.model_dump(mode="json"),
        )

    assert response.status_code == 409
    assert response.json()["detail"]["errors"] == ["planning failed"]
    agent.execute_generation.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_from_folder_route_forwards_agent_client_model_and_overrides():
    agent = MagicMock()
    agent.client = MagicMock()
    agent.model_name = "metadata-model"
    expected = PaperMetaData(
        title="Generated",
        idea_hypothesis="h",
        method="m",
        data="d",
        experiments="e",
    )

    with patch(
        "src.agents.metadata_agent.metadata_generator.generate_metadata_from_folder",
        new=AsyncMock(return_value=expected),
    ) as mock_gen:
        async with _client(_app(agent)) as client:
            response = await client.post(
                "/metadata/generate-from-folder",
                params={
                    "folder_path": "/tmp/materials",
                    "title": "Generated",
                    "style_guide": "ICML",
                    "template_path": "/tmp/template.zip",
                    "target_pages": 8,
                },
            )

    assert response.status_code == 200
    assert response.json()["title"] == "Generated"
    mock_gen.assert_awaited_once_with(
        folder_path="/tmp/materials",
        llm_client=agent.client,
        model_name="metadata-model",
        title="Generated",
        style_guide="ICML",
        template_path="/tmp/template.zip",
        target_pages=8,
    )


@pytest.mark.asyncio
async def test_generate_from_folder_maps_errors():
    agent = MagicMock()
    agent.client = MagicMock()
    agent.model_name = "metadata-model"

    with patch(
        "src.agents.metadata_agent.metadata_generator.generate_metadata_from_folder",
        new=AsyncMock(side_effect=FileNotFoundError("missing")),
    ):
        async with _client(_app(agent)) as client:
            response = await client.post(
                "/metadata/generate-from-folder",
                params={"folder_path": "/tmp/missing"},
            )
    assert response.status_code == 404

    with patch(
        "src.agents.metadata_agent.metadata_generator.generate_metadata_from_folder",
        new=AsyncMock(side_effect=RuntimeError("provider failed")),
    ):
        async with _client(_app(agent)) as client:
            response = await client.post(
                "/metadata/generate-from-folder",
                params={"folder_path": "/tmp/materials"},
            )
    assert response.status_code == 500
    assert "Metadata generation failed:" in response.json()["detail"]
