# Presentation Image-Generation Prompts

Give each page a clear role. Identify the current page as the redesign target, accepted samples as style references, and source figures or recorded frames as factual material. Use only the inputs needed for the current iteration; the generated image does not verify the underlying claims.

## Initial candidate

```text
Create a visual design candidate for a presentation page, to be reconstructed as editable objects.

Audience and page purpose: <what the audience should understand>
Essential content and evidence: <verified material and relationships>
Inputs:
- Image 1, redesign target: <current page and its specific defects>.
- Image 2, style reference: <accepted visual characteristics; do not copy its claims>.
- Image 3, source material: <paper figure, photograph, screenshot, or video frame>.
Deck constraints: <specified header, logo, palette, typography, footer, and other invariants>
Composition: <image-text relationships, hierarchy, grouping, visual emphasis, spacing>
Avoid: inventing facts, changing mathematical or chart meaning, and filling space with unrelated decoration.
```

Adapt the aspect ratio and content to the user's deck. Give exact wording only when it matters, then verify the resulting text independently.

## Targeted revision

```text
Adjust only <specific region>: <visible defect> makes <relationship> unclear. Change <desired relationship or hierarchy>. Keep <content, other regions, branding, and established constraints> unchanged. Preserve the meaning of the original evidence.
```

Address related issues together when useful. Compare the result with the prior candidate and keep the stronger version; do not add decoration merely to make a page look busier.
