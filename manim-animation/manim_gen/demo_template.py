"""Pre-built Manim demo scene that bypasses LLM generation.

This produces a reliable "Dina Berry" title card animation
without depending on llama3 to generate valid Manim code.
"""

from datetime import datetime


def get_demo_scene(datetime_str: str = None) -> str:
    """Return a complete GeneratedScene Manim class with the given timestamp.

    Args:
        datetime_str: Formatted date/time string to embed in the video.
            If None, uses current date/time.

    Returns:
        Valid Python source for a Manim GeneratedScene class.
    """
    if datetime_str is None:
        datetime_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    return f'''from manim import *


class GeneratedScene(Scene):
    def construct(self):
        # Dark background
        self.camera.background_color = "#0f0c29"

        # Title: "Dina Berry"
        title = Text("Dina Berry", font_size=72, color=WHITE, weight=BOLD)
        title.move_to(ORIGIN)

        # Timestamp below the title
        timestamp = Text(
            "{datetime_str}",
            font_size=28,
            color=GREY_A,
        )
        timestamp.next_to(title, DOWN, buff=0.5)

        # Animate in: title first, then timestamp
        self.play(FadeIn(title, shift=UP * 0.3), run_time=1.0)
        self.play(FadeIn(timestamp, shift=UP * 0.2), run_time=0.8)
        self.wait(2.0)

        # Clear before outro — no stacking
        self.play(FadeOut(title), FadeOut(timestamp), run_time=0.8)
        self.wait(0.3)

        # Outro
        outro = Text(
            "Generated with Manim",
            font_size=24,
            color=GREY_B,
        )
        outro.move_to(ORIGIN)
        self.play(FadeIn(outro), run_time=0.8)
        self.wait(2.0)
        self.play(FadeOut(outro), run_time=0.6)
'''
