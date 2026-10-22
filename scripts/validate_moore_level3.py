"""Validate five pilot files, then every selected original with MetPy.

Run in a Python environment containing MetPy and NumPy. This verifies binary
decoding and provenance alignment; it does not crop, regrid, normalize units,
or interpret tornado signatures. Native packed-code categories are retained.
"""

import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import metpy
import numpy as np
from metpy.io import Level3File

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data/inventories/ktlx-level3-20130520"
CODES = {"N0Q": 94, "N0U": 99, "N0S": 56, "N0C": 161, "N0X": 159}
TARGET = datetime(2013, 5, 20, 20, 10, tzinfo=UTC)


def utc(time):
    # NIDS times are UTC; MetPy returns naive UTC datetimes.
    return time.replace(tzinfo=UTC).isoformat()


def decode(row):
    path = ROOT / row["local_path"]
    data = path.read_bytes()
    if (
        len(data) != int(row["size_bytes"])
        or hashlib.sha256(data).hexdigest() != row["sha256"]
    ):
        raise ValueError(f"File checksum/size mismatch: {path}")
    product = row["product"]
    radar = Level3File(str(path))
    if radar.siteID != "TLX" or radar.header.code != CODES[product]:
        raise ValueError(f"Wrong radar/product: {path}")
    if abs(radar.lat - 35.333) > 0.002 or abs(radar.lon + 97.278) > 0.002:
        raise ValueError(f"Unexpected radar coordinates: {path}")
    time = radar.metadata["vol_time"].replace(tzinfo=UTC)
    filename_time = datetime.fromisoformat(row["filename_time_utc"])
    if time.strftime("%Y-%m-%dT%H:%M") != filename_time.strftime("%Y-%m-%dT%H:%M"):
        raise ValueError(f"Volume-start/filename time mismatch: {path}")
    packets = []
    for layer in radar.sym_block:
        for packet in layer:
            if "data" not in packet:
                continue
            packed = np.asarray(packet["data"])
            if packed.ndim != 2 or len(packet["start_az"]) != packed.shape[0]:
                raise ValueError(f"Invalid radial array: {path}")
            values = radar.map_data(packed)
            finite = values[np.isfinite(values)]
            packets.append(
                {
                    "shape": list(values.shape),
                    "finite_cells": int(finite.size),
                    "nonfinite_cells": int(values.size - finite.size),
                    "mapped_min": float(finite.min()) if finite.size else None,
                    "mapped_max": float(finite.max()) if finite.size else None,
                    "reader_units": getattr(radar.map_data, "units", None),
                    "packed_code_counts": {
                        str(int(code)): int(count)
                        for code, count in zip(
                            *np.unique(packed, return_counts=True), strict=True
                        )
                    },
                }
            )
    if not packets:
        raise ValueError(f"No radial data packet: {path}")
    return {
        "filename": row["filename"],
        "product": product,
        "status": "decoded",
        "station": radar.siteID,
        "product_code": radar.header.code,
        "product_name": radar.product_name,
        "latitude": radar.lat,
        "longitude": radar.lon,
        "message_time_utc": utc(radar.metadata["msg_time"]),
        "volume_start_utc": utc(radar.metadata["vol_time"]),
        "product_generation_utc": utc(radar.metadata["prod_time"]),
        "elevation_degrees": radar.metadata.get("el_angle"),
        "vcp": radar.prod_desc.vcp,
        "operating_mode": radar.prod_desc.op_mode,
        "packets": packets,
    }


def main():
    with (INVENTORY / "file-manifest.csv").open() as source:
        rows = list(csv.DictReader(source))
    pilot_rows = [
        min(
            (r for r in rows if r["product"] == product),
            key=lambda r: abs(datetime.fromisoformat(r["filename_time_utc"]) - TARGET),
        )
        for product in CODES
    ]
    pilot = [decode(row) for row in pilot_rows]
    (INVENTORY / "pilot-decode.json").write_text(json.dumps(pilot, indent=2) + "\n")
    print("Five-product pilot passed; validating the full selection.", flush=True)
    results = []
    failures = []
    for row in rows:
        try:
            results.append(decode(row))
        except (
            OSError,
            ValueError,
            EOFError,
            IndexError,
            KeyError,
            TypeError,
        ) as error:
            failures.append({"filename": row["filename"], "error": str(error)})
    with (INVENTORY / "decode-manifest.jsonl").open("w") as output:
        for result in results:
            output.write(json.dumps(result) + "\n")
    summary = {
        "decoder": "MetPy Level3File",
        "decoder_version": metpy.__version__,
        "pilot_files": len(pilot),
        "selected_files": len(rows),
        "decoded_files": len(results),
        "decoded_product_counts": dict(
            sorted(Counter(r["product"] for r in results).items())
        ),
        "failures": failures,
        "status": "passed" if not failures else "failed",
        "checks": [
            "SHA-256 and size",
            "KTLX station and coordinates",
            "product code",
            "volume-start/filename UTC minute",
            "radial array dimensions",
            "packed-code mapping",
        ],
        "limitations": [
            "Whole radar products retained; no geographic cropping or gridding performed.",
            "Message, volume-start and product-generation timestamps are distinct and retained.",
            "No unit conversion or velocity dealiasing performed.",
            "MetPy can map missing and range-folded codes to the same NaN; packed-code counts retained.",
            "Legacy N0S uses categorical threshold bins; no continuous-value reconstruction performed.",
            "Decode success does not establish tornado signatures or exact per-gate observation times.",
        ],
    }
    (INVENTORY / "decode-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
