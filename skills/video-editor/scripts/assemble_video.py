#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Video Editor - Assemble intro (with title overlay) + scenes + BGM into final video.

Key fixes (2026-05-22):
1. concat_videos: replace xfade with fps-normalized concat filtergraph (avoids frame drops on mixed-framerate sources)
2. add_bgm: use atrim+duration=first instead of duration=first alone (avoids video truncation)
3. generate_title_overlay: fix undefined 'idx' variable bug
"""

import json
import subprocess
import sys
import argparse
from pathlib import Path
import shutil


def run_ffmpeg(args, label="ffmpeg"):
    cmd = ["ffmpeg", "-y"] + args
    print(f"[{label}] Running: {' '.join(cmd[:10])}...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"[{label}] STDERR:\n{result.stderr[-2000:]}")
        raise RuntimeError(f"{label} failed (exit {result.returncode})")
    return result


def has_audio_stream(filepath):
    """Check if a video file has an audio stream."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return "audio" in result.stdout.strip()


def get_video_duration(filepath):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return float(result.stdout.strip())


def generate_title_overlay(title, config, workspace):
    """Generate a title overlay PNG using PIL (precise text measurement + rounded rect bg).

    Returns path to the generated PNG file.
    """
    fontsize = config.get("font_size", 70)
    res = config.get("resolution", "720x1280")
    w = int(res.split("x")[0])
    h = int(res.split("x")[1])

    from PIL import Image, ImageDraw, ImageFont

    font_path = r"C:\Windows\Fonts\字魂241号-秋枫体.ttf"
    font = ImageFont.truetype(font_path, fontsize)

    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Measure full title width
    bbox = draw.textbbox((0, 0), title, font=font)
    text_width = bbox[2] - bbox[0]

    # Line breaking: if wider than video width, split at a natural separator
    lines = []
    if text_width > w:
        split_done = False
        for sep in ['\uff1a', '\uff0c', '\u3002', '\uff01', '\uff1f', '、', ' ']:
            idx = title.find(sep)
            if idx > 0:
                lines.append(title[:idx+1])
                lines.append(title[idx+1:])
                split_done = True
                break
        if not split_done:
            mid = int(len(title) * 0.6)
            lines.append(title[:mid])
            lines.append(title[mid:])
    else:
        lines.append(title)

    # Measure each line's actual rendered size
    line_metrics = []
    for line in lines:
        tmp_img = Image.new('L', (w, fontsize * 2), 0)
        tmp_draw = ImageDraw.Draw(tmp_img)
        tmp_draw.text((0, 0), line, fill=255, font=font)
        tmp_bbox = tmp_img.getbbox()
        if tmp_bbox:
            real_w = tmp_bbox[2] - tmp_bbox[0]
            real_h = tmp_bbox[3] - tmp_bbox[1]
        else:
            tb = tmp_draw.textbbox((0, 0), line, font=font)
            real_w = tb[2] - tb[0]
            real_h = tb[3] - tb[1]
        line_metrics.append((line, real_w, real_h))

    # Layout: center vertically in upper 1/3 of screen
    font_ascent, font_descent = font.getmetrics()
    LINE_GAP = int((font_ascent + font_descent) * 0.25)
    padding_y = int(fontsize * 0.6)
    radius = 20

    text_block_height = sum(m[2] for m in line_metrics) + (len(line_metrics) - 1) * LINE_GAP
    total_height = text_block_height + padding_y * 2
    y_center = int(h * 0.32)
    box_top = y_center - total_height // 2
    box_bottom = box_top + total_height

    draw.rounded_rectangle([0, box_top, w, box_bottom], radius=radius, fill=(0, 0, 0, 180))

    y_cursor = box_top + padding_y
    for line, real_w, real_h in line_metrics:
        x = (w - real_w) // 2
        draw.text((x, y_cursor), line, fill=(255, 255, 0, 255), font=font)
        y_cursor += real_h + LINE_GAP

    overlay_path = str(workspace / "_title_overlay.png")
    overlay.save(overlay_path)
    print(f"  Title overlay: {overlay_path} (box Y=[{box_top},{box_bottom}], h={total_height}px)")
    return overlay_path


