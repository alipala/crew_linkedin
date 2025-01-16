# api/slack_message_handler.py

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import requests
from utils.logger import logger
from utils.topic_manager import TopicManager
from config.settings import Config
import hmac
import hashlib
import json
import time
from fastapi import APIRouter, Request, HTTPException, Response

router = APIRouter()
topic_manager = TopicManager()

def verify_slack_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    """Verify that the request came from Slack"""
    if not Config.SLACK_SIGNING_SECRET:
        logger.error("Slack signing secret not configured")
        return False
        
    if abs(time.time() - int(timestamp)) > 300:
        logger.error("Request timestamp too old")
        return False
        
    base_string = f"v0:{timestamp}:{request_body.decode()}"
    computed_signature = (
        f"v0={hmac.new(Config.SLACK_SIGNING_SECRET.encode(), base_string.encode(), hashlib.sha256).hexdigest()}"
    )
    return hmac.compare_digest(computed_signature, signature)

async def handle_message_event(event_data: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Handle incoming Slack messages"""
    try:
        text = event_data.get('event', {}).get('text', '').strip().lower()
        channel = event_data.get('event', {}).get('channel')
        user = event_data.get('event', {}).get('user')
        
        # Ignore bot messages to prevent loops
        if event_data.get('event', {}).get('bot_id'):
            return None
        
        if text.startswith('hello!'):
            return {
                'response_type': 'in_channel',
                'channel': channel,
                'text': (
                    "👋 Hello! I'm ready to help you manage AI topics.\n"
                    "*Available commands:*\n"
                    "• `add: topic1, topic2, ...` - Add new topics\n"
                    "• `show topics` - Display current topics\n"
                    "• `clear topics` - Reset to default topics\n"
                    "• `start scan` - Begin scanning with current topics"
                )
            }
            
        elif text.startswith('add:'):
            # Extract topics after 'add:'
            new_topics = text[4:].strip()
            success, current_topics = topic_manager.add_topics(new_topics)
            
            if success:
                response = (
                    "✅ Topics updated successfully!\n"
                    "*Current topics:*\n" + 
                    "\n".join(f"• {topic}" for topic in current_topics)
                )
            else:
                response = "❌ Failed to update topics. Please try again."
                
            return {
                'response_type': 'in_channel',
                'channel': channel,
                'text': response
            }
            
        elif text == 'show topics':
            current_topics = topic_manager.get_current_topics()
            return {
                'response_type': 'in_channel',
                'channel': channel,
                'text': "*Current topics:*\n" + 
                        "\n".join(f"• {topic}" for topic in current_topics)
            }
            
        elif text == 'clear topics':
            if topic_manager.clear_topics():
                return {
                    'response_type': 'in_channel',
                    'channel': channel,
                    'text': "✅ Topics reset to defaults."
                }
            return {
                'response_type': 'in_channel',
                'channel': channel,
                'text': "❌ Failed to reset topics."
            }
            
        elif text == 'start scan':
            # Get scheduler from app state for execution
            scheduler = request.app.state.scheduler
            current_topics = topic_manager.get_current_topics()
            
            # Simplified input structure
            await scheduler.execute_crew_workflow({
                'topics': current_topics  # Just pass topics directly
            })
            
            return {
                'response_type': 'in_channel',
                'channel': channel,
                'text': (
                    "🚀 Starting LinkedIn post scan with the following topics:\n" +
                    "\n".join(f"• {topic}" for topic in current_topics)
                )
            }
            
        return None
            
    except Exception as e:
        logger.error(f"Error handling Slack message: {e}")
        return {
            'response_type': 'in_channel',
            'channel': channel,
            'text': f"❌ Error processing command: {str(e)}"
        }

@router.post("/events")
async def slack_events(request: Request):
    """Handle Slack events with deduplication and improved error handling"""
    try:
        # Get raw body
        body = await request.body()
        body_str = body.decode()
        logger.debug(f"Received body: {body_str}")
        
        # Parse JSON body
        event_data = json.loads(body_str)
        
        # Handle URL verification without signature check
        if event_data.get('type') == 'url_verification':
            challenge = event_data.get('challenge')
            logger.info(f"Handling URL verification. Challenge: {challenge}")
            return Response(
                content=json.dumps({"challenge": challenge}),
                media_type="application/json"
            )
            
        # For other events, verify signature
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")
        
        logger.debug(f"Headers - Timestamp: {timestamp}, Signature: {signature}")
        
        if not verify_slack_signature(body, timestamp, signature):
            logger.error("Invalid Slack signature")
            raise HTTPException(status_code=401, detail="Invalid request signature")

        # Deduplication check
        event_id = event_data.get('event_id')
        if not hasattr(request.app.state, 'processed_events'):
            request.app.state.processed_events = set()
            
        if event_id in request.app.state.processed_events:
            logger.info(f"Duplicate event {event_id} - skipping processing")
            return Response(
                content=json.dumps({'ok': True}),
                media_type="application/json"
            )
            
        # Store event_id for deduplication
        request.app.state.processed_events.add(event_id)
        
        # Cleanup old events (keep last 1000)
        if len(request.app.state.processed_events) > 1000:
            request.app.state.processed_events = set(list(request.app.state.processed_events)[-1000:])

        # Handle message events
        if event_data.get('event', {}).get('type') == 'message':
            # Ignore bot messages to prevent loops
            if event_data.get('event', {}).get('bot_id'):
                return Response(
                    content=json.dumps({'ok': True}),
                    media_type="application/json"
                )
                
            response = await handle_message_event(event_data, request)
            if response:
                # Send message back to Slack
                slack_response = requests.post(
                    'https://slack.com/api/chat.postMessage',
                    headers={
                        'Authorization': f'Bearer {Config.SLACK_BOT_TOKEN}',
                        'Content-Type': 'application/json'
                    },
                    json=response
                )
                
                if not slack_response.ok:
                    logger.error(f"Error sending Slack message: {slack_response.text}")
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to send Slack message"
                    )
                    
                logger.info("Successfully sent Slack message")
                
            return Response(
                content=json.dumps({'ok': True}),
                media_type="application/json"
            )
            
        return Response(
            content=json.dumps({'ok': True}),
            media_type="application/json"
        )
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    except Exception as e:
        logger.error(f"Error in Slack events endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))