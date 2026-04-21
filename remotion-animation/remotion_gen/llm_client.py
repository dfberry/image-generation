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

SYSTEM_PROMPT = """You generate Remotion TSX components. Return ONLY raw TSX code — no markdown, no explanation, no fences.

ALWAYS:
- Name the component GeneratedScene and use export default function GeneratedScene().
- Import ONLY from 'remotion'. Valid imports: useCurrentFrame, useVideoConfig, interpolate, spring, Sequence, AbsoluteFill, Img, staticFile, Audio, Video, OffthreadVideo, Series, Easing, random, delayRender, continueRender, Loop, Still, Composition.
- Destructure fps and durationInFrames from useVideoConfig().
- Use inline styles (no CSS imports, no className).
- Match every opening bracket, parenthesis, and brace with its closing counterpart.
- Use {extrapolateRight: 'clamp'} on every interpolate() call.
- Close every JSX tag: <AbsoluteFill>...</AbsoluteFill>, <Sequence>...</Sequence>, <div>...</div>.
- Return valid TypeScript React — no any, no untyped variables.

NEVER:
- Do NOT wrap output in ``` or ```tsx fences — return raw code only.
- Do NOT import from 'react' — Remotion re-exports what you need.
- Do NOT use require(), fs, child_process, http, net, os, path, crypto, or any Node.js built-in.
- Do NOT use file:// URLs or relative paths — only staticFile() for assets.
- Do NOT use CSS modules, styled-components, or external style imports.
- Do NOT add comments like "// your code here" — write complete working code.
- Do NOT leave trailing commas in interpolate() or spring() argument lists.

API signatures (use these exactly):
- const frame = useCurrentFrame();  // returns number
- const {fps, durationInFrames, width, height} = useVideoConfig();
- interpolate(frame, [inputStart, inputEnd], [outputStart, outputEnd], {extrapolateRight: 'clamp'})
- spring({frame, fps, config: {damping: 200}})  // returns number 0-1
- <Sequence from={30} durationInFrames={60}>...</Sequence>

When an image is provided:
- Add Img and staticFile to your remotion import.
- Use <Img src={staticFile('filename.png')} style={{width: 1280, height: 720}} /> to display.
- Animate images with interpolate() on opacity, scale, or position.

Working example (copy this pattern exactly):

import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const opacity = interpolate(frame, [0, 30], [0, 1], {extrapolateRight: 'clamp'});
  const scale = interpolate(frame, [0, 30], [0.8, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a2e', justifyContent: 'center', alignItems: 'center'}}>
      <h1 style={{color: '#fff', fontSize: 80, opacity, transform: `scale(${scale})`}}>Hello Remotion</h1>
    </AbsoluteFill>
  );
}

Generate a component following these rules exactly."""


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


def _call_llm(
    client,
    model_name: str,
    provider: str,
    user_prompt: str,
    temperature: float,
) -> str:
    """Make a single LLM API call and extract the TSX code.

    Args:
        client: OpenAI-compatible client instance.
        model_name: Model to call.
        provider: Provider name (for logging).
        user_prompt: The user message content.
        temperature: Sampling temperature.

    Returns:
        Extracted TSX code string.

    Raises:
        LLMError: If API call fails or returns unusable output.
    """
    try:
        logger.info("Calling %s API with model %s", provider, model_name)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
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


def generate_component(
    prompt: str,
    duration_seconds: int,
    fps: int,
    provider: str = "ollama",
    model: Optional[str] = None,
    image_context: Optional[str] = None,
    max_retries: int = 0,
    validation_errors: Optional[list[str]] = None,
) -> str:
    """Generate Remotion component code from user prompt.

    Calls the LLM, validates the resulting TSX for structural errors
    (bracket mismatches, unclosed tags), and retries up to *max_retries*
    times by feeding errors back to the model for self-correction.

    Args:
        prompt: User's animation description
        duration_seconds: Target video duration
        fps: Frames per second
        provider: LLM provider ("ollama", "openai", or "azure")
        model: Optional model name override
        image_context: Optional context about an available image asset
        max_retries: Max retry attempts if validation fails (0 = no retry)
        validation_errors: Errors from a previous attempt, used for retry context

    Returns:
        TSX component code

    Raises:
        LLMError: If API call fails or returns invalid response after retries
    """
    from remotion_gen.component_builder import validate_tsx_syntax

    duration_frames = duration_seconds * fps

    base_prompt = f"""Create a {duration_seconds}-second animation ({duration_frames} frames at {fps}fps):

{prompt}
"""

    if image_context:
        base_prompt += f"\n{image_context}\n"

    base_prompt += "\nReturn ONLY raw TSX code. No markdown fences. Component must be named GeneratedScene with export default."

    # Lower temperature for small models to reduce structural errors
    temperature = 0.4 if provider == "ollama" else 0.7

    client, default_model = _create_client(provider)
    model_name = model or default_model

    current_errors = validation_errors
    attempts = 1 + max_retries  # first attempt + retries

    for attempt in range(attempts):
        user_prompt = base_prompt

        # Append prior errors so the LLM can self-correct
        if current_errors:
            error_list = "\n".join(f"  - {e}" for e in current_errors)
            user_prompt += (
                "\n\nYour previous attempt had these errors:\n"
                f"{error_list}\n"
                "Fix all of them. Double-check every bracket and parenthesis."
            )

        code = _call_llm(client, model_name, provider, user_prompt, temperature)

        # Quick structural validation before returning
        syntax_errors = validate_tsx_syntax(code)
        if not syntax_errors:
            return code

        # Validation failed — retry if we have attempts left
        if attempt < attempts - 1:
            logger.warning(
                "Attempt %d/%d produced syntax errors, retrying: %s",
                attempt + 1,
                attempts,
                syntax_errors,
            )
            current_errors = syntax_errors
        else:
            # Last attempt — return the code anyway and let
            # write_component raise a proper ValidationError
            logger.warning(
                "All %d attempts produced syntax errors; returning best effort",
                attempts,
            )
            return code
