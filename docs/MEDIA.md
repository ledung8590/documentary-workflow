# Archival media and maps (stage 6: photos + video clips built; maps planned)

## Commands
- `doc.py media JOB search "query" --tag T [--kind photo|video] [--n 8] [--sources commons,openverse,dvids]`
  - Licence-gated results.
  - 500 px previews and a contact sheet at `qa/media-T.jpg`.
  - Flags: re-photos of museum displays, low resolution, vertical video.
- `doc.py media JOB pick SLOT T K --caption "what it really shows" [--in S --dur S]`
  - Downloads the full file only now: 1920 px photo, or a video range cut from the 1080p/720p Commons transcode.
  - Sets `src`/`kind`/`credit` on the timeline clip and appends a `LICENSES.md` row.
- The agent finds the media itself, including Vietnamese and Ukrainian/Russian war material. Google Images' CC filter is only a hint; the licence is read from the origin file page.

## Rate limits (Wikimedia)
- `upload.wikimedia.org` blocks bursts for 600 s, and is much stricter for clients whose User-Agent has no contact info.
- The scripts:
  - browse at 500 px;
  - use only standard thumbnail widths (500/1280/1920);
  - pause 3 s between files;
  - stop instead of retrying when blocked.
- Set `WIKIMEDIA_CONTACT` (the user's chosen email or URL) in the user environment so the User-Agent complies with Wikimedia's policy.
- Openverse anonymous access is intermittent (HTTP 401/504); Commons is the primary source.

## Allowed licences
Public domain (incl. US federal government works, expired copyright), CC0, CC BY, CC BY-SA (credit + same licence for the file, fine in a video), files the user supplies with rights. **Rejected:** any NC or ND, "editorial use only", unknown/unclear, IWM Non-Commercial Licence, Getty/AP/Alamy/British Pathé/Reuters without a paid licence, frames ripped from other YouTube videos. Vietnamese state archive photos (TTXVN, TTLTQG III, Báo QĐND) are **not** automatically free: use them only where the specific file on Wikimedia Commons carries a valid PD/CC tag, or with the user's licence.

Per file, `LICENSES.md` row: file, source page URL, author, licence + URL, attribution line, download date, what the image actually shows. On screen: short credit line bottom-right (as in the reference). Description: `credits.txt`.

## Sources (APIs, no scraping of HTML where an API exists)
| source | good for | API | licence notes |
|---|---|---|---|
| Wikimedia Commons | everything; best metadata | `commons.wikimedia.org/w/api.php` (`prop=imageinfo&iiprop=url|extmetadata`) | read `LicenseShortName`, `Artist`, `UsageTerms` per file |
| US National Archives (NARA) | WWII, Korea, Vietnam (US side), film reels | `catalog.archives.gov/api/v2` (free key) | most federal records PD; check "use restrictions" |
| Library of Congress | photos, maps, posters | `loc.gov/photos/?fo=json` | "No known restrictions" ≠ always; read rights field |
| DVIDS / US DoD | modern US military | `api.dvidshub.net` (free key) | PD (US gov) |
| Internet Archive | PD newsreels, Prelinger | `archive.org/advancedsearch.php` | verify per item; many uploads are not PD |
| Openverse | meta-search CC/PD | `api.openverse.org/v1/images` | always confirm on the origin page |
| Bundesarchiv (via Commons) | German WWII | Commons | CC BY-SA 3.0 DE, credit "Bundesarchiv, Bild …" |
| Australian War Memorial | Pacific, Korea, Vietnam | collection search | many PD (pre-1955 photos); check each |
| Europeana | European archives | `api.europeana.eu` (free key) | filter `reusability=open` |

Video clips: NARA, Internet Archive, Commons video. Download only the needed range with ffmpeg (`-ss/-t`), keep the source ID in the file name.

## Maps
- Terrain: AWS Terrain Tiles (Mapzen, SRTM etc.; attribution list in their README) or Copernicus DEM GLO-30 (free, attribution "© DLR/Airbus, Copernicus"). Hillshade rendered locally.
- Satellite: **Sentinel-2 cloudless 2016 by EOX (CC BY 4.0)**. Later EOX years (2018+) are CC BY-NC-SA → not for monetized videos. Copernicus Sentinel-2 raw scenes are free with attribution.
- Vector: Natural Earth (PD) for countries/coasts; OpenStreetMap (ODbL, "© OpenStreetMap contributors") for roads/rivers/places.
- Historical positions, front lines, arrows: drawn by us, labelled schematic/"minh hoạ" when not exact. Vietnamese maps must show Hoàng Sa and Trường Sa as Vietnam's.
- Map moves: render a large still (e.g. 4096 px) then animate crop/zoom in the compositor; annotations on the overlay track so they stay editable.
