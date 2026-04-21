"""Configuration and presets for manim_gen"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class QualityPreset(Enum):
    """Quality presets mapping to Manim quality flags and resolution"""

    LOW = ("l", 480, 15)  # 480p, 15fps
    MEDIUM = ("m", 720, 30)  # 720p, 30fps
    HIGH = ("h", 1080, 60)  # 1080p, 60fps

    @property
    def flag(self) -> str:
        """Manim quality flag (-ql, -qm, -qh)"""
        return self.value[0]

    @property
    def height(self) -> int:
        """Vertical resolution in pixels"""
        return self.value[1]

    @property
    def fps(self) -> int:
        """Frames per second"""
        return self.value[2]

@dataclass
class Config:
    """Runtime configuration for video generation"""

    quality: QualityPreset = QualityPreset.MEDIUM
    duration: int = 10  # seconds
    output_dir: Path = Path("outputs")
    debug: bool = False
    provider: str = "ollama"  # "ollama" (local, default), "openai", or "azure"

    def __post_init__(self):
        if isinstance(self.quality, str):
            self.quality = QualityPreset[self.quality.upper()]
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        if self.duration < 5 or self.duration > 30:
            raise ValueError("Duration must be between 5 and 30 seconds")

# Allowed imports in generated code (security whitelist)
ALLOWED_IMPORTS = {
    "manim",
    "math",
    "numpy",
    "np",  # common alias for numpy
}

# System prompt for LLM
SYSTEM_PROMPT = """You are a Manim Community Edition expert. Generate ONLY valid Python code for a Manim scene.

Requirements:
1. Create a single class named `GeneratedScene` that inherits from `Scene`
2. Use ONLY these imports: `from manim import *` and standard math/numpy
3. Implement the `construct(self)` method with animations
4. Use `self.play()` for animations and `self.wait()` for pauses
5. Target the specified duration with appropriate timing
6. Use Manim Community Edition syntax (not legacy ManimGL)
7. Return ONLY the Python code block with no explanation or markdown
8. When showing a sequence of items (numbers, text labels, equations), ALWAYS use FadeOut() or ReplacementTransform() to remove the previous item before showing the next. NEVER leave old items on screen when replaced by new ones.
9. For countdowns or number sequences, create each number as a new Text/MathTex object, FadeOut the old one, then FadeIn the new one. Do NOT stack them.

Example structure:
```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        # Create objects
        circle = Circle()
        text = Text("Hello")

        # Animate
        self.play(Create(circle))
        self.play(Write(text))
        self.wait()
```

When images are provided:
- Use `ImageMobject('filename.png')` to load images (they are in the working directory)
- Always use ONLY the exact literal filenames provided — never construct paths dynamically
- Scale images with `.scale()` or `.set_width()` / `.set_height()` to fit the scene
- Position with `.to_edge()`, `.shift()`, `.move_to()`, `.next_to()`
- Animate with FadeIn, FadeOut, GrowFromCenter, or any standard Manim animation

Now generate code for the user's request."""

# Few-shot examples for better LLM output
FEW_SHOT_EXAMPLES = """
Example 1 - Simple shape animation:
User: "A blue square that rotates and changes to a red circle"
```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        square = Square(color=BLUE)
        self.play(Create(square))
        self.play(Rotate(square, PI))
        self.wait(0.5)
        circle = Circle(color=RED)
        self.play(Transform(square, circle))
        self.wait()
```

Example 2 - Using an image:
User: "Show the screenshot sliding in from the left"
```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        img = ImageMobject('image_0_screenshot.png')
        img.scale(0.5)
        img.shift(LEFT * 6)
        self.play(img.animate.shift(RIGHT * 6), run_time=2)
        self.wait(1)
        caption = Text("Here's the screenshot", font_size=32)
        caption.next_to(img, DOWN)
        self.play(FadeIn(caption))
        self.wait()
```

Example 3 - Text with equation:
User: "Show the Pythagorean theorem with text and equation"
```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        title = Text("Pythagorean Theorem", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        equation = MathTex("a^2", "+", "b^2", "=", "c^2")
        self.play(Write(equation))
        self.wait(2)

        self.play(FadeOut(title), FadeOut(equation))
```

Example 4 - Counting sequence (correct cleanup):
User: "Count from 1 to 5 with each number appearing centered"
```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        prev = None
        for i in range(1, 6):
            num = Text(str(i), font_size=96)
            if prev is None:
                self.play(FadeIn(num))
            else:
                self.play(FadeOut(prev), FadeIn(num))
            self.wait(0.8)
            prev = num
        self.play(FadeOut(prev))
        self.wait(0.5)
```
"""
