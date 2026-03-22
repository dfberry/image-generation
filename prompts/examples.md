# Example Prompts

Curated prompts in the tropical magical-realism style for the dfberry blog post visuals.

## Style Guide
- **Palette:** deep magenta, teal, emerald green, warm gold, coral, amber
- **Aesthetic:** Latin American folk art, magical realism illustration
- **Mood:** Warmth, community, luminous energy
- **Resolution:** 1024×1024 (SDXL native)

## Prompt 1 — The Friction Wall
```
A glowing coral-and-teal architectural diagram rendered as a tropical mural, showing a labyrinth of tangled vines and colorful doors, each door labeled with a different codebase symbol, vibrant magenta and emerald palette, magical realism illustration style, luminous warm lighting, no text
```
```bash
python generate.py --prompt "A glowing coral-and-teal architectural diagram rendered as a tropical mural..." --refine --seed 42
```

## Prompt 2 — The Squad Gift
```
A radiant community gathering in a vibrant tropical courtyard, diverse group of figures each surrounded by a glowing colored aura representing their unique skill, deep magenta and gold particle effects, Latin American folk art aesthetic, lush botanical background, warm amber and teal accents, no text
```

## Prompt 3 — Inner Source Bridge
```
A luminous bridge made of intertwined tropical flowers and circuit patterns connecting two colorful village squares, each square representing a different team, emerald green and deep teal palette with gold light particles, magical realism illustration style, birds and butterflies in flight, no text
```

## Prompt 4 — Contributor Success
```
A single figure standing at the center of a blooming tropical garden, surrounded by floating glowing skill badges and ceremony symbols, warm coral and magenta gradient sky, lush emerald foliage, Latin American folk art color palette, celebratory and empowering mood, no text
```

## Prompt 5 — The Ceremonies Circle
```
An aerial view of a circular gathering space surrounded by tropical flora, figures seated in a ceremonial circle with colorful light emanating from a central glowing artifact, deep teal and gold palette, magical realism illustration, warm amber lantern light, no text
```

## Parameter Recommendations

| Use case | --steps | --guidance | --refine |
|----------|---------|------------|---------|
| Quick draft | 20 | 7.5 | no |
| Blog quality | 40 | 7.5 | yes |
| Best quality | 50 | 8.0 | yes |
