"""
Simple test for ParseAgent functionality.
Tests with a real PDF file and checks for JSON output.
"""
import asyncio
import json
import os
from pathlib import Path

import pytest

from src.config.schema import ModelConfig
from src.agents.parse_agent.parse_agent import ParseAgent


class TestParseAgentSimple:
    """Simple test suite for ParseAgent"""

    @pytest.fixture
    def config(self):
        """Create a ModelConfig for testing"""
        return ModelConfig(
            model_name="openai/gpt-4o-mini",
            api_key="test-api-key",
            base_url="https://example.invalid/v1"
        )

    def test_agent_initialization(self, config):
        """Test that ParseAgent initializes correctly"""
        agent = ParseAgent(config)
        assert agent.name == "paper_parser"
        assert agent.description == "Research paper understanding and parsing agent"
        assert agent.model_name == config.model_name

    @pytest.mark.live_llm
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_parse_pdf_output_format(self, config):
        """Test that ParseAgent can parse a PDF and output JSON format"""
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("Set OPENROUTER_API_KEY to run the live ParseAgent test.")

        pdf_path = os.environ.get("EASYPAPER_PARSE_TEST_PDF")
        if not pdf_path:
            pytest.skip("Set EASYPAPER_PARSE_TEST_PDF to a local PDF for this live test.")

        # Check if test file exists
        if not Path(pdf_path).exists():
            pytest.skip(f"Test PDF file not found at: {pdf_path}")

        live_config = ModelConfig(
            model_name=os.environ.get("OPENROUTER_PARSE_MODEL", "openai/gpt-4o-mini"),
            api_key=api_key,
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        )
        agent = ParseAgent(live_config)

        try:
            # Run the agent
            result = await agent.run(file_path=pdf_path)

            # Check that we got a result
            assert result is not None
            assert "understand_result" in result

            # Check that the understand_result is a dictionary
            understand_result = result["understand_result"]
            assert isinstance(understand_result, dict)

            # Check for expected JSON fields
            expected_fields = [
                "summary",
                "research_background",
                "research_question",
                "research_hypothesis",
                "methods",
                "results",
                "key_findings"
            ]

            for field in expected_fields:
                assert field in understand_result, f"Missing field: {field}"

            # Print the result for manual inspection
            print("\n=== ParseAgent Test Results ===")
            print(f"Successfully parsed PDF: {pdf_path}")
            print("\nParsed JSON output:")
            print(json.dumps(understand_result, indent=2))

        except Exception as e:
            pytest.fail(f"ParseAgent failed to process PDF: {e}")

    @pytest.mark.asyncio
    async def test_agent_properties(self, config):
        """Test agent properties and metadata"""
        agent = ParseAgent(config)

        # Test basic properties
        assert agent.name == "paper_parser"
        assert agent.description == "Research paper understanding and parsing agent"

        # Test router property
        from fastapi import APIRouter
        assert hasattr(agent, 'router')

        # Test endpoints_info
        endpoints = agent.endpoints_info
        assert isinstance(endpoints, list)
        assert len(endpoints) > 0


if __name__ == "__main__":
    # Run a simple test directly
    print("Running simple ParseAgent test...")

    config = ModelConfig(
        model_name="openai/gpt-4o-mini",
        api_key=os.environ.get("OPENROUTER_API_KEY", "test-api-key"),
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )

    pdf_path = os.environ.get("EASYPAPER_PARSE_TEST_PDF", "./test_pdf.pdf")

    if not Path(pdf_path).exists():
        print(f"Please place a PDF file at: {pdf_path}")
        print("Then run this test again.")
    else:
        async def run_test():
            agent = ParseAgent(config)
            try:
                result = await agent.run(file_path=pdf_path)
                print("✅ Success! ParseAgent processed the PDF.")
                if 'understand_result' in result:
                    print("JSON output format detected:")
                    print(json.dumps(result['understand_result'], indent=2))
            except Exception as e:
                print(f"❌ Error: {e}")

        asyncio.run(run_test())
