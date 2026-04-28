from pathlib import Path

import pytest
from pydantic import ValidationError

from groove.operations.concatenate import ConcatenateInputRef, ConcatenateOperation


def make_op(tmp_path: Path, **kwargs: object) -> ConcatenateOperation:
    file_a = tmp_path / "a.mp4"
    file_b = tmp_path / "b.mp4"
    file_a.touch()
    file_b.touch()
    data: dict[str, object] = {
        "type": "concatenate",
        "inputs": [str(file_a), str(file_b)],
    }
    data.update(kwargs)
    return ConcatenateOperation.model_validate(data)


class TestConcatenateOperationValidation:
    def test_valid_config(self, tmp_path: Path) -> None:
        op = make_op(tmp_path)
        assert len(op.inputs) == 2
        assert op.mode == "reencode"

    def test_requires_at_least_two_inputs(self, tmp_path: Path) -> None:
        file_a = tmp_path / "a.mp4"
        file_a.touch()
        with pytest.raises(ValidationError, match="at least two"):
            ConcatenateOperation(type="concatenate", inputs=[str(file_a)])

    def test_id_is_auto_generated(self, tmp_path: Path) -> None:
        op1 = make_op(tmp_path)
        op2 = make_op(tmp_path)
        assert op1.id != op2.id

    def test_name_defaults_to_none(self, tmp_path: Path) -> None:
        op = make_op(tmp_path)
        assert op.name is None

    def test_output_defaults_to_none(self, tmp_path: Path) -> None:
        op = make_op(tmp_path)
        assert op.output is None

    def test_accepts_operation_id_ref_input(self, tmp_path: Path) -> None:
        file_a = tmp_path / "a.mp4"
        file_a.touch()
        op = ConcatenateOperation(
            type="concatenate",
            inputs=[str(file_a), ConcatenateInputRef(id="intro")],
        )
        assert len(op.inputs) == 2


class TestConcatenateOperationBuildInvocation:
    def test_raises_when_input_file_missing(self, tmp_path: Path) -> None:
        op = ConcatenateOperation(
            type="concatenate",
            inputs=["/nonexistent/a.mp4", "/nonexistent/b.mp4"],
        )
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            op.build_invocation(output_dir=tmp_path)

    def test_resolve_input_paths_uses_operation_results(self, tmp_path: Path) -> None:
        file_a = tmp_path / "a.mp4"
        file_b = tmp_path / "b.mp4"
        file_a.touch()
        file_b.touch()
        op = ConcatenateOperation(
            type="concatenate",
            inputs=[str(file_a), {"id": "intro"}],
        )

        resolved = op.resolve_input_paths(results_by_id={"intro": file_b})

        assert resolved == [file_a, file_b]

    def test_resolve_input_paths_raises_on_unknown_id(self, tmp_path: Path) -> None:
        file_a = tmp_path / "a.mp4"
        file_a.touch()
        op = ConcatenateOperation(
            type="concatenate",
            inputs=[str(file_a), {"id": "intro"}],
        )

        with pytest.raises(ValueError, match="Unknown operation id reference"):
            op.resolve_input_paths(results_by_id={})

    def test_build_invocation_copy_mode_calls_ffmpeg_with_correct_args(
        self, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = make_op(tmp_path, id="concat-id", mode="copy")
        invocation = op.build_invocation(output_dir=output_dir)

        assert invocation.output_path == output_dir / "a_concat.mp4"
        args = invocation.command
        assert args[0] == "ffmpeg"
        assert "-f" in args and "concat" in args
        assert "-safe" in args and "0" in args
        assert "-c" in args and "copy" in args
        assert str(output_dir / "concat-id.txt") in args
        assert args[-1] == str(output_dir / "a_concat.mp4")
        assert invocation.cleanup_paths == [output_dir / "concat-id.txt"]

    def test_build_invocation_reencode_mode_builds_filter_complex(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = make_op(tmp_path, mode="reencode")
        invocation = op.build_invocation(output_dir=output_dir)

        assert invocation.output_path == output_dir / "a_concat.mp4"
        args = invocation.command
        assert args[0] == "ffmpeg"
        assert "-filter_complex" in args
        filter_expr = args[args.index("-filter_complex") + 1]
        assert "scale2ref" in filter_expr
        assert "aformat=sample_rates=48000:channel_layouts=stereo" in filter_expr
        assert "concat=n=2:v=1:a=1[outv][outa]" in filter_expr
        assert "-map" in args
        assert "[outv]" in args and "[outa]" in args
        assert "-c:v" in args and "libx264" in args
        assert "-c:a" in args and "aac" in args

    def test_build_invocation_uses_name_as_label_when_set(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        op = make_op(tmp_path, name="Final merge", id="test-id")
        op.build_invocation(output_dir=output_dir)

        captured = capsys.readouterr()
        assert "Final merge" in captured.out
