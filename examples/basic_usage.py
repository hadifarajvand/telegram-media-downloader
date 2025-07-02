#!/usr/bin/env python3
"""
Example usage of the enhanced Telegram Media Downloader
"""

import asyncio
import os
from pathlib import Path
from src.downloader import TelegramDownloader

async def example_basic_download():
    """Basic example of downloading media from a channel."""
    
    # Load environment variables
    api_id = int(os.getenv("API_ID", "0"))
    api_hash = os.getenv("API_HASH", "")
    
    # Initialize downloader
    async with TelegramDownloader(api_id, api_hash) as downloader:
        # Get media messages from a channel
        channel = "@example_channel"  # Replace with actual channel
        messages = await downloader.get_media_messages(channel, limit=10)
        
        if messages:
            # Download images only
            image_messages = downloader.filter_messages_by_type(messages, "images")
            
            # Download to organized directory
            output_path = Path("downloads") / "example_channel" / "images"
            stats = await downloader.download_batch(image_messages, output_path, batch_size=3)
            
            print(f"Download completed: {stats}")

async def example_with_filters():
    """Example with custom filtering."""
    
    api_id = int(os.getenv("API_ID", "0"))
    api_hash = os.getenv("API_HASH", "")
    
    async with TelegramDownloader(api_id, api_hash) as downloader:
        channel = "@example_channel"
        
        # Get all media messages
        messages = await downloader.get_media_messages(channel, limit=50)
        
        # Filter for videos only
        video_messages = downloader.filter_messages_by_type(messages, "videos")
        
        # Download with custom batch size
        output_path = Path("downloads") / "videos_only"
        stats = await downloader.download_batch(video_messages, output_path, batch_size=2)
        
        print(f"Video download stats: {stats}")

async def example_resume_download():
    """Example showing resume functionality."""
    
    api_id = int(os.getenv("API_ID", "0"))
    api_hash = os.getenv("API_HASH", "")
    
    async with TelegramDownloader(api_id, api_hash) as downloader:
        channel = "@example_channel"
        
        # First run - download some files
        messages = await downloader.get_media_messages(channel, limit=20)
        output_path = Path("downloads") / "resume_test"
        
        # Download first batch
        stats1 = await downloader.download_batch(messages[:10], output_path, batch_size=5)
        print(f"First batch: {stats1}")
        
        # Second run - resume (will skip already downloaded files)
        stats2 = await downloader.download_batch(messages, output_path, batch_size=5)
        print(f"Second batch (resume): {stats2}")

if __name__ == "__main__":
    # Check if environment variables are set
    if not os.getenv("API_ID") or not os.getenv("API_HASH"):
        print("Please set API_ID and API_HASH environment variables")
        exit(1)
    
    # Run examples
    print("Running basic download example...")
    asyncio.run(example_basic_download())
    
    print("\nRunning filtered download example...")
    asyncio.run(example_with_filters())
    
    print("\nRunning resume download example...")
    asyncio.run(example_resume_download()) 