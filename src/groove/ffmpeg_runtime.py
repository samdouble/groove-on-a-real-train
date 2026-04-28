import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FFmpegInvocation:
    command: list[str]
    output_path: Path
    cleanup_paths: list[Path] = field(default_factory=list)


def run_ffmpeg(invocation: FFmpegInvocation) -> Path:
    try:
        subprocess.run(invocation.command, check=True)
    finally:
        for path in invocation.cleanup_paths:
            path.unlink(missing_ok=True)
    return invocation.output_path
