#!/usr/bin/env python3
"""Collect the ESP-IDF build output into a static web flasher site.

Reads build/flasher_args.json, copies each flash image into <out>/firmware/,
writes <out>/firmware/manifest.json for the web page, creates a merged image
(flash with `esptool write-flash 0x0 merged.bin`) and copies the web page files.
"""

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, default=Path('build'))
    parser.add_argument('--web-dir', type=Path, default=Path('web'))
    parser.add_argument('--out-dir', type=Path, default=Path('_site'))
    parser.add_argument('--version', default='local')
    args = parser.parse_args()

    flasher_args = json.loads((args.build_dir / 'flasher_args.json').read_text())
    project = json.loads((args.build_dir / 'project_description.json').read_text())
    chip = flasher_args['extra_esptool_args']['chip']

    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    shutil.copytree(args.web_dir, args.out_dir)
    fw_dir = args.out_dir / 'firmware'
    fw_dir.mkdir()

    parts = []
    for offset, rel_path in sorted(flasher_args['flash_files'].items(), key=lambda kv: int(kv[0], 16)):
        src = args.build_dir / rel_path
        dst = fw_dir / Path(rel_path).name
        shutil.copyfile(src, dst)
        parts.append({'path': dst.name, 'offset': int(offset, 16), 'size': dst.stat().st_size})

    # Merged image starting at 0x0; gaps are filled with 0xFF (erased flash).
    merged_name = f'{project["project_name"]}-{chip}-merged.bin'
    end = max(p['offset'] + p['size'] for p in parts)
    merged = bytearray(b'\xff' * end)
    for p in parts:
        merged[p['offset']:p['offset'] + p['size']] = (fw_dir / p['path']).read_bytes()
    (fw_dir / merged_name).write_bytes(merged)

    manifest = {
        'name': project['project_name'],
        'version': args.version,
        'built': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'idf_version': project.get('git_revision', ''),
        'chip': chip,
        'flash_settings': flasher_args['flash_settings'],
        'parts': parts,
        'merged': {'path': merged_name, 'offset': 0, 'size': len(merged)},
    }
    (fw_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

    for p in parts:
        print(f'0x{p["offset"]:06x}  {p["size"]:>8}  {p["path"]}')
    print(f'merged    {len(merged):>8}  {merged_name}')
    print(f'site      {args.out_dir}')


if __name__ == '__main__':
    main()
