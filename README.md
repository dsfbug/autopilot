<div align="center">

# AUTOPILOT

**Fully automated short-form content pipeline**

Discovers top Twitch clips, scores and ranks them, reformats for vertical video,
<br>adds subtitles and overlays, and publishes across 4 platforms — every day, zero manual input.

<br>

<table>
<tr>
<td align="center"><h2>2M+</h2>YouTube views<br><sub>first 30 days</sub></td>
<td align="center"><h2>700K</h2>Instagram views<br><sub>first 3 days</sub></td>
<td align="center"><h2>538</h2>videos uploaded<br><sub>fully automated</sub></td>
<td align="center"><h2>4</h2>platforms<br><sub>simultaneous cross-post</sub></td>
</tr>
</table>

<br>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)
![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?style=flat-square&logo=ffmpeg&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Whisper](https://img.shields.io/badge/Whisper-412991?style=flat-square&logo=openai&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-8E75B2?style=flat-square&logo=google&logoColor=white)

</div>

---

### Dashboard

Pipeline controls, autopilot triggers, and real-time clip recommendations.

<img src="docs/screenshots/dashboard.png" alt="Dashboard" width="100%">

### Studio

Review, approve, and edit clips before they go out. Each card shows the thumbnail, score, streamer, and platform targets.

<img src="docs/screenshots/studio.png" alt="Studio" width="100%">

### Analytics

Track total views, best posting windows, and per-video performance. Scoring weights retrain automatically based on what actually gets views.

<img src="docs/screenshots/analytics.png" alt="Analytics" width="100%">

---

## How it works

Every morning at 7am, the pipeline runs unattended:

**Discover** — Pulls hundreds of clips from the Twitch Helix API, filtered by game and streamer. Deduplicates against a history of 14K+ previously seen clips.

**Score + Screen** — Each clip is ranked by view velocity, duration, audio quality, and title keywords. Scoring weights are trained from actual upload performance — the system learns what gets views on each channel. Top candidates are then screened by Gemini for content quality.

**Process** — Clips are converted from 16:9 → 9:16 vertical format. The facecam is auto-detected and cropped to fill the top band. Gameplay is zoomed and repositioned with the HUD overlaid at the bottom. Each streamer has a calibrated layout profile (55+ profiles stored). Whisper generates word-level subtitles with karaoke-style highlighting. FFmpeg composites everything: subtitles, hook text, progress bar, and platform-specific CTA animations.

**Publish** — Clips are uploaded to YouTube with `publishAt` scheduling across peak hours, then cross-posted to Instagram, TikTok, and Facebook with per-platform throttling. Daily highlight compilations are assembled automatically with transition cards between clips.

**Learn** — After upload, the system tracks views and engagement. Scoring weights are periodically retrained so clip selection improves over time. The analytics dashboard surfaces best posting windows and top-performing streamer segments.

## Daily schedule

| Time | What happens |
|:---|:---|
| 7:00 AM | Fetch clips from Twitch, score and approve top candidates |
| 7:05 AM | Format, subtitle, and burn overlays (3 clips processed in parallel) |
| 7:35 AM | Upload 7 Shorts to YouTube, scheduled across peak hours |
| 7:40 AM | Build and upload daily highlight compilation |
| 8:00 AM | Marathon channel runs the same pipeline independently |
| 9:00 AM | Cross-post top performers to Instagram, TikTok, Facebook |
| Every 5 min | Release executor publishes any uploads whose scheduled time has arrived |

Runs via launchd cron on macOS. The web dashboard is for reviewing clips and monitoring performance — not required for daily operation.

## Stack

| | |
|:---|:---|
| **Pipeline + API** | Python, FastAPI, SSE streaming |
| **Video** | FFmpeg via imageio-ffmpeg (libass, loudnorm, concat demuxer) |
| **Speech-to-text** | Whisper with word-level alignment |
| **Content AI** | Gemini for screening, titles, descriptions, captions |
| **Database** | SQLite in WAL mode with auto-migration |
| **Frontend** | React, TypeScript, shadcn/ui, Vite |
| **Downloads** | yt-dlp |
| **Platforms** | YouTube Data API v3, Instagram Graph API, TikTok, Facebook Reels |

## Setup

## Plug-and-play setup (single YouTube channel)

Tested path for running this yourself at zero cost on one channel:

1. **Google account**: the account that owns the YouTube channel must have
   2-Step Verification turned on - Google Cloud blocks console access without it
   (enforced since May 2026). Turn it on at myaccount.google.com/security.
2. **Google Cloud project**: in console.cloud.google.com (signed in as the
   channel account), create a project, then enable **YouTube Data API v3**
   (APIs & Services > Library).
3. **OAuth consent screen**: APIs & Services > OAuth consent screen. If the
   console offers an **Audience: Personal** mode, pick it - it needs no
   verification, shows no unverified-app warning, and its tokens do not expire
   after 7 days. Otherwise choose External; in **Testing** status add the
   channel account as a test user and re-run `python -m clipper auth` weekly
   (testing-mode refresh tokens expire in 7 days), or publish the app to
   production status to avoid that.
4. **OAuth client**: APIs & Services > Credentials > Create Credentials >
   OAuth client ID > application type **Desktop app**. Download the JSON and
   save it as `client_secrets.json` in the project root.
5. **Authenticate**: `python -m clipper auth` opens a browser on the machine.
   On a headless server, use `python scripts/auth_headless.py` instead and
   paste the final redirect URL back.
6. **Uploads default to unlisted** (see `config.yaml`: `auto_upload: false`,
   `privacy: unlisted`, `default_privacy: unlisted`). Review clips in the
   Studio queue, and flip privacy only when you actually want public posts.
   Uploads from unverified API projects are no longer locked private per
   YouTube's November 2026 API revision-history change, but verify with one
   unlisted test upload before relying on any scheduled public posting.
7. **Free quota**: the default API quota allows ~100 uploads/day - plenty for
   a daily Shorts batch. Whisper runs locally (CPU-friendly `small` model is
   the default here). Gemini screening is optional; without a key it falls
   back to a local Ollama model if installed, or can be disabled
   (`pre_llm_screen: false`).


```bash
pip install -r requirements.txt
cp .env.example .env            # Twitch, Meta, TikTok, Gemini API keys
python -m clipper auth           # OAuth setup for each platform
python -m clipper serve          # API + web UI → localhost:8420
```

All behavior is driven by `config.yaml` — streamer lists, scoring thresholds, daily caps, posting schedules, layout preferences. No secrets in config; credentials live in `.env` and OAuth token files.

### Upload-only mode (no token file)

If you only need uploads, you can skip the broad-scope consent. Authorize once with the `youtube.upload` scope, then point the uploader at three files that each hold one value:

    export CLIPPER_YT_CLIENT_ID_FILE=/path/client_id
    export CLIPPER_YT_CLIENT_SECRET_FILE=/path/client_secret
    export CLIPPER_YT_REFRESH_TOKEN_FILE=/path/refresh_token

The uploader then mints an access token in memory and never writes `.clipper_token.json`. This mode cannot read the channel, change an existing video or fetch analytics. Keep `privacy: unlisted` until you have reviewed a clip.
