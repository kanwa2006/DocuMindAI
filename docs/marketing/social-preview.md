# Social Preview Specification — DocuMindAI

**Format:** GitHub Social Preview (OG Image)
**Dimensions:** 1280 × 640 px
**Export:** PNG, optimized for GitHub, Twitter/X, LinkedIn link previews

---

## Design Intent

The social preview should communicate three things in under 2 seconds:

1. This is an AI product for documents
2. It is enterprise-grade and technically serious
3. It is different from generic chatbots — grounded, cited, trusted

---

## Layout Blueprint

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                                                                                │
│  [LEFT PANEL — 55% width]                  [RIGHT PANEL — 45% width]          │
│                                                                                │
│  ┌──────────────────────────────┐           ┌──────────────────────────────┐  │
│  │                              │           │                              │  │
│  │   🧠  DocuMindAI             │           │  FEATURE PILLS (stacked)     │  │
│  │                              │           │                              │  │
│  │   Enterprise AI Document     │           │  ✦ Grounded AI Answers       │  │
│  │   Intelligence               │           │  ✦ Page-Level Citations      │  │
│  │                              │           │  ✦ Veritas Trust Score       │  │
│  │   Grounded · Cited · Trusted │           │  ✦ Hybrid RAG Retrieval      │  │
│  │                              │           │  ✦ 7 Specialized Workspaces  │  │
│  │   ─────────────────          │           │  ✦ Multi-Engine OCR          │  │
│  │                              │           │  ✦ Real-Time Streaming       │  │
│  │   FastAPI · Next.js 16       │           │                              │  │
│  │   pgvector · Gemini          │           └──────────────────────────────┘  │
│  │                              │                                              │
│  │   github.com/kanwa2006/      │                                              │
│  │   DocuMindAI                 │                                              │
│  │                              │                                              │
│  └──────────────────────────────┘                                              │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Color Palette

| Role | Hex | Usage |
|------|-----|-------|
| Background | `#0D1117` | Full canvas — GitHub dark default |
| Surface | `#161B22` | Card / panel backgrounds |
| Border | `#30363D` | Subtle panel borders |
| Accent Primary | `#58A6FF` | Title text, feature pill border |
| Accent Glow | `#1F6FEB` | Gradient behind brain icon |
| Tagline | `#8B949E` | Subtitle / tagline text |
| Feature text | `#E6EDF3` | Feature pill labels |
| Stack pills | `#21262D` | Technology badge backgrounds |
| Green accent | `#3FB950` | Trust score / verified indicators |

### Gradient (background subtle wash)
```
radial-gradient(ellipse at 20% 50%, #1F6FEB18 0%, transparent 60%)
radial-gradient(ellipse at 80% 20%, #58A6FF0D 0%, transparent 50%)
```

---

## Typography

| Element | Font | Weight | Size | Color |
|---------|------|--------|------|-------|
| Logo / Title | **Inter** | 800 (ExtraBold) | 52px | `#E6EDF3` |
| Subtitle line 1 | **Inter** | 600 (SemiBold) | 28px | `#8B949E` |
| Tagline | **Inter** | 400 (Regular) | 20px | `#58A6FF` |
| Feature pills | **Inter Mono** | 500 (Medium) | 16px | `#E6EDF3` |
| Tech stack | **Inter** | 400 (Regular) | 14px | `#8B949E` |
| GitHub URL | **Inter** | 400 (Regular) | 14px | `#58A6FF` |

**Recommended Google Fonts import:**
```
Inter:wght@400;500;600;800
```

---

## Spacing System

| Element | Value |
|---------|-------|
| Canvas padding | 64px all sides |
| Left/right panel gap | 48px |
| Between feature pills | 14px vertical |
| Feature pill padding | 10px 16px |
| Brain icon size | 48px |
| Icon–title gap | 16px |

---

## Feature Pills (Right Panel)

Each pill is a small rounded rectangle:

```
Border: 1px solid #30363D
Background: #161B22
Border-radius: 8px
Padding: 10px 16px
Font: Inter Mono 500 16px
Color: #E6EDF3
Leading dot: ✦ in #58A6FF
```

Pill labels (in order):
1. `✦  Grounded AI Answers`
2. `✦  Page-Level Citations`
3. `✦  Veritas Trust Score 0–100`
4. `✦  Hybrid RAG Retrieval`
5. `✦  7 Specialized Workspaces`
6. `✦  Multi-Engine OCR`
7. `✦  Real-Time SSE Streaming`

---

## Brain Icon

Use the `🧠` emoji rendered at large size OR an SVG brain icon (e.g., Lucide `brain`).

Render with a soft blue radial glow behind it:
```css
filter: drop-shadow(0 0 24px #1F6FEB60);
```

---

