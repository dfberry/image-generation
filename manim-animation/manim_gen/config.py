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

Example 2 - Text with equation:
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
"""
