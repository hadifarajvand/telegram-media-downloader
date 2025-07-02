"""
Telegram Link Extractor Module
Extracts channel links from Telegram messages and stores detailed information.
"""

import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from telethon.tl.types import Message, MessageEntityTextUrl, MessageEntityUrl, KeyboardButtonUrl
from telethon.tl.functions.channels import GetFullChannelRequest

logger = logging.getLogger(__name__)

class TelegramLinkExtractor:
    """Extracts and analyzes Telegram channel links from messages."""
    def __init__(self, client):
        self.client = client
        # Improved regex patterns for all Telegram link formats
        self.link_patterns = [
            r'https?://t\.me/[a-zA-Z0-9_]+',
            r't\.me/[a-zA-Z0-9_]+',
            r'@([a-zA-Z0-9_]{5,32})',
            r'https?://t\.me/joinchat/[a-zA-Z0-9_-]+',
            r'https?://t\.me/c/\d+/\d+',
        ]

    def extract_links_from_text(self, text: str, message_id: int, chat_id: Optional[int], context: str = "") -> List[Dict[str, Any]]:
        links = []
        if not text:
            return links
        for pattern in self.link_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                link = match.group(0)
                links.append({
                    'link': link,
                    'message_id': message_id,
                    'chat_id': chat_id,
                    'context': context,
                    'position': match.span(),
                    'timestamp': datetime.now().isoformat()
                })
        return links

    def extract_links_from_entities(self, message: Message) -> List[Dict[str, Any]]:
        links = []
        if hasattr(message, 'entities') and message.entities:
            for entity in message.entities:
                if isinstance(entity, (MessageEntityTextUrl, MessageEntityUrl)):
                    if hasattr(entity, 'url') and entity.url:
                        links.append({
                            'link': entity.url,
                            'message_id': message.id,
                            'chat_id': getattr(message, 'chat_id', None),
                            'context': 'entity',
                            'position': (entity.offset, entity.offset + entity.length),
                            'timestamp': datetime.now().isoformat()
                        })
        return links

    def extract_links_from_reply_markup(self, message: Message) -> List[Dict[str, Any]]:
        links = []
        markup = getattr(message, 'reply_markup', None)
        if markup and hasattr(markup, 'rows'):
            for row in markup.rows:
                for button in row.buttons:
                    if isinstance(button, KeyboardButtonUrl):
                        links.append({
                            'link': button.url,
                            'message_id': message.id,
                            'chat_id': getattr(message, 'chat_id', None),
                            'context': 'button',
                            'position': None,
                            'timestamp': datetime.now().isoformat()
                        })
        return links

    async def get_channel_info(self, channel_identifier: str) -> Optional[Dict[str, Any]]:
        try:
            if channel_identifier.startswith('@'):
                channel_identifier = channel_identifier[1:]
            entity = await self.client.get_entity(channel_identifier)
            if not entity:
                return None
            if hasattr(entity, 'id'):
                try:
                    full_channel = await self.client(GetFullChannelRequest(entity))
                    full_info = full_channel.full_chat
                except Exception as e:
                    logger.warning(f"Could not get full channel info for {channel_identifier}: {e}")
                    full_info = None
            else:
                full_info = None
            channel_info = {
                'id': getattr(entity, 'id', None),
                'username': getattr(entity, 'username', None),
                'title': getattr(entity, 'title', None),
                'verified': getattr(entity, 'verified', False),
                'scam': getattr(entity, 'scam', False),
                'fake': getattr(entity, 'fake', False),
                'type': type(entity).__name__,
                'access_hash': getattr(entity, 'access_hash', None),
            }
            if full_info:
                channel_info.update({
                    'description': getattr(full_info, 'about', None),
                    'participants_count': getattr(full_info, 'participants_count', None),
                    'admins_count': getattr(full_info, 'admins_count', None),
                    'kicked_count': getattr(full_info, 'kicked_count', None),
                    'banned_count': getattr(full_info, 'banned_count', None),
                    'online_count': getattr(full_info, 'online_count', None),
                    'chat_photo': str(getattr(full_info, 'chat_photo', None)),
                    'exported_invite': str(getattr(full_info, 'exported_invite', None)),
                    'pinned_msg_id': getattr(full_info, 'pinned_msg_id', None),
                    'linked_chat_id': getattr(full_info, 'linked_chat_id', None),
                    'slowmode_seconds': getattr(full_info, 'slowmode_seconds', None),
                    'ttl_period': getattr(full_info, 'ttl_period', None),
                })
            return channel_info
        except Exception as e:
            logger.error(f"Error getting channel info for {channel_identifier}: {e}")
            return None

    async def process_message(self, message: Message) -> List[Dict[str, Any]]:
        links = []
        # Main text
        if getattr(message, 'message', None):
            links.extend(self.extract_links_from_text(message.message, message.id, getattr(message, 'chat_id', None), context="text"))
        # Caption
        if hasattr(message, 'caption') and getattr(message, 'caption', None):
            links.extend(self.extract_links_from_text(message.caption, message.id, getattr(message, 'chat_id', None), context="caption"))
        # Entities (URLs)
        links.extend(self.extract_links_from_entities(message))
        # Reply markup (buttons)
        links.extend(self.extract_links_from_reply_markup(message))
        # Debug output
        if links:
            logger.info(f"[DEBUG] Message {message.id}: Found {len(links)} link(s)")
        return links

    async def extract_links_from_channel(
        self, 
        channel_identifier: str, 
        limit: int = 1000,
        save_to_file: bool = True,
        output_file: str = "extracted_links.json"
    ) -> Dict[str, Any]:
        try:
            if not channel_identifier.startswith('@'):
                channel_identifier = f"@{channel_identifier}"
            entity = await self.client.get_entity(channel_identifier)
            if not entity:
                raise ValueError(f"Could not find channel: {channel_identifier}")
            logger.info(f"Starting link extraction from: {getattr(entity, 'title', channel_identifier)}")
            channel_info = await self.get_channel_info(channel_identifier)
            results = {
                'extraction_info': {
                    'channel_identifier': channel_identifier,
                    'channel_info': channel_info,
                    'extraction_date': datetime.now().isoformat(),
                    'message_limit': limit,
                    'total_messages_processed': 0,
                    'total_links_found': 0,
                },
                'links': [],
                'statistics': {
                    'link_types': {},
                    'unique_links': 0,
                }
            }
            message_count = 0
            total_links = 0
            async for message in self.client.iter_messages(entity, limit=limit):
                message_count += 1
                message_links = await self.process_message(message)
                total_links += len(message_links)
                results['links'].extend(message_links)
                for link in message_links:
                    link_type = link['context']
                    results['statistics']['link_types'][link_type] = results['statistics']['link_types'].get(link_type, 0) + 1
                if message_count % 100 == 0:
                    logger.info(f"Processed {message_count} messages, total links so far: {total_links}")
            results['extraction_info']['total_messages_processed'] = message_count
            results['extraction_info']['total_links_found'] = total_links
            results['statistics']['unique_links'] = len({l['link'] for l in results['links']})
            if save_to_file:
                self.save_links_to_file(results, output_file)
            logger.info(f"Extraction completed: {total_links} links found from {message_count} messages")
            logger.info(f"Unique links found: {results['statistics']['unique_links']}")
            return results
        except Exception as e:
            logger.error(f"Error extracting links from channel {channel_identifier}: {e}")
            raise

    def save_links_to_file(self, results: Dict[str, Any], output_file: str):
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Links saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving links to file: {e}")
            raise 