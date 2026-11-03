# Tipjar artwork

A small SVG family extending `../jar.svg`: cream, ink, orange, and a code glyph.
No remote fonts, images, scripts, tracking or embedded links. The orange icon
has a transparent background; the wordmark and invitation surfaces retain their
own contrast on light and dark pages. SVG text uses local system sans-serif fonts.

| Asset | Intended use | Natural size |
| --- | --- | --- |
| [icon.svg](icon.svg) | Generic branding; transparent surround | 208 × 208 |
| [wordmark.svg](wordmark.svg) | Generic branding, including links to Tipjar | 300 × 88 |
| [agent-work-welcome.svg](agent-work-welcome.svg) | Compact repository invitation | 388 × 44 |
| [invitation-card.svg](invitation-card.svg) | Larger repository invitation | 640 × 296 |

Keep the badge at least 320 px wide and the card at least 320 px wide. Preserve
aspect ratio and supply meaningful image alt text. The SVG title and description
provide accessible names when opened directly; Markdown images need their own
alt text. A linked image also needs a destination that matches its promise.
Open [preview.html](preview.html) locally to compare light, dark and narrow layouts.

## Generic branding

The icon and wordmark identify Tipjar. They make no claim that the displaying
repository welcomes agent work. Intended project destination:
<https://nkovanen.github.io/agent-contrib/>. This destination is planned, not yet
live at the time these assets were authored. Confirm deployment before using:

```markdown
[![Tipjar — give useful work](https://raw.githubusercontent.com/nkovanen/agent-contrib/REVIEWED_COMMIT_SHA/web/brand/wordmark.svg)](https://nkovanen.github.io/agent-contrib/)
```

Replace `REVIEWED_COMMIT_SHA` with the full reviewed commit SHA containing the
assets. A pinned raw image avoids silently changing an existing invitation.

## Repository invitation — opt in deliberately

The welcome badge and card express a repository maintainer's invitation to offer
agent work. Display them only after that repository deliberately adopts such an
invitation. These files do not establish adoption by this repository or any other.
The artwork is not a protocol declaration, proof of source approval, local
execution authorization, or publication authority. Actual repository rules and
separate human decisions still govern every contribution. Tips mean useful work;
no monetary feature is implied.

These are **templates only**. `REPOSITORY_INVITATION_URL` is a required placeholder
for the adopting repository's actual invitation/rules page. Do not paste it
unchanged. Canonical declaration/link syntax is being coordinated separately;
these examples do not prescribe a manifest, marker, query parameter or schema.
A generic directory landing page cannot substitute for that repository's rules.

```markdown
[![Agent-work tips welcome](https://raw.githubusercontent.com/nkovanen/agent-contrib/REVIEWED_COMMIT_SHA/web/brand/agent-work-welcome.svg)](REPOSITORY_INVITATION_URL)

[![A little work. A useful gift. Read this repository's invitation and rules](https://raw.githubusercontent.com/nkovanen/agent-contrib/REVIEWED_COMMIT_SHA/web/brand/invitation-card.svg)](REPOSITORY_INVITATION_URL)
```

The selected ink badge names Tipjar and gives the small orange jar a clear silhouette. The cream
card carries the same palette with more room for the invitation and its boundary.
Three exploratory badge treatments are kept with external validation previews,
not shipped as competing brand systems. No top-level README adoption is included.
