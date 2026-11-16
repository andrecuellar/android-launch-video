# Store images and Play metadata

## Play screenshots

- Up to 8, 1080x1920 (9:16), 24-bit PNG without alpha, or JPEG.
- Source: clean frames of the 9:16 film, or real app screens with a headline above them.
- `node video/scripts/store_shots.mjs ...` renders them with a single `seek(t)` per frame, so there
  is no motion blur (the final render averages subframes; a still must not).
- `python3 video/scripts/png_srgb.py ...` rewrites each PNG as 24-bit sRGB without alpha and without
  color-profile chunks that some store pipelines reject.
- The first screenshot states the value proposition in one line. Each next one shows one feature,
  one headline, one screen.
- Same rules as the film: real app screens, believable data, no other app on screen, no personal
  data, clean status bar.

## Feature graphic

- 1024x500, no alpha.
- Brand, one line and the phone.
- Keep the center (about x 362 to 662) free of anything important: Play overlays the video play
  button there when the listing has a promo video.

## Social stills

- 1080x1920.
- Nothing important in the top 14 %, the bottom 20 % or the last ~120 px on the right: the
  Reels, Shorts and TikTok UI covers those bands.

## Play metadata rules

They apply to the listing texts, the screenshots and the video:

- No "#1", "best", "top", rankings or awards unless the app really holds them and the listing can
  show it.
- No testimonials or user quotes.
- No calls to download or install ("download now"), no prices or offers with dates.
- No repeated keywords or keyword stuffing.
- Nothing the app does not do: every screen and claim must exist in the version that is live.

## Listing texts to deliver with the video

- Short description (80 characters) and full description, in the listing's language, with
  correct diacritics.
- The video goes to YouTube (public or unlisted, ads off) and its link to the listing; whoever
  owns the Play listing pastes it.
- Music credits: track title, author and "Mixkit" with the license link, wherever the platform
  allows a description.
