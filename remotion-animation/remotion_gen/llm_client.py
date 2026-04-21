"""LLM client for generating Remotion React components."""

import logging
import os
from typing import Optional

from remotion_gen.errors import LLMError

try:
    from openai import AzureOpenAI, OpenAI
except ImportError:
    raise ImportError(
        "OpenAI package not found. Install with: pip install openai"
    )

logger = logging.getLogger(__name__)

# Default models per provider
DEFAULT_MODELS = {
    "ollama": "llama3",
    "openai": "gpt-4",
}

SYSTEM_PROMPT = """You are a Remotion animation expert. Generate a React component for Remotion based on the user's description.

Requirements:
- Component name MUST be `GeneratedScene` (default export)
- Use Remotion hooks: useCurrentFrame(), useVideoConfig(), interpolate(), spring()
- Import from 'remotion' package: AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig
- Use inline styles (no external CSS)
- Component must accept fps, durationInFrames from useVideoConfig()
- Return ONLY the TSX code block, no explanation before or after
- Code must be valid TypeScript React
- Use modern React patterns (functional components, hooks)

When an image is provided:
- Import Img from 'remotion': import {Img} from 'remotion'
- Import staticFile from 'remotion': import {staticFile} from 'remotion'
- Use <Img src={staticFile('filename')} style={{width: 1280, height: 720}} /> to display
- Animate images with interpolate() on opacity, scale, or position
- NEVER use file:// URLs or relative paths — only staticFile()

Example structure:
```tsx
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  
  const opacity = interpolate(frame, [0, 30], [0, 1], {extrapolateRight: 'clamp'});
  
  return (
    <AbsoluteFill style={{backgroundColor: '#000', justifyContent: 'center', alignItems: 'center'}}>
      <h1 style={{color: '#fff', opacity}}>Hello Remotion</h1>
    </AbsoluteFill>
  );
}
```

Now generate a component based on the user's prompt."""


def _extract_code_block(response: str) -> str:
    """Extract TSX code from markdown code block."""
    lines = response.strip().split('\n')

    # Find code block boundaries
    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('```'):
            if start_idx is None:
                start_idx = i
            else:
                end_idx = i
                break

    if start_idx is None:
        # No code block markers, assume entire response is code
        return response.strip()

    if end_idx is None:
        # Only opening marker found
        code_lines = lines[start_idx + 1:]
    else:
        code_lines = lines[start_idx + 1:end_idx]

    return '\n'.join(code_lines).strip()


def _create_client(provider: str) -> tuple:
    """Create an OpenAI-compatible client for the given provider.
    
    Args:
        provider: "ollama", "openai", or "azure"
        
    Returns:
        Tuple of (client, model_name)
        
    Raises:
        LLMError: If credentials are missing or provider is unknown
    """
    provider = provider.lower()

    if provider == "ollama":
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        client = OpenAI(
            base_url=f"{ollama_host}/v1",
            api_key="ollama",
        )
        model = DEFAULT_MODELS["ollama"]
        return client, model

    if provider == "azure":
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_key = os.getenv("AZURE_OPENAI_KEY")
        azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

        if not all([azure_endpoint, azure_key, azure_deployment]):
            raise LLMError(
                "Azure OpenAI requires AZURE_OPENAI_ENDPOINT, "
                "AZURE_OPENAI_KEY, and AZURE_OPENAI_DEPLOYMENT"
            )
        client = AzureOpenAI(
            api_key=azure_key,
            api_version="2024-02-15-preview",
            azure_endpoint=azure_endpoint,
        )
        return client, azure_deployment

    if provider == "openai":
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise LLMError("OpenAI requires OPENAI_API_KEY environment variable")
        client = OpenAI(api_key=openai_key)
        return client, DEFAULT_MODELS["openai"]

    raise LLMError(
        f"Unknown provider '{provider}'. Use 'ollama', 'openai', or 'azure'."
    )


def generate_component(
    prompt: str,
    duration_seconds: int,
    fps: int,
    provider: str = "ollama",
    model: Optional[str] = None,
    image_context: Optional[str] = None,
) -> str:
    """Generate Remotion component code from user prompt.
    
    Args:
        prompt: User's animation description
        duration_seconds: Target video duration
        fps: Frames per second
        provider: LLM provider ("ollama", "openai", or "azure")
        model: Optional model name override
        image_context: Optional context about an available image asset
        
    Returns:
        TSX component code
        
    Raises:
        LLMError: If API call fails or returns invalid response
    """
    duration_frames = duration_seconds * fps

    user_prompt = f"""Create a {duration_seconds}-second animation ({duration_frames} frames at {fps}fps):

{prompt}
"""

    if image_context:
        user_prompt += f"\n{image_context}\n"

    user_prompt += "\nRemember: Return ONLY the TSX code, component must be named GeneratedScene and exported as default."

    try:
        client, default_model = _create_client(provider)
        model_name = model or default_model

        logger.info(f"Calling {provider} API with model {model_name}")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
        )

        if not response.choices:
            raise LLMError("LLM returned no choices")

        content = response.choices[0].message.content
        if not content:
            raise LLMError("LLM returned empty response")

        code = _extract_code_block(content)

        if not code:
            raise LLMError("Failed to extract code from LLM response")

        return code

    except Exception as e:
        if isinstance(e, LLMError):
            raise
        raise LLMError(f"LLM API call failed: {e}")