## Tech Stack Row (bottom of left panel)

Three small pill badges in a horizontal row:

```
[ FastAPI ]  [ Next.js 16 ]  [ pgvector ]  [ Gemini ]
```

Badge style:
```
Background: #21262D
Border: 1px solid #30363D
Border-radius: 6px
Padding: 4px 12px
Font: Inter 400 14px
Color: #8B949E
```

---

## GitHub URL Footer

```
github.com/kanwa2006/DocuMindAI
```

Positioned bottom-left, color `#58A6FF`, font size 14px.

---

## Export Recommendations

| Platform | Requirement |
|----------|-------------|
| **GitHub Social Preview** | Upload via Settings → Social Preview. Max 1MB. |
| **Twitter/X card** | Use `og:image` meta tag in Next.js `layout.tsx` pointing to a hosted copy |
| **LinkedIn** | Auto-fetches from `og:image` when sharing the GitHub URL |
| **Devpost** | Upload as project gallery image |

### How to upload to GitHub
1. Go to `https://github.com/kanwa2006/DocuMindAI/settings`
2. Scroll to **Social preview** section
3. Click **Edit** → upload the 1280×640 PNG

---

## Creation Tools

| Tool | Notes |
|------|-------|
| **Figma** | Recommended — use Auto Layout for pills, export as PNG 2x |
| **Canva** | Use custom dimensions 1280×640, dark mode |
| **Carbon.now.sh** | Good for code-focused previews |
| **Vercel OG Playground** | Can generate OG images programmatically |
| **HTML + Puppeteer** | Best for pixel-perfect replication of the spec above |

---

## HTML Reference Implementation

A minimal HTML snapshot that can be rendered to PNG via Puppeteer or `html-to-image`:

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1280px; height: 640px;
    background: #0D1117;
    font-family: 'Inter', sans-serif;
    display: flex;
    align-items: center;
    padding: 64px;
    gap: 48px;
    background-image:
      radial-gradient(ellipse at 20% 50%, #1F6FEB18 0%, transparent 60%),
      radial-gradient(ellipse at 80% 20%, #58A6FF0D 0%, transparent 50%);
  }
  .left { flex: 1.2; display: flex; flex-direction: column; gap: 20px; }
  .right { flex: 1; display: flex; flex-direction: column; gap: 14px; }
  .logo-row { display: flex; align-items: center; gap: 16px; }
  .brain { font-size: 48px; filter: drop-shadow(0 0 24px #1F6FEB60); }
  .title { font-size: 52px; font-weight: 800; color: #E6EDF3; line-height: 1; }
  .subtitle { font-size: 28px; font-weight: 600; color: #8B949E; }
  .tagline { font-size: 20px; color: #58A6FF; }
  .divider { width: 80px; height: 2px; background: #30363D; margin: 4px 0; }
  .stack { display: flex; gap: 8px; flex-wrap: wrap; }
  .badge {
    background: #21262D; border: 1px solid #30363D;
    border-radius: 6px; padding: 4px 12px;
    font-size: 14px; color: #8B949E;
  }
  .url { font-size: 14px; color: #58A6FF; margin-top: 8px; }
  .pill {
    background: #161B22; border: 1px solid #30363D;
    border-radius: 8px; padding: 10px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px; color: #E6EDF3;
  }
  .dot { color: #58A6FF; margin-right: 8px; }
</style>
</head>
<body>
  <div class="left">
    <div class="logo-row">
      <span class="brain">🧠</span>
      <span class="title">DocuMindAI</span>
    </div>
    <div class="subtitle">Enterprise AI Document Intelligence</div>
    <div class="tagline">Grounded · Cited · Trusted</div>
    <div class="divider"></div>
    <div class="stack">
      <span class="badge">FastAPI</span>
      <span class="badge">Next.js 16</span>
      <span class="badge">pgvector</span>
      <span class="badge">Gemini</span>
    </div>
    <div class="url">github.com/kanwa2006/DocuMindAI</div>
  </div>
  <div class="right">
    <div class="pill"><span class="dot">✦</span>Grounded AI Answers</div>
    <div class="pill"><span class="dot">✦</span>Page-Level Citations</div>
    <div class="pill"><span class="dot">✦</span>Veritas Trust Score 0–100</div>
    <div class="pill"><span class="dot">✦</span>Hybrid RAG Retrieval</div>
    <div class="pill"><span class="dot">✦</span>7 Specialized Workspaces</div>
    <div class="pill"><span class="dot">✦</span>Multi-Engine OCR</div>
    <div class="pill"><span class="dot">✦</span>Real-Time SSE Streaming</div>
  </div>
</body>
</html>
```

Save as `social-preview.html`, render with Puppeteer at viewport `1280×640`, export PNG.
