from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from groove.ffmpeg_runtime import FFmpegInvocation


def _escape_concat_file_path(path: Path) -> str:
    return str(path.resolve()).replace("'", r"'\''")


class ConcatenateInputRef(BaseModel):
    id: str


ConcatenateInput = str | ConcatenateInputRef


class ConcatenateOperation(BaseModel):
    type: Literal["concatenate"]
    inputs: list[ConcatenateInput]
    mode: Literal["reencode", "copy"] = "reencode"
    name: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    output: str | None = None

    @model_validator(mode="after")
    def must_have_at_least_two_inputs(self) -> "ConcatenateOperation":
        if len(self.inputs) < 2:
            raise ValueError("inputs must contain at least two files")
        return self

    def resolve_input_paths(self, results_by_id: dict[str, Path]) -> list[Path]:
        resolved: list[Path] = []
        for item in self.inputs:
            if isinstance(item, str):
                resolved.append(Path(item))
                continue
            resolved_path = results_by_id.get(item.id)
            if resolved_path is None:
                raise ValueError(
                    f"Unknown operation id reference in concatenate inputs: {item.id!r}"
                )
            resolved.append(resolved_path)
        return resolved

    def build_invocation(
        self, output_dir: Path, input_paths: list[Path] | None = None
    ) -> FFmpegInvocation:
        resolved_input_paths = input_paths or [Path(p) for p in self.inputs if isinstance(p, str)]
        if input_paths is None and len(resolved_input_paths) != len(self.inputs):
            raise ValueError(
                "concatenate inputs include id references but no resolved input_paths were provided"
            )
        input_paths = resolved_input_paths
        for input_path in input_paths:
            if not input_path.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")

        label = self.name or ", ".join([p.name for p in input_paths])
        print(f"[{self.id}] Concatenating: {label} (mode={self.mode})")
        output_path = output_dir / f"{input_paths[0].stem}_concat{input_paths[0].suffix}"

        if self.mode == "copy":
            list_file_path = output_dir / f"{self.id}.txt"
            list_file_content = "".join(
                [f"file '{_escape_concat_file_path(path)}'\n" for path in input_paths]
            )
            list_file_path.write_text(list_file_content, encoding="utf-8")
            command = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file_path),
                "-c",
                "copy",
                str(output_path),
            ]
            return FFmpegInvocation(
                command=command,
                output_path=output_path,
                cleanup_paths=[list_file_path],
            )
        else:
            command = ["ffmpeg", "-y"]
            for path in input_paths:
                command.extend(["-i", str(path)])
            filter_parts: list[str] = [
                "[0:v:0]fps=25,format=yuv420p,setsar=1,split=2[v0][vref0]",
                "[0:a:0]aformat=sample_rates=48000:channel_layouts=stereo[a0]",
            ]
            for i in range(1, len(input_paths)):
                prev_ref = f"vref{i - 1}"
                filter_parts.append(
                    f"[{i}:v:0][{prev_ref}]scale2ref=w=iw:h=ih[v{i}s][vref{i}]"
                )
                filter_parts.append(f"[v{i}s]fps=25,format=yuv420p,setsar=1[v{i}]")
                filter_parts.append(f"[vref{i}]nullsink")
                filter_parts.append(
                    f"[{i}:a:0]aformat=sample_rates=48000:channel_layouts=stereo[a{i}]"
                )
            concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(input_paths)))
            filter_parts.append(
                f"{concat_inputs}concat=n={len(input_paths)}:v=1:a=1[outv][outa]"
            )
            command.extend(
                [
                    "-filter_complex",
                    ";".join(filter_parts),
                    "-map",
                    "[outv]",
                    "-map",
                    "[outa]",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(output_path),
                ]
            )
            return FFmpegInvocation(command=command, output_path=output_path)
