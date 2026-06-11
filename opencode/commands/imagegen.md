---
description: Generate an explanatory image for research discussion or lab-meeting visuals
---

Load the imagegen skill.

Generate one explanatory raster image for this request:

$ARGUMENTS

Use the current conversation as scientific/design context. Prefer a clean educational diagram suitable for concept discussion, architecture explanation, or lab-meeting slides.

Workflow:

1. Compose a final image prompt using the imagegen skill guidance. Keep labels short and avoid dense exact equations.
2. Run the labflow image generator CLI from the current working directory:

```bash
node /home/hac/labflow/opencode/scripts/imagegen.mjs generate \
  --prompt "<final image prompt>" \
  --size 3840x2160 \
  --quality high
```

Use `--quality low` only for a quick draft. Use `--quality medium` when the user wants a faster normal-quality image. Use `--out <path>` only when the user names a destination; otherwise the CLI saves under `figures/imagegen/`.

After generation, report the saved path, model, size, quality, and the final prompt. Keep the explanation short; the image is the main artifact.
