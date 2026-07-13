<!-- GAP-022:COMPLETED — 14 of 16 done. -->
# hoi4_audio_researcher — Platform-Agnostic Checklist

**Purpose:** Research licensed/public-domain audio for HOI4 mod music and sound cues.

## Checklist
- [ ] Audio is public domain, CC-licensed, or used with permission
- [ ] Source URL and license are documented
- [ ] Audio converted to OGG Vorbis format (HOI4 requirement)
- [ ] Bitrate appropriate: 128-192kbps for music, 64-128kbps for sound effects
- [ ] Audio registered in `music/` or `sound/` station definitions
- [ ] No copyrighted commercial music without explicit license
- [ ] Audio fits the mod's era (pre-1950 music for WWII setting)

## Output Format
```
## Audio Research: <track_name>
### Source: [URL]
### License: [type]
### Format: OGG | MP3 → needs conversion
### Duration: MM:SS
### Usage: music track | sound cue | event SFX
```