def concat_videos(video_files, output_path, transition=0.5):
    """Concatenate multiple video files.

    Fixed (2026-05-22): Use fps-normalized filtergraph concat instead of xfade.
    This avoids frame drops when input videos have different framerates
    (e.g., intro=30fps, scenes=24fps).
    """
    if len(video_files) == 1:
        run_ffmpeg(["-i", video_files[0], "-c", "copy", output_path], label="concat_single")
        return output_path

    n = len(video_files)
    target_fps = 30
    target_w, target_h = 720, 1280

    # Step 1: Normalize each video to 30fps/720x1280 (re-encode to clean timestamps)
    normalized = []
    for i, f in enumerate(video_files):
        norm_path = str(Path(output_path).parent / f"_norm_{i}.mp4")
        has_audio = has_audio_stream(f)
        if has_audio:
            run_ffmpeg([
                "-i", f,
                "-vf", f"fps={target_fps},scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                norm_path
            ], label=f"norm_{i}")
        else:
            run_ffmpeg([
                "-i", f,
                "-vf", f"fps={target_fps},scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-an",
                norm_path
            ], label=f"norm_{i}")
        normalized.append(norm_path)

    # Step 2: Concat video (filtergraph with fps normalization per input)
    inputs = []
    for f in normalized:
        inputs.extend(["-i", f])

    # Build video concat filter: each input → fps=30 → concat
    # Use single concat with n=N for all inputs (not chained pairs)
    vf_parts = []
    for i in range(n):
        vf_parts.append(f"[{i}:v]fps=30,format=yuv420p[v{i}]")
    # Single concat filter with n=N for all normalized inputs
    concat_inputs = "][".join(f"v{i}" for i in range(n))
    vf_parts.append(f"[{concat_inputs}]concat=n={n}:v=1:a=0[vout]")

    video_concated = str(Path(output_path).with_suffix(".video.mp4"))
    run_ffmpeg(
        inputs + [
            "-filter_complex", ";".join(vf_parts),
            "-map", "[vout]",
            "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-g", "30", "-keyint_min", "30",
            video_concated
        ],
        label="concat_video"
    )

    # Step 3: Concat audio separately (clean timestamp concat demuxer)
    audio_concated = str(Path(output_path).with_suffix(".audio.aac"))
    audio_files = [f for f in normalized if has_audio_stream(f)]
    if audio_files:
        audio_list = str(Path(output_path).parent / "_audio_concat.txt")
        with open(audio_list, "w", encoding="utf-8") as cf:
            for ap in audio_files:
                p = str(ap).replace("\\", "/")
                cf.write(f"file '{p}'\n")
        run_ffmpeg([
            "-f", "concat", "-safe", "0", "-i", audio_list,
            "-c:a", "aac", "-b:a", "192k",
            audio_concated
        ], label="concat_audio")
        try:
            Path(audio_list).unlink(missing_ok=True)
        except:
            pass

    # Step 4: Merge clean video + clean audio
    run_ffmpeg([
        "-i", video_concated,
        "-i", audio_concated,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path
    ], label="merge_av")

    # Cleanup intermediate files
    for p in [video_concated, audio_concated]:
        try:
            Path(p).unlink(missing_ok=True)
        except:
            pass
    for f in normalized:
        try:
            Path(f).unlink(missing_ok=True)
        except:
            pass

    return output_path


