from pathlib import Path

import pytest

from groove.operations.apply_filter import ApplyFilterOperation


def make_op(tmp_path: Path, **kwargs: object) -> ApplyFilterOperation:
    input_file = tmp_path / "video.mp4"
    input_file.touch()
    data: dict[str, object] = {
        "type": "apply_filter",
        "input": str(input_file),
        "filter": "gta5wasted",
        "timestamp": 9.05,
    }
    data.update(kwargs)
    return ApplyFilterOperation.model_validate(data)


class TestApplyFilterOperationBuildInvocation:
    def test_raises_when_input_file_missing(self, tmp_path: Path) -> None:
        op = ApplyFilterOperation(
            type="apply_filter",
            input="/nonexistent/file.mp4",
            filter="gta5wasted",
            timestamp=9.05,
        )
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            op.build_invocation(output_dir=tmp_path)

    def test_build_invocation_gta5wasted(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        op = make_op(tmp_path, id="test-id")

        invocation = op.build_invocation(output_dir=output_dir)

        assert invocation.output_path == output_dir / "video_gta5wasted.mp4"
        args = invocation.command
        assert args[0] == "ffmpeg"
        assert "-itsoffset" in args
        assert "12.05" in args
        assert "-filter_complex" in args
        filter_expr = args[args.index("-filter_complex") + 1]
        assert "concat=n=3:v=1:a=1[v0out][a0out]" in filter_expr
