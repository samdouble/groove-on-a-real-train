import subprocess


def main():
    result = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True,
    )
    print(result.stdout.splitlines()[0])
    print("ffmpeg is ready to use.")


if __name__ == "__main__":
    main()
