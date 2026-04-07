#!/usr/bin/env python3
import sys
import subprocess
import json
import os

# ================= FPS PATCH ================= #
def patch_atom(atom_name, data, scale_factor=0.5):
    count = 0
    start = 0
    atom_bytes = atom_name.encode('utf-8')

    while True:
        found = data.find(atom_bytes, start)
        if found == -1:
            break

        header_offset = found - 4
        if header_offset < 0:
            start = found + 4
            continue

        box_size = int.from_bytes(data[header_offset:header_offset+4], 'big')
        if box_size < 8:
            start = found + 4
            continue

        version = data[header_offset + 8]

        if version == 0:
            timescale_offset = header_offset + 20
            duration_offset = header_offset + 24
            if duration_offset + 4 > header_offset + box_size:
                start = found + 4
                continue
            old_timescale = int.from_bytes(data[timescale_offset:timescale_offset+4], 'big')
            old_duration = int.from_bytes(data[duration_offset:duration_offset+4], 'big')
            new_timescale = int(old_timescale * scale_factor)
            new_duration = int(old_duration * scale_factor)
            data[timescale_offset:timescale_offset+4] = new_timescale.to_bytes(4, 'big')
            data[duration_offset:duration_offset+4] = new_duration.to_bytes(4, 'big')
            print(f"  Patched {atom_name}: timescale {old_timescale}->{new_timescale}, duration {old_duration}->{new_duration}")
            count += 1

        elif version == 1:
            timescale_offset = header_offset + 28
            duration_offset = header_offset + 32
            if duration_offset + 8 > header_offset + box_size:
                start = found + 4
                continue
            old_timescale = int.from_bytes(data[timescale_offset:timescale_offset+4], 'big')
            old_duration = int.from_bytes(data[duration_offset:duration_offset+8], 'big')
            new_timescale = int(old_timescale * scale_factor)
            new_duration = int(old_duration * scale_factor)
            data[timescale_offset:timescale_offset+4] = new_timescale.to_bytes(4, 'big')
            data[duration_offset:duration_offset+8] = new_duration.to_bytes(8, 'big')
            print(f"  Patched {atom_name}: timescale {old_timescale}->{new_timescale}, duration {old_duration}->{new_duration}")
            count += 1
        else:
            print(f"  Skipping {atom_name} unknown version {version}")

        start = found + 4
    return count

def patch_fps(input_filename, output_filename, scale_factor=0.5):
    with open(input_filename, 'rb') as f:
        data = bytearray(f.read())
    patched_mvhd = patch_atom("mvhd", data, scale_factor)
    patched_mdhd = patch_atom("mdhd", data, scale_factor)
    with open(output_filename, 'wb') as f:
        f.write(data)
    print(f"  Total atoms patched: {patched_mvhd + patched_mdhd}")

# ================= VIDEO INFO ================= #
def get_video_info(filename):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "json", filename
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception("FFmpeg/FFprobe not found! Run: pkg install ffmpeg")
    data = json.loads(result.stdout)
    stream = data['streams'][0]
    width = int(stream['width'])
    height = int(stream['height'])
    fps_fraction = stream['r_frame_rate']
    num, den = map(int, fps_fraction.split('/'))
    fps = round(num / den)
    return width, height, fps

# ================= SHARPEN + DOWNSCALE ================= #
def process_video(input_filename, output_filename):
    width, height, fps = get_video_info(input_filename)
    print(f"\n  Detected resolution: {width}x{height}")
    print(f"  Detected FPS: {fps}")

    filters = []

    # Downscale if higher than 1080p
    if height > 1080 or width > 1920:
        print(f"  Resolution > 1080p — downscaling to 1080p...")
        filters.append("scale=1920:1080:flags=lanczos")
    else:
        print(f"  Resolution is 1080p or lower — keeping original size.")

    # Always sharpen
    filters.append("unsharp=5:5:1.0:5:5:0.0")
    print(f"  Applying sharpening filter...")

    filter_str = ",".join(filters)

    cmd = [
        "ffmpeg", "-i", input_filename,
        "-vf", filter_str,
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "fast",
        "-c:a", "copy",
        "-y", output_filename
    ]

    print(f"\n  Processing video (this may take a moment)...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg error:\n{result.stderr}")
    print(f"  Video processed and saved!")

# ================= MAIN ================= #
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("\nUsage: python patcher.py input.mp4 output.mp4 [scale_factor]")
        print("Example: python patcher.py input.mp4 output.mp4 0.5\n")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    factor = 0.5

    if len(sys.argv) > 3:
        try:
            factor = float(sys.argv[3])
        except ValueError:
            print("Invalid scale factor. Using default 0.5x.")

    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    print("\n=============================")
    print("   JV-60FPS PATCHER TOOL")
    print("=============================")

    # Step 1: Sharpen + downscale
    temp_file = input_file + "_temp.mp4"
    print("\n[1/2] Processing resolution & sharpness...")
    try:
        process_video(input_file, temp_file)
    except Exception as e:
        print(f"\nFFmpeg not available: {e}")
        print("Skipping resolution/sharpen step...")
        temp_file = input_file

    # Step 2: Patch FPS metadata
    print(f"\n[2/2] Patching FPS metadata (scale: {factor}x)...")
    patch_fps(temp_file, output_file, scale_factor=factor)

    # Cleanup temp file
    if temp_file != input_file and os.path.exists(temp_file):
        os.remove(temp_file)

    print(f"\n✅ Done! Output saved to: {output_file}")
    print("=============================\n")
