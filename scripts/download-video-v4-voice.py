#!/usr/bin/env python3
import shutil
import subprocess
import urllib.request
from pathlib import Path

OUTPUT = Path("submission/video/v4/voice")
URLS = {
    1: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_111950_d1526d95-aaae-49d3-903b-8bdf2ca8249d.mp3",
    2: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_111950_626aee2e-17c8-4159-8bcf-fabe03626e02.mp3",
    3: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_111950_d60edc4a-f9c1-4280-ab66-4e694ca067f5.mp3",
    4: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_112209_caf16e8e-ddae-4792-8e2c-6a537520f20c.mp3",
    5: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_111950_63befa3a-4872-4d37-9a1a-50c747a2b6cc.mp3",
    6: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_111950_36addf76-4e5a-4e70-a2d3-d6aed0c8a714.mp3",
    7: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_112010_a3c40479-4f58-4a7a-abd4-a860f70cc613.mp3",
    8: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_112010_93c45a43-3d2a-4ace-aafa-c0b63081bddc.mp3",
    9: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_112119_9ea8eb0a-c546-487b-a2f2-16aa06587f88.mp3",
    10: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_112010_6f845752-5f9a-42c8-bdd9-b8a4ac3cc83c.mp3",
    11: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_112010_1fd6d749-56e9-4738-bf53-8d2a1cbb780f.mp3",
    12: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_112010_22170788-ad31-43c9-8423-02afc57ee2f7.mp3",
    13: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_112024_bde14d03-a6c5-48dc-af3d-a1a2840de261.mp3",
    14: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_112024_1d50f1ad-4644-4dc0-82c2-be1008d176a3.mp3",
    15: "https://d8j0ntlcm91z4.cloudfront.net/user_35MJ2aWMmEoqYSm4FasjQsplt4C/hf_20260908_112024_fc029561-9d24-4cbb-81ec-d7970f640085.mp3",
}

OUTPUT.mkdir(parents=True, exist_ok=True)
ffmpeg = shutil.which("ffmpeg")
ffprobe = shutil.which("ffprobe")
if not ffmpeg or not ffprobe:
    raise RuntimeError("ffmpeg and ffprobe are required")

for index, url in URLS.items():
    mp3 = OUTPUT / f"take{index:02d}.mp3"
    wav = OUTPUT / f"take{index:02d}.wav"
    if not url.startswith("https://d8j0ntlcm91z4.cloudfront.net/"):
        raise ValueError("Unexpected narration asset URL")
    with urllib.request.urlopen(url) as response:  # noqa: S310 - exact HTTPS host checked above
        mp3.write_bytes(response.read())
    subprocess.run(  # noqa: S603 - fixed executable and arguments
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(mp3),
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(wav),
        ],
        check=True,
    )

for wav in sorted(OUTPUT.glob("take??.wav")):
    duration = subprocess.check_output(  # noqa: S603 - fixed executable and arguments
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(wav),
        ],
        text=True,
    ).strip()
    print(wav.name, duration)
