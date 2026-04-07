#!/usr/bin/env python3
import sys

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

            print(f"Patched {atom_name} at offset {header_offset}: timescale {old_timescale}->{new_timescale}, duration {old_duration}->{new_duration}")
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

            print(f"Patched {atom_name} at offset {header_offset}: timescale {old_timescale}->{new_timescale}, duration {old_duration}->{new_duration}")
            count += 1
        else:
            print(f"Found {atom_name} at offset {header_offset} with unknown version {version}; skipping.")

        start = found + 4

    return count

def patch_mp4(input_filename, output_filename, scale_factor=0.5):
    print(f"Scale factor: {scale_factor}x")

    with open(input_filename, 'rb') as f:
        data = bytearray(f.read())

    patched_mvhd = patch_atom("mvhd", data, scale_factor)
    patched_mdhd = patch_atom("mdhd", data, scale_factor)

    total_patched = patched_mvhd + patched_mdhd
    print(f"\nTotal patched atoms: {total_patched}")

    with open(output_filename, 'wb') as f:
        f.write(data)

    print(f"Patched file saved to: {output_filename}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python patcher.py input.mp4 output.mp4 [scale_factor]")
        print("Example (0.5x): python patcher.py input.mp4 output.mp4 0.5")
        print("Example (2x):   python patcher.py input.mp4 output.mp4 2.0")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    factor = 0.5  # default is 0.5x

    if len(sys.argv) > 3:
        try:
            factor = float(sys.argv[3])
        except ValueError:
            print("Invalid scale factor. Using default 0.5x.")

    patch_mp4(input_file, output_file, scale_factor=factor)
