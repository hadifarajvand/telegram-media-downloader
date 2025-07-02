"""
Utility functions for Telegram Media Downloader
"""

import json
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    default_config = {
        "telegram": {
            "session_name": "default_session",
            "batch_size": 5,
            "max_retries": 3,
            "retry_delay": 5
        },
        "download": {
            "output_directory": "downloads",
            "max_file_size_mb": 1000,
            "download_speed_limit": 0,
            "preserve_metadata": True,
            "organize_by_date": False,
            "organize_by_channel": True
        },
        "filters": {
            "min_file_size_kb": 0,
            "max_file_size_mb": 1000,
            "allowed_extensions": [],
            "excluded_extensions": [".exe", ".bat", ".sh"]
        },
        "logging": {
            "level": "INFO",
            "file": "telegram_downloader.log",
            "max_size_mb": 10,
            "backup_count": 5
        },
        "ui": {
            "show_progress": True,
            "show_file_info": True,
            "colors": True,
            "quiet_mode": False
        }
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                # Merge with defaults for missing keys
                return merge_configs(default_config, config)
        else:
            # Create default config file
            with open(config_path, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)
            return default_config
    except Exception as e:
        print(f"Warning: Could not load config file: {e}")
        return default_config

def merge_configs(default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge user config with defaults."""
    result = default.copy()
    for key, value in user.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result

def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception:
        return ""

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size_float = float(size_bytes)
    while size_float >= 1024 and i < len(size_names) - 1:
        size_float /= 1024.0
        i += 1
    
    return f"{size_float:.1f}{size_names[i]}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    return filename

def create_download_path(base_path: Path, channel_name: str, media_type: str, 
                        organize_by_date: bool = False, organize_by_channel: bool = True) -> Path:
    """Create organized download path."""
    path_parts = [str(base_path)]
    
    if organize_by_channel:
        path_parts.append(sanitize_filename(channel_name))
    
    if organize_by_date:
        path_parts.append(datetime.now().strftime("%Y-%m-%d"))
    
    path_parts.append(media_type)
    
    return Path(*path_parts)

def save_metadata(message, file_path: Path, config: Dict[str, Any]):
    """Save message metadata alongside downloaded file."""
    if not config.get("download", {}).get("preserve_metadata", True):
        return
    
    metadata = {
        "message_id": message.id,
        "date": message.date.isoformat() if message.date else None,
        "sender": str(message.sender_id) if message.sender else None,
        "chat": str(message.chat_id) if message.chat else None,
        "file_name": file_path.name,
        "file_size": file_path.stat().st_size if file_path.exists() else 0,
        "downloaded_at": datetime.now().isoformat()
    }
    
    metadata_path = file_path.with_suffix(file_path.suffix + ".json")
    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: Could not save metadata for {file_path}: {e}")

def should_download_file(file_size: int, file_extension: str, config: Dict[str, Any]) -> bool:
    """Check if file should be downloaded based on filters."""
    filters = config.get("filters", {})
    
    # Check file size limits
    min_size_kb = filters.get("min_file_size_kb", 0)
    max_size_mb = filters.get("max_file_size_mb", 1000)
    
    if file_size < min_size_kb * 1024:
        return False
    
    if file_size > max_size_mb * 1024 * 1024:
        return False
    
    # Check extension filters
    allowed_extensions = filters.get("allowed_extensions", [])
    excluded_extensions = filters.get("excluded_extensions", [])
    
    if allowed_extensions and file_extension.lower() not in [ext.lower() for ext in allowed_extensions]:
        return False
    
    if file_extension.lower() in [ext.lower() for ext in excluded_extensions]:
        return False
    
    return True

def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return Path(filename).suffix.lower()

def create_backup_filename(file_path: Path) -> Path:
    """Create a backup filename to avoid overwriting existing files."""
    counter = 1
    original_path = file_path
    
    while file_path.exists():
        stem = original_path.stem
        suffix = original_path.suffix
        file_path = original_path.parent / f"{stem}_{counter}{suffix}"
        counter += 1
    
    return file_path 