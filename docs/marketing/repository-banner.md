# Repository Banner — DocuMindAI

**Format:** Wide repository banner for README header  
**Dimensions:** 1400 × 300 px (aspect ratio ~4.67:1)  
**Use:** Placed at the very top of README, above the title

---

## Design Intent

The banner should immediately communicate:

- **Brand identity** — DocuMindAI name and brain identity
- **Core value** — grounded, cited, trusted AI answers
- **Key differentiators** — 4–5 feature pills arranged horizontally
- **Professionalism** — dark SaaS aesthetic, no gimmicks

---

## Layout Blueprint

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                           │
│   [LEFT — 35%]                              [CENTER — 30%]     [RIGHT — 35%]             │
│                                                                                           │
│   🧠  DocuMindAI                        ──── ────── ────       ✦ Grounded AI              │
│   Enterprise AI Document Intelligence   ──── ────── ──         ✦ Page Citations           │
│   Grounded · Cited · Trusted                                   ✦ Trust Score              │
│                                                                ✦ Hybrid Retrieval         │
│                                                                ✦ 7 Workspaces             │
│                                                                                           │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Colors

| Element | Hex |
|---------|-----|
| Background | `#0D1117` |
| Left accent gradient | `radial-gradient(#1F6FEB18, transparent)` |
| Title | `#E6EDF3` |
| Subtitle | `#8B949E` |
| Tagline | `#58A6FF` |
| Feature dots | `#58A6FF` |
| Feature text | `#C9D1D9` |
| Divider lines | `#21262D` |
| Border | `1px solid #30363D` |

---

## Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Title (DocuMindAI) | Inter | 42px | 800 |
| Subtitle | Inter | 18px | 500 |
| Tagline | Inter | 15px | 400 |
| Feature labels | JetBrains Mono | 14px | 500 |

---

## Feature Pills (right column)

```
✦  Grounded AI Answers
✦  Page-Level Citations
✦  Veritas Trust Score
✦  Hybrid RAG Retrieval
✦  7 Specialized Workspaces
```

Each on its own line, dot color `#58A6FF`, text color `#C9D1D9`.

---

## HTML Reference Implementation

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1400px; height: 300px;
    background: #0D1117;
    font-family: 'Inter', sans-serif;
    display: flex;
    align-items: center;
    padding: 0 56px;
    gap: 48px;
    border-bottom: 1px solid #30363D;
    background-image:
      radial-gradient(ellipse at 15% 60%, #1F6FEB18 0%, transparent 55%);
    overflow: hidden;
  }
  .left { flex: 1.2; }
  .divider { width: 1px; height: 160px; background: #21262D; }
  .right { flex: 1; display: flex; flex-direction: column; gap: 14px; }
  .logo { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
  .brain { font-size: 40px; filter: drop-shadow(0 0 18px #1F6FEB70); }
  .name { font-size: 42px; font-weight: 800; color: #E6EDF3; line-height: 1; }
  .subtitle { font-size: 18px; font-weight: 500; color: #8B949E; margin-bottom: 6px; }
  .tagline { font-size: 15px; color: #58A6FF; }
  .feat {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px; font-weight: 500;
    color: #C9D1D9; display: flex; align-items: center; gap: 10px;
  }
  .dot { color: #58A6FF; font-size: 12px; }
</style>
</head>
<body>
  <div class="left">
    <div class="logo">
      <span class="brain">🧠</span>
      <span class="name">DocuMindAI</span>
    </div>
    <div class="subtitle">Enterprise AI Document Intelligence</div>
    <div class="tagline">Grounded · Cited · Trusted</div>
  </div>
  <div class="divider"></div>
  <div class="right">
    <div class="feat"><span class="dot">✦</span> Grounded AI Answers</div>
    <div class="feat"><span class="dot">✦</span> Page-Level Citations</div>
    <div class="feat"><span class="dot">✦</span> Veritas Trust Score 0–100</div>
    <div class="feat"><span class="dot">✦</span> Hybrid RAG Retrieval</div>
    <div class="feat"><span class="dot">✦</span> 7 Specialized Workspaces</div>
  </div>
</body>
</html>
```

---

## Export Instructions

1. Save as `banner.html`
2. Render with Puppeteer:
   ```js
   const browser = await puppeteer.launch();
   const page = await browser.newPage();
   await page.setViewport({ width: 1400, height: 300 });
   await page.goto('file:///path/to/banner.html');
   await page.screenshot({ path: 'docs/screenshots/banner.png', type: 'png' });
   await browser.close();
   ```
3. Place at `docs/screenshots/banner.png`
4. Add to README at the very top, before the centered div block:
   ```markdown
   ![DocuMindAI Banner](docs/screenshots/banner.png)
   ```

---

## Alternative: Figma

1. New frame: 1400 × 300
2. Fill: `#0D1117`
3. Add radial gradient fill layer at 15% opacity, origin left
4. Place elements per layout above
5. Export: PNG, 1x, compressed

---

## Fallback (text-only shield badges in README)

If image creation is not immediately possible, a badge row provides a minimal banner effect:

```markdown
<div align="center">
<img src="https://img.shields.io/badge/-%F0%9F%A7%A0%20DocuMindAI-0D1117?style=for-the-badge&labelColor=0D1117&color=1F6FEB" />
<img src="https://img.shields.io/badge/Grounded%20AI-Answers-1F6FEB?style=for-the-badge" />
<img src="https://img.shields.io/badge/Page-Citations-58A6FF?style=for-the-badge" />
<img src="https://img.shields.io/badge/Veritas-Trust%20Score-3FB950?style=for-the-badge" />
<img src="https://img.shields.io/badge/7-Workspaces-orange?style=for-the-badge" />
</div>
```
