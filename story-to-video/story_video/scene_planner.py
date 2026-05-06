"""LLM-based scene planning from story text."""

import json
from pathlib import Path
from typing import Literal, Optional

from openai import OpenAI

from .config import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    DEFAULT_SCENE_DURATION,
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
)
from .models import StoryPlan


class ScenePlanner:
    """Breaks a story into visual scenes using LLM."""

    def __init__(
        self,
        provider: Literal["ollama", "openai", "azure"] = DEFAULT_PROVIDER,
        model: str = DEFAULT_MODEL,
        scene_duration: int = DEFAULT_SCENE_DURATION,
    ):
        self.provider = provider
        self.model = model
        self.scene_duration = scene_duration
        self.client = self._create_client()

    def _create_client(self) -> OpenAI:
        """Create OpenAI client based on provider."""
        if self.provider == "ollama":
            return OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
        elif self.provider == "openai":
            return OpenAI()
        elif self.provider == "azure":
            from openai import AzureOpenAI
            return AzureOpenAI()
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def plan_scenes(self, story: str, style_hint: Optional[str] = None) -> StoryPlan:
        """Convert story text into a structured scene plan."""
        system_prompt = self._load_system_prompt()
        user_prompt = self._build_user_prompt(story, style_hint)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )

        response_text = response.choices[0].message.content
        plan_data = self._extract_json(response_text)
        return StoryPlan(**plan_data)

    def _load_system_prompt(self) -> str:
        """Load the scene planning system prompt."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "scene_planning.md"
        if prompt_path.exists():
            return prompt_path.read_text()
        return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Fallback system prompt if file doesn't exist."""
        return """You are a visual storytelling expert. Your job is to break stories into scenes for video production.

For each scene, you must:
1. Choose the best visual style (image/remotion/manim)
2. Write a detailed visual prompt for the generator
3. Write narration text (shown as overlay)
4. Set appropriate duration (5-30s)
5. Choose transitions between scenes

Visual style guide:
- "image": Atmospheric, landscape, portrait, still moments (rendered with Ken Burns effect)
- "remotion": Dynamic motion, text animations, transitions, abstract visuals
- "manim": Explanatory diagrams, math, data visualization

Output must be valid JSON matching this schema:
{
  "title": "Story Title",
  "total_scenes": N,
  "scenes": [
    {
      "scene_number": 1,
      "duration": 30,
      "visual_style": "image|remotion|manim",
      "description": "Brief description",
      "prompt": "Detailed visual prompt for generator",
      "narration": "Text overlay for this scene",
      "transition": "none|fade_to_black|crossfade"
    }
  ]
}"""

    def _build_user_prompt(self, story: str, style_hint: Optional[str] = None) -> str:
        """Build the user prompt with story and constraints."""
        prompt = f"Convert this story into visual scenes (target duration: {self.scene_duration}s per scene):\n\n{story}"
        if style_hint:
            prompt += f"\n\nStyle preference: {style_hint}"
        return prompt

    def _extract_json(self, response_text: str) -> dict:
        """Extract JSON from LLM response (handles markdown code blocks)."""
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        
        return json.loads(text)
