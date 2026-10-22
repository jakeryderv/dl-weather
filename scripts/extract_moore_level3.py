"""Extract the inventoried Moore Level III window from NOAA's daily .tar.Z.

Run from the project root with Python 3.12+; requires the system uncompress
command. Writes original product bytes, a SHA-256 manifest, and an independent
comparison against NOAA's previously saved timestamp inventory.
"""

import csv
import hashlib
import json
import re
import subprocess
import tarfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data/inventories/ktlx-level3-20130520"
RAW = ROOT / "data/raw/nexrad-level3/KTLX/20130520"
ARCHIVE = RAW / "NWS_NEXRAD_NXL3_KTLX_20130520000000_20130520235959.tar.Z"
PRODUCTS = {"N0Q", "N0U", "N0S", "N0C", "N0X"}
START = datetime(2013, 5, 20, 18, tzinfo=UTC)
END = datetime(2013, 5, 20, 22, tzinfo=UTC)
NAME = re.compile(
    r"[A-Z0-9]{4}_[A-Z0-9]{6}_(?P<product>[A-Z0-9]{3})TLX_"
    r"(?P<stamp>\d{12}(?:\d{2})?)"
)


def main():
    records = []
    seen = set()
    total_members = 0
    process = subprocess.Popen(
        ["uncompress", "-c", str(ARCHIVE)], stdout=subprocess.PIPE
    )
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            for member in archive:
                total_members += 1
                if not member.isfile():
                    continue
                match = NAME.fullmatch(member.name)
                if match is None or match["product"] not in PRODUCTS:
                    continue
                stamp = match["stamp"]
                time = datetime.strptime(
                    stamp, "%Y%m%d%H%M" if len(stamp) == 12 else "%Y%m%d%H%M%S"
                ).replace(tzinfo=UTC)
                if not START <= time <= END:
                    continue
                if member.name in seen:
                    raise ValueError(
                        f"Duplicate selected archive member: {member.name}"
                    )
                seen.add(member.name)
                stream = archive.extractfile(member)
                data = stream.read()
                if len(data) != member.size:
                    raise ValueError(f"Truncated member: {member.name}")
                destination = RAW / "selected" / match["product"] / member.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                records.append(
                    {
                        "station": "KTLX",
                        "product": match["product"],
                        "filename": member.name,
                        "filename_time_utc": time.isoformat(),
                        "filename_time_precision": "minute"
                        if len(stamp) == 12
                        else "second",
                        "size_bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "local_path": str(destination.relative_to(ROOT)),
                    }
                )
        # Drain tar padding so uncompress reaches EOF and validates the full stream.
        while process.stdout.read(1024 * 1024):
            pass
        process.wait()
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
        returncode = process.wait()
    if returncode:
        raise RuntimeError(f"Archive decompression failed: {returncode}")
    records.sort(key=lambda r: (r["filename_time_utc"], r["product"]))
    if not records:
        raise ValueError("No selected product files found")
    with (INVENTORY / "file-manifest.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    with (INVENTORY / "window.csv").open() as source:
        expected = {
            (r["product"], r["timestamp_utc_minute"]) for r in csv.DictReader(source)
        }
    actual = {
        (
            r["product"],
            datetime.fromisoformat(r["filename_time_utc"]).strftime("%Y-%m-%dT%H:%MZ"),
        )
        for r in records
    }
    summary = {
        "status": "matched_inventory" if actual == expected else "inventory_difference",
        "archive_members_scanned": total_members,
        "selected_files": len(records),
        "selected_bytes": sum(r["size_bytes"] for r in records),
        "product_counts": dict(sorted(Counter(r["product"] for r in records).items())),
        "missing_inventory_minutes": sorted(expected - actual),
        "extra_archive_minutes": sorted(actual - expected),
        "scope": "Whole radar product files; no geographic crop or resampling",
    }
    (INVENTORY / "extraction-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
