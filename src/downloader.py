#!/usr/bin/env python3
"""
Telegram Media Downloader - Enhanced Version
A robust tool for downloading media from Telegram channels and groups.
"""

import asyncio
import json
import logging
import os
import sys
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel
from tenacity import retry, stop_after_attempt, wait_exponential
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError, 
    SessionPasswordNeededError, 
    PhoneCodeInvalidError
)
from telethon.tl.types import (
    DocumentAttributeFilename,
    InputMessagesFilterVideo,
    InputMessagesFilterPhotos,
    InputMessagesFilterDocument,
    Message,
    Channel,
    Chat
)
from link_extractor import TelegramLinkExtractor

# Load environment variables
load_dotenv()

# Replace sys.stdout with a UTF-8 writer
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_downloader.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Rich console for better output
console = Console()

class DownloadState:
    """Manages download state and resume functionality."""
    
    def __init__(self, state_file: str = "download_state.json"):
        self.state_file = state_file
        self.downloaded_files: Set[str] = set()
        self.load_state()
    
    def load_state(self):
        """Load previously downloaded files from state file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.downloaded_files = set(data.get('downloaded_files', []))
                logger.info(f"Loaded {len(self.downloaded_files)} previously downloaded files")
        except Exception as e:
            logger.warning(f"Could not load download state: {e}")
    
    def save_state(self):
        """Save current download state to file."""
        try:
            data = {
                'downloaded_files': list(self.downloaded_files),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save download state: {e}")
    
    def is_downloaded(self, file_id: str) -> bool:
        """Check if a file has already been downloaded."""
        return file_id in self.downloaded_files
    
    def mark_downloaded(self, file_id: str):
        """Mark a file as downloaded."""
        self.downloaded_files.add(file_id)
        self.save_state()

class TelegramDownloader:
    """Enhanced Telegram media downloader with advanced features."""
    
    def __init__(self, api_id: int, api_hash: str, session_name: str = "default_session"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.client: Optional[TelegramClient] = None
        self.download_state = DownloadState()
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.disconnect()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def connect(self):
        """Connect to Telegram with retry logic."""
        try:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await self.client.start()
            
            if not await self.client.is_user_authorized():
                console.print("[red]Authentication required![/red]")
                phone = console.input("[cyan]Enter your phone number: [/cyan]")
                await self.client.send_code_request(phone)
                code = console.input("[cyan]Enter the code you received: [/cyan]")
                try:
                    await self.client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    password = console.input("[cyan]Enter your 2FA password: [/cyan]")
                    await self.client.sign_in(password=password)
            
            console.print("[green]✓ Connected to Telegram successfully![/green]")
            logger.info("Successfully connected to Telegram")
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise
    
    def get_file_id(self, message: Message) -> str:
        """Generate a unique file ID for tracking downloads."""
        if message.video:
            return f"video_{message.id}_{message.video.id}"
        elif message.document:
            return f"doc_{message.id}_{message.document.id}"
        elif message.photo:
            return f"photo_{message.id}_{message.photo.id}"
        else:
            return f"media_{message.id}"
    
    def get_file_name(self, message: Message) -> str:
        """Extract filename from message."""
        document = getattr(message, 'document', None)
        if document:
            for attr in getattr(document, 'attributes', []):
                if isinstance(attr, DocumentAttributeFilename):
                    return attr.file_name
            return f"document_{getattr(message, 'id', 'unknown')}"
        video = getattr(message, 'video', None)
        if video is not None:
            return f"video_{getattr(message, 'id', 'unknown')}.mp4"
        photo = getattr(message, 'photo', None)
        if photo is not None:
            return f"photo_{getattr(message, 'id', 'unknown')}.jpg"
        return f"media_{getattr(message, 'id', 'unknown')}"
    
    def get_file_size(self, message: Message) -> int:
        """Get file size in bytes."""
        if message.video:
            return message.video.size or 0
        elif message.document:
            return message.document.size or 0
        elif message.photo:
            return 1024 * 1024  # 1MB estimate
        return 0
    
    async def download_file(self, message: Message, folder_path: Path, progress: Progress) -> bool:
        """Download a single file with progress tracking and error handling."""
        file_id = self.get_file_id(message)
        file_name = self.get_file_name(message)
        file_size = self.get_file_size(message)
        
        # Check if already downloaded
        if self.download_state.is_downloaded(file_id):
            logger.info(f"Skipping already downloaded file: {file_name}")
            return True
        
        # Ensure file_name is a valid string (not an object)
        if not isinstance(file_name, str) or file_name.startswith("<telethon.tl.custom"):
            # Try to get from message.file.name or fallback
            file_name = getattr(getattr(message, 'file', None), 'name', None) or f"media_{getattr(message, 'id', 'unknown')}"
        file_path = folder_path / file_name
        
        # Create task for progress tracking
        task = progress.add_task(
            f"[cyan]Downloading {file_name}",
            total=file_size,
            filename=file_name
        )
        
        try:
            # Download with progress callback
            await message.download_media(
                file=str(file_path),
                progress_callback=lambda current, total: progress.update(task, completed=current)
            )
            
            # Mark as downloaded
            self.download_state.mark_downloaded(file_id)
            progress.update(task, description=f"[green]✓ Downloaded {file_name}")
            logger.info(f"Successfully downloaded: {file_name}")
            return True
            
        except Exception as e:
            progress.update(task, description=f"[red]✗ Failed {file_name}")
            logger.error(f"Failed to download {file_name}: {e}")
            # Remove partial file if it exists
            if file_path.exists():
                file_path.unlink()
            return False
    
    async def get_media_messages(
        self, 
        entity: Union[str, Channel, Chat], 
        filter_type: Optional[object] = None,
        limit: int = 2000,
        offset_date: Optional[datetime] = None
    ) -> List[Message]:
        """Get media messages with filtering and pagination."""
        try:
            # Get entity if string is provided
            if isinstance(entity, str):
                entity = await self.client.get_entity(entity)
            
            console.print(f"[yellow]Fetching messages from: {getattr(entity, 'title', entity)}[/yellow]")
            
            messages = []
            async for message in self.client.iter_messages(
                entity, 
                filter=filter_type, 
                limit=limit,
                offset_date=offset_date
            ):
                if message.media:
                    messages.append(message)
            
            console.print(f"[green]Found {len(messages)} media messages[/green]")
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            raise
    
    async def download_batch(
        self, 
        messages: List[Message], 
        folder_path: Path, 
        batch_size: int = 5
    ) -> Dict[str, int]:
        """Download messages in batches with progress tracking."""
        stats = {"success": 0, "failed": 0, "skipped": 0}
        
        # Create download folder
        folder_path.mkdir(parents=True, exist_ok=True)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            # Process in batches
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                console.print(f"\n[cyan]Processing batch {i//batch_size + 1}/{(len(messages) + batch_size - 1)//batch_size}[/cyan]")
                
                # Download files in parallel
                tasks = [
                    self.download_file(message, folder_path, progress) 
                    for message in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count results
                for result in results:
                    if isinstance(result, Exception):
                        stats["failed"] += 1
                        logger.error(f"Download task failed: {result}")
                    elif result is True:
                        stats["success"] += 1
                    else:
                        stats["skipped"] += 1
        
        return stats
    
    def get_filter_type(self, media_type: str):
        """Get Telethon filter type based on media type."""
        filters = {
            "images": InputMessagesFilterPhotos(),
            "videos": InputMessagesFilterVideo(),
            "documents": InputMessagesFilterDocument(),
            "all": None
        }
        return filters.get(media_type.lower())
    
    def filter_messages_by_type(self, messages: List[Message], media_type: str) -> List[Message]:
        """Filter messages by specific media type."""
        if media_type.lower() == "all":
            return messages
        
        filtered = []
        for message in messages:
            if media_type.lower() == "images" and message.photo:
                filtered.append(message)
            elif media_type.lower() == "videos" and message.video:
                filtered.append(message)
            elif media_type.lower() == "pdfs" and message.document and message.document.mime_type == "application/pdf":
                filtered.append(message)
            elif media_type.lower() == "zips" and message.document and message.document.mime_type == "application/zip":
                filtered.append(message)
            elif media_type.lower() == "documents" and message.document:
                filtered.append(message)
        
        return filtered

# --- Main Menu Logic ---
def main_menu():
    console.print("[bold cyan]\nWelcome to Telegram Media Downloader![/bold cyan]")
    while True:
        console.print("\n[bold]Please select an action:[/bold]")
        console.print("1. Download media from a channel/group")
        console.print("2. Extract Telegram channel links from messages")
        console.print("3. Exit")
        choice = console.input("[cyan]> [/cyan]").strip()
        if choice == "1":
            return "download"
        elif choice == "2":
            return "extract_links"
        elif choice == "3":
            console.print("[yellow]Goodbye![/yellow]")
            sys.exit(0)
        else:
            console.print("[red]Invalid choice. Please select 1, 2, or 3.[/red]")

@click.command()
@click.option('--channel', '-c', help='Channel username or link')
@click.option('--type', '-t', 'media_type', 
              type=click.Choice(['images', 'videos', 'pdfs', 'zips', 'documents', 'all']),
              default=None, help='Type of media to download')
@click.option('--limit', '-l', default=None, help='Maximum number of messages to fetch')
@click.option('--batch-size', '-b', default=None, help='Number of concurrent downloads')
@click.option('--output', '-o', default=None, help='Output directory')
@click.option('--dry-run', is_flag=True, help='Show what would be downloaded without actually downloading')
@click.option('--resume', is_flag=True, help='Resume from previous download state')
@click.option('--extract-links', is_flag=True, help='Extract Telegram channel links from messages and save to JSON')
@click.option('--extract-output', default=None, help='Output file for extracted links (JSON)')
def main(channel, media_type, limit, batch_size, output, dry_run, resume, extract_links, extract_output):
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    if not api_id or not api_hash:
        console.print("[red]Error: API_ID and API_HASH must be set in .env file[/red]")
        sys.exit(1)
    try:
        api_id = int(api_id)
    except ValueError:
        console.print("[red]Error: API_ID must be a valid integer[/red]")
        sys.exit(1)

    # If no CLI options, show main menu
    if not any([channel, media_type, extract_links]):
        action = main_menu()
        if action == "download":
            channel = console.input("[cyan]Enter channel username or link: [/cyan]").strip()
            console.print("[cyan]Choose the type of content to download:[/cyan]\n1. Images\n2. Videos\n3. PDFs\n4. ZIP files\n5. All types")
            type_choice = console.input("[cyan]Enter your choice (1-5): [/cyan]").strip()
            type_map = {"1": "images", "2": "videos", "3": "pdfs", "4": "zips", "5": "all"}
            media_type = type_map.get(type_choice, "all")
            batch_size = console.input("[cyan]Set batch size (default 5): [/cyan]").strip() or "5"
            limit = console.input("[cyan]Set message limit (default 2000): [/cyan]").strip() or "2000"
            output = console.input("[cyan]Set output directory (default downloads): [/cyan]").strip() or "downloads"
            dry_run = False
            resume = False
        elif action == "extract_links":
            channel = console.input("[cyan]Enter channel username or link: [/cyan]").strip()
            limit = console.input("[cyan]Set message limit for extraction (default 1000): [/cyan]").strip() or "1000"
            extract_output = console.input("[cyan]Set output file (default extracted_links.json): [/cyan]").strip() or "extracted_links.json"
            extract_links = True
        else:
            sys.exit(0)

    asyncio.run(run_main(api_id, api_hash, channel, media_type, limit, batch_size, output, dry_run, resume, extract_links, extract_output))

async def run_main(api_id, api_hash, channel, media_type, limit, batch_size, output, dry_run, resume, extract_links, extract_output):
    # Only one TelegramClient instance, used everywhere
    async with TelegramClient("default_session", api_id, api_hash) as client:
        if extract_links:
            await run_link_extraction(client, channel, limit, extract_output)
        else:
            await run_media_download(client, channel, media_type, limit, batch_size, output, dry_run, resume)

def get_filter_type(media_type: str):
    filters = {
        "images": InputMessagesFilterPhotos(),
        "videos": InputMessagesFilterVideo(),
        "documents": InputMessagesFilterDocument(),
        "all": None
    }
    return filters.get(media_type.lower())

def filter_messages_by_type(messages, media_type: str):
    if media_type.lower() == "all":
        return messages
    filtered = []
    for message in messages:
        if media_type.lower() == "images" and getattr(message, 'photo', None):
            filtered.append(message)
        elif media_type.lower() == "videos" and getattr(message, 'video', None):
            filtered.append(message)
        elif media_type.lower() == "pdfs" and getattr(message, 'document', None) and getattr(message.document, 'mime_type', None) == "application/pdf":
            filtered.append(message)
        elif media_type.lower() == "zips" and getattr(message, 'document', None) and getattr(message.document, 'mime_type', None) == "application/zip":
            filtered.append(message)
        elif media_type.lower() == "documents" and getattr(message, 'document', None):
            filtered.append(message)
    return filtered

async def run_media_download(client, channel, media_type, limit, batch_size, output, dry_run, resume):
    # Set defaults if not provided
    media_type = media_type or "all"
    batch_size = int(batch_size) if batch_size else 5
    limit = int(limit) if limit else 2000
    output = output or "downloads"
    # Show configuration
    table = Table(title="Download Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Channel", channel)
    table.add_row("Media Type", media_type)
    table.add_row("Limit", str(limit))
    table.add_row("Batch Size", str(batch_size))
    table.add_row("Output Directory", output)
    table.add_row("Dry Run", str(dry_run))
    table.add_row("Resume", str(resume))
    console.print(table)
    if dry_run:
        console.print("[yellow]Dry run mode - no files will be downloaded[/yellow]")
    # Get media messages
    filter_type = get_filter_type(media_type)
    messages = []
    async for msg in client.iter_messages(channel, filter=filter_type, limit=limit):
        messages.append(msg)
    if not messages:
        console.print("[red]No media messages found![/red]")
        return
    if media_type in ['pdfs', 'zips']:
        messages = filter_messages_by_type(messages, media_type)
    if dry_run:
        table = Table(title="Files to be downloaded")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Size", style="green")
        table.add_column("Name", style="white")
        total_size = 0
        for msg in messages[:10]:
            file_name = getattr(msg, 'file', None) or getattr(msg, 'id', None)
            file_size = getattr(getattr(msg, 'document', None), 'size', 0) or getattr(getattr(msg, 'video', None), 'size', 0) or 0
            total_size += file_size
            msg_type = "Video" if getattr(msg, 'video', None) else "Document" if getattr(msg, 'document', None) else "Photo" if getattr(msg, 'photo', None) else "Other"
            table.add_row(str(msg.id), msg_type, f"{file_size/1024/1024:.1f}MB", str(file_name))
        if len(messages) > 10:
            table.add_row("...", "...", "...", f"... and {len(messages)-10} more files")
        console.print(table)
        console.print(f"[green]Total files: {len(messages)}[/green]")
        console.print(f"[green]Estimated total size: {total_size/1024/1024:.1f}MB[/green]")
        return
    output_path = Path(output) / media_type
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
    console.print(f"\n[cyan]Starting download to: {output_path}[/cyan]")
    # Use TelegramDownloader for graphical progress
    downloader = TelegramDownloader(api_id=client.api_id, api_hash=client.api_hash, session_name=client.session.filename)
    downloader.client = client  # Use the already-authenticated client
    stats = await downloader.download_batch(messages, output_path, batch_size=batch_size)
    # Show results
    result_table = Table(title="Download Results")
    result_table.add_column("Metric", style="cyan")
    result_table.add_column("Count", style="green")
    result_table.add_row("Successfully Downloaded", str(stats["success"]))
    result_table.add_row("Failed", str(stats["failed"]))
    result_table.add_row("Skipped (Already Downloaded)", str(stats["skipped"]))
    result_table.add_row("Total Processed", str(sum(stats.values())))
    console.print(result_table)
    if stats["failed"] > 0:
        console.print("[yellow]Some downloads failed. Check the log file for details.[/yellow]")

async def run_link_extraction(client, channel, limit, extract_output):
    extractor = TelegramLinkExtractor(client)
    console.print(f"[yellow]Extracting links from {channel}...[/yellow]")
    results = await extractor.extract_links_from_channel(
        channel_identifier=channel,
        limit=int(limit) if limit else 1000,
        save_to_file=True,
        output_file=extract_output or "extracted_links.json"
    )
    console.print(f"[green]Extraction complete! {results['extraction_info']['total_links_found']} links found.[/green]")
    console.print(f"[green]Links saved to: {extract_output or 'extracted_links.json'}[/green]")

if __name__ == "__main__":
    main() 