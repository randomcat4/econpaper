from src.agents.metadata_agent.orchestrator import ReviewOrchestrator


def test_needs_final_compile_when_latest_pdf_is_not_in_final_dir(tmp_path):
    iteration_dir = tmp_path / "iteration_01"
    final_dir = tmp_path / "iteration_01_final"
    iteration_dir.mkdir()

    needs_compile, reason = ReviewOrchestrator._needs_final_compile(
        final_fingerprint="same",
        last_compiled_fingerprint="same",
        pdf_path=str(iteration_dir / "main.pdf"),
        final_dir=final_dir,
    )

    assert needs_compile is True
    assert "not in the final output directory" in reason


def test_skips_final_compile_when_latest_pdf_is_already_final(tmp_path):
    final_dir = tmp_path / "iteration_01_final"
    final_dir.mkdir()

    needs_compile, reason = ReviewOrchestrator._needs_final_compile(
        final_fingerprint="same",
        last_compiled_fingerprint="same",
        pdf_path=str(final_dir / "main.pdf"),
        final_dir=final_dir,
    )

    assert needs_compile is False
    assert "no content changes" in reason


def test_needs_final_compile_when_content_changed(tmp_path):
    final_dir = tmp_path / "iteration_01_final"
    final_dir.mkdir()

    needs_compile, reason = ReviewOrchestrator._needs_final_compile(
        final_fingerprint="after",
        last_compiled_fingerprint="before",
        pdf_path=str(final_dir / "main.pdf"),
        final_dir=final_dir,
    )

    assert needs_compile is True
    assert "content changed" in reason
