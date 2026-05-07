"""Builds video-stitcher playlist YAML from render results."""

from pathlib import Path
from typing import List, Optional

import yaml

from .models import RenderResult


class PlaylistBuilder:
    """Creates playlist YAML for video-stitcher from rendered clips."""

    @staticmethod
    def build_playlist(
        results: List[RenderResult],
        output_path: Path,
        transition: str = "fade_to_black",
        scenes: Optional[List] = None,
    ) -> Path:
        """Build playlist YAML file from render results."""
        # Build scene transition lookup
        scene_transitions = {}
        if scenes:
            scene_transitions = {s.scene_number: s.transition for s in scenes}

        clips = []
        
        for result in results:
            if not result.success:
                continue
            
            clip_entry = {
                "path": str(result.clip_path.absolute()),
                "duration": result.duration,
            }
            
            # Use per-scene transition if available, else global
            scene_transition = scene_transitions.get(result.scene_number, transition)
            if scene_transition != "none":
                clip_entry["transition"] = scene_transition
            
            clips.append(clip_entry)
        
        if not clips:
            raise ValueError("No scenes rendered successfully — cannot build playlist")
        
        playlist_data = {
            "version": "1.0",
            "clips": clips,
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            yaml.dump(playlist_data, f, default_flow_style=False, sort_keys=False)
        
        return output_path