def add_bgm(video_path, bgm_path, output_path, volume=0.35):
    """Add BGM to video.

    Fixed (2026-05-22): Use atrim=0:video_dur on BGM instead of duration=first alone.
    This ensures the output exactly matches the video duration, not shorter.
    """
    video_dur = get_video_duration(video_path)
    audio_exists = has_audio_stream(video_path)

    if audio_exists:
        # BGM: trim to video_dur + fade-out; mix with original audio (duration=first keeps original length)
        filter_complex = (
            f"[1:a]atrim=0:{video_dur},volume={volume},afade=t=out:st={video_dur - 2}:d=2[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first[aout]"
        )
    else:
        filter_complex = (
            f"[1:a]atrim=0:{video_dur},volume={volume},afade=t=out:st={video_dur - 2}:d=2,apad=whole_dur={video_dur}[aout]"
        )

    run_ffmpeg([
        "-i", video_path,
        "-i", bgm_path,
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        output_path
    ], label="add_bgm")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Video Editor - Assemble final video")
    parser.add_argument("--config", required=True, help="Path to config JSON")
    parser.add_argument("--workspace", default=".", help="Workspace directory for temp files")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    scenes = [Path(s) for s in config["scenes"]]
    bgm_path = config.get("bgm", "")
    title = config.get("title", "")
    intro_video = config.get("intro_video", "")
    bgm_vol = config.get("bgm_volume", 0.35)
    transition = config.get("scene_transition", 0.5)  # kept for config compat, hard-cut always used
    output = config.get("output", "final.mp4")

    res = config.get("resolution", "720x1280")
    w, h = res.split("x")

    parts = []

    # 1. Intro: normalize + overlay title PNG using PIL
    if intro_video and Path(intro_video).exists():
        intro_path = workspace / "_intro.mp4"
        intro_dur = get_video_duration(intro_video)
        intro_has_audio = has_audio_stream(intro_video)

        if title:
            print(f"[+] Generating title overlay with PIL...")
            overlay_png = generate_title_overlay(title, config, workspace)
            overlay_slash = overlay_png.replace("\\", "/")
            print(f"[+] Overlaying title '{title}' on intro video (PIL method)")

            if intro_has_audio:
                run_ffmpeg([
                    "-i", intro_video,
                    "-i", overlay_slash,
                    "-filter_complex",
                    f"[0:v]fps=30,scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[scaled];[scaled][1:v]overlay=x=0:y=0",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    intro_path
                ], label="intro")
            else:
                run_ffmpeg([
                    "-i", intro_video,
                    "-i", overlay_slash,
                    "-filter_complex",
                    f"[0:v]fps=30,scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[scaled];[scaled][1:v]overlay=x=0:y=0",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-an",
                    intro_path
                ], label="intro")
        else:
            vf = f"fps=30,scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
            if intro_has_audio:
                run_ffmpeg([
                    "-i", intro_video,
                    "-vf", vf,
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    intro_path
                ], label="intro")
            else:
                run_ffmpeg([
                    "-i", intro_video,
                    "-vf", vf,
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-an",
                    intro_path
                ], label="intro")

        parts.append(str(intro_path))
        print(f"[+] Intro video: {intro_dur}s ({Path(intro_video).name})")
        config["title_duration"] = intro_dur
    else:
        intro_dur = config.get("intro_duration", 3)
        intro_path = workspace / "_intro.mp4"
        run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d={intro_dur}:r=30",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            intro_path
        ], label="intro")
        parts.append(str(intro_path))
        print(f"[+] Intro: {intro_dur}s black")
        if title:
            print(f"[!] Warning: no intro_video set; title not overlaid")

    # 2. Scene videos
    for s in scenes:
        if not s.exists():
            print(f"[!] Scene not found: {s}")
            continue
        parts.append(str(s))
        print(f"[+] Scene: {s.name}")

    if len(parts) < 2:
        print("[!] Not enough parts to assemble")
        sys.exit(1)

    # 3. Concat (hard cut, fps-normalized)
    if len(parts) == 1:
        concat_path = parts[0]
    else:
        concat_path = str(workspace / "_concat.mp4")
        concat_videos(parts, concat_path, transition)
        print(f"[+] Concatenated {len(parts)} parts (hard cut, fps-normalized)")

    # 4. BGM
    if bgm_path and Path(bgm_path).exists():
        final = add_bgm(concat_path, bgm_path, str(workspace / output), bgm_vol)
        print(f"[+] BGM mixed at {int(bgm_vol * 100)}%")
    else:
        out_path = str(workspace / output)
        if concat_path != out_path:
            shutil.move(concat_path, out_path)
        final = out_path
        print("[i] No BGM")

    # 5. Verify
    final_path = Path(final)
    if not final_path.exists():
        print("[!] Final video missing!")
        sys.exit(1)

    dur = get_video_duration(final)
    size = final_path.stat().st_size
    print(f"\n{'=' * 50}")
    print(f"Done: {final_path.resolve()}")
    print(f"  Duration: {dur:.1f}s | Size: {size / 1024 / 1024:.1f} MB")
    print(f"{'=' * 50}")

    # 6. Cleanup temp files (NEVER delete source scene files)
    source_scenes = [str(s) for s in scenes]
    for p in parts:
        if p in source_scenes:
            continue
        try:
            Path(p).unlink(missing_ok=True)
        except:
            pass
    try:
        Path(concat_path).unlink(missing_ok=True)
    except:
        pass
    try:
        (workspace / "_title_overlay.png").unlink(missing_ok=True)
    except:
        pass


if __name__ == "__main__":
    main()
