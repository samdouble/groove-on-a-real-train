from typing import Literal

import yaml
import yt_dlp
from pydantic import BaseModel, HttpUrl, field_validator

CONFIG_PATH = "/app/config.yaml"


class YtDlpOptions(BaseModel):
    format: str = "bestvideo+bestaudio/best"
    merge_output_format: Literal["mp4", "mkv", "webm"] = "mp4"


class Config(BaseModel):
    url: HttpUrl
    yt_dlp: YtDlpOptions = YtDlpOptions()

    @field_validator("url")
    @classmethod
    def must_be_youtube(cls, v: HttpUrl) -> HttpUrl:
        host = v.host or ""
        if not any(h in host for h in ("youtube.com", "youtu.be")):
            raise ValueError(f"URL must be a YouTube link, got: {v}")
        return v


def load_config(path: str) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return Config.model_validate(raw)


def main():
    config = load_config(CONFIG_PATH)
    url = str(config.url)
    ydl_opts = {
        **config.yt_dlp.model_dump(),
        "outtmpl": "/downloads/%(title)s.%(ext)s",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print(f"Downloading: {info['title']}")
        ydl.download([url])

    print("Download complete!")


if __name__ == "__main__":
    main()
