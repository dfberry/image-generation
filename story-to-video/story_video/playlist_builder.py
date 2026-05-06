"""Builds video-stitcher playlist YAML from render results."""

from pathlib import Path
from typing import List

import yaml

from .models import RenderResult


class PlaylistBuilder:
    """Creates playlist YAML for video-stitcher from rendered clips."""

    @staticmethod
    def build_playlist(
        results: List[RenderResult],
        output_path: Path,
        transition: str = "fade_to_black",
    ) -> Path:
        """Build playlist YAML file from render results."""
        clips = []
        
        for result in results:
            if not result.success:
                continue
            
            clip_entry = {
                "path": str(result.clip_path.absolute()),
                "duration": result.duration,
            }
            
            # Add transition from scene metadata if available
            # For now, use the global transition setting
            if transition != "none":
                clip_entry["transition"] = transition
            
            clips.append(clip_entry)
        
        playlist_data = {
            "version": "1.0",
            "clips": clips,
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            yaml.dump(playlist_data, f, default_flow_style=False, sort_keys=False)
        
        return output_path
