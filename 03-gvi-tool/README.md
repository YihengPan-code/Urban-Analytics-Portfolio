# Green View Index (GVI) Quantification Tool (HTML/JS)

This is a lightweight browser-based tool to quantify **Green View Index (GVI)** from street-level images.
It focuses on transparency + controllable parameters (HSV thresholds) rather than “black-box” models.

## What it does
- Batch-load a set of street-level images (ideally 4 directions per sampling point)
- Segment vegetation pixels using **HSV thresholds** (Hue / Saturation / Lightness)
- Optionally exclude artifacts (e.g., high-visibility clothing / glare) via an additional filter
- Output:
  - per-image GVI (%)
  - mean GVI across the loaded set
  - exportable masks + summary tables/figures

## Core idea (algorithm)
1) Input images → convert RGB → HSV  
2) **Hue check**: keep pixels within a vegetation hue range  
3) Apply saturation + lightness thresholds to reduce noise  
4) **Artifact exclusion (optional)**: remove non-vegetation pixels that are “too saturated / too bright”
   (useful for high-vis vests or reflective artifacts)  
5) Vegetation mask → compute:
   - `GVI = (vegetation_pixels / total_pixels) * 100`

## Parameter presets
The UI provides presets for common conditions (plus Custom), e.g.
- Standard (baseline hue range)
- Autumn-adjusted (handles seasonal browning)
- Strict filter (reduce false positives)
- Shadow enhancement (low-light/shadow scenes)
- Anti-glare / Vest (more aggressive artifact exclusion)

## How to run (no installation)
- Open `GVI.html` in Chrome/Edge.
- Click **Load Dataset** → select your images.
- Review masks + per-image GVI.
- Use **Export Data & Figures** to save results.

Tip: If your browser blocks batch file access, run a local server:
- `python -m http.server`
and open the page from `http://localhost:8000/`

## What’s in this folder
- `GVI.html` — the full single-file app

## Limitations (honest)
- HSV thresholding is simple and explainable, but sensitive to:
  lighting, shadows, seasonal color shift, and “green objects” that are not vegetation.
- This tool is intended for rapid, transparent GVI auditing.
  For high-stakes applications, validate against manual annotation on a sample.

## Suggested dataset practice (for consistency)
- Use consistent camera settings where possible
- Keep 4-direction images per sampling point (N/E/S/W) if your study design supports it
- Avoid extreme glare / night scenes unless using dedicated presets

