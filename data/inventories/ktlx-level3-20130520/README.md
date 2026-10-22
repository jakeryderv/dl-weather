# Moore 2013: KTLX Level III acquisition

**Complete:** 258 original files acquired and successfully decoded with MetPy 1.7.1.

NOAA NCEI inventory for May 20, 2013, 18:00–22:00 UTC (1–5 PM CDT), inclusive.

| Product | Description | Selected files | Bytes | Tornado-period records (19:56–20:35 UTC) |
|---|---|---:|---:|---:|
| N0Q | Digital base reflectivity | 53 | 1,253,192 | 9 |
| N0U | Digital base velocity | 51 | 3,018,784 | 9 |
| N0S | Storm-relative velocity | 50 | 961,110 | 9 |
| N0C | Correlation coefficient | 52 | 4,114,316 | 9 |
| N0X | Differential reflectivity | 52 | 4,356,024 | 9 |

The selected files total **13,703,426 bytes** (13.7 MB), across 53 distinct UTC minutes. All five products have entries within the tornado period. Their filenames match every saved inventory record, with no missing or additional minutes. Decoded operating modes and VCP numbers also match the inventory.

## Source and cache

NOAA links Google Cloud as a complete historical Level III archive through its Open Data Dissemination program. KTLX's station/day is packaged as one `.tar.Z`, so the **780,915,569-byte archive** was downloaded once. The original archive remains cached; only the selected products and window were extracted. No NCEI order or notification email was needed.

The download was pinned to object generation `1558552549295129`. Its size and MD5 match cloud object metadata, and its local SHA-256 is recorded in `archive-source.json`. Every extracted file has its own size, SHA-256, and path in `file-manifest.csv`.

Local originals: `data/raw/nexrad-level3/KTLX/20130520/selected/<PRODUCT>/`. The raw cache is ignored by Git. The source bytes are unchanged.

## Validation and timestamps

The five-product pilot used the volume beginning at 20:08:11 UTC. It passed, then all 258 files passed binary decoding, SHA-256/size checks, station/product checks, volume-start/filename minute alignment, and radial-array/code-mapping checks.

The inventory and filenames identify the **volume-start minute**. Binary headers retain the actual volume-start second, product-generation time, and message time separately. In these files, volume start is 0–59 seconds after the filename minute; message time is 21–208 seconds after it. Message-generation time is not the observation time.

Cadences differ and some products have longer intervals. Do not force products onto identical times or label every longer interval a missing scan without checking the operating mode and archive contents.

This is acquisition and decoder validation. Products retain whole radar coverage; no Moore/Oklahoma crop, regridding, NetCDF export, velocity dealiasing, or meteorological interpretation has been performed. MetPy can map missing and range-folded codes to the same NaN; packed-code counts are recorded, and original bytes preserve the distinction. N0S uses categorical threshold bins. No unit normalization is performed.

## Artifacts

- `archive-source.json`: official source reference, object metadata, pinned download URL, and archive checksum verification.
- `file-manifest.csv`: exact filenames, sizes, SHA-256 hashes, and cache paths.
- `extraction-summary.json`: actual archive members compared with the availability inventory.
- `pilot-decode.json`: sample metadata and array statistics for all five products.
- `decode-manifest.jsonl`: native header times and decode statistics for every file.
- `decode-summary.json`: validation status and scope limits.
- `decoder-requirements.txt`: exact packages in the temporary decoder environment.
- `*-day.csv`, `window.csv`, and `summary.json`: source inventory and current acquisition state.

## Reproduce from the cached archive

Requires the system `uncompress` command. Run from the project root:

```sh
python3 scripts/extract_moore_level3.py
uv run --no-project --python 3.12 --with-requirements data/inventories/ktlx-level3-20130520/decoder-requirements.txt python scripts/validate_moore_level3.py
```

Project dependencies were not changed for this acquisition. MetPy was used in a temporary environment. `archive-source.json` preserves the pinned source URL for downloading the original archive again.

## Sources

- [NOAA official historical cloud archive links](https://www.ncei.noaa.gov/products/ncei-data-noaa-open-dissemination-program)
- [NOAA inventory results](https://www.ncei.noaa.gov/nexradinv/displaygraphs.jsp?mm=05&dd=20&yyyy=2013&product=AML3N0Q&product=CEL3N0U&product=CNL3N0S&product=DEL3N0C&product=DAL3N0X&id=KTLX)
- [NWS Moore event summary](https://www.weather.gov/oun/events-20130520)
- [MetPy Level III reader](https://unidata.github.io/MetPy/latest/api/generated/metpy.io.Level3File.html)
