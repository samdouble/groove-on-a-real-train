from pathlib import Path


class FFmpegCommandBuilder:
    def __init__(self) -> None:
        self._args: list[str] = ["ffmpeg", "-y"]

    def add_input(self, path: Path) -> "FFmpegCommandBuilder":
        self._args.extend(["-i", str(path)])
        return self

    def set_video_filter(self, filter_expression: str) -> "FFmpegCommandBuilder":
        self._args.extend(["-vf", filter_expression])
        return self

    def set_video_codec(self, codec: str) -> "FFmpegCommandBuilder":
        self._args.extend(["-c:v", codec])
        return self

    def set_pixel_format(self, pixel_format: str) -> "FFmpegCommandBuilder":
        self._args.extend(["-pix_fmt", pixel_format])
        return self

    def set_audio_codec(self, codec: str) -> "FFmpegCommandBuilder":
        self._args.extend(["-c:a", codec])
        return self

    def set_output(self, path: Path) -> "FFmpegCommandBuilder":
        self._args.append(str(path))
        return self

    def build(self) -> list[str]:
        return list(self._args)
