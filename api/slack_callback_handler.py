from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from utils.logger import logger
from config.settings import Config
from utils.share_agent import ShareAgent
import hmac
import hashlib
import json
import time

router = APIRouter()

class SlackEvent(BaseModel):
    type: str
    user: Optional[Dict[str, Any]]
    payload: Optional[Dict[str, Any]]

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

@router.post("/interactive")
async def slack_interactive(request: Request):
    """Handle interactive actions from Slack"""
    try:
        # Get raw body and headers for verification
        body = await request.body()
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")
        
        # Verify the request
        if not verify_slack_signature(body, timestamp, signature):
            raise HTTPException(status_code=401, detail="Invalid request signature")

        # Parse the form data
        form_data = await request.form()
        payload = json.loads(form_data.get("payload", "{}"))
        
        logger.info(f"Received Slack interaction: {payload.get('type')}")
        
        # Extract action and relevant data
        action = payload.get("actions", [{}])[0].get("value")
        user = payload.get("user", {}).get("name", "unknown")
        
        if action == "approve":
            # Extract message blocks
            message_blocks = payload.get("message", {}).get("blocks", [])
            
            # Extract title from header block
            header_block = next(
                (block for block in message_blocks if block.get("type") == "header"), 
                None
            )
            title = header_block.get("text", {}).get("text", "").replace("🚨 ", "") if header_block else ""
            
            # Extract content from section block
            content_block = next(
                (block for block in message_blocks if block.get("type") == "section"), 
                None
            )
            
            if not content_block:
                raise HTTPException(status_code=400, detail="Could not find post content")
                
            content = (
                content_block.get("text", {})
                .get("text", "")
                .replace("*Content:*\n", "")
                .strip()
            )
            
            try:
                # Initialize ShareAgent
                share_agent = ShareAgent()
                
                # Execute sharing with both title and content
                result = share_agent._run({
                    "title": title,
                    "content": content,
                    "visibility": "connections"
                })
                
                if result.get("success"):
                    logger.info(f"Post successfully shared by {user}")
                    return JSONResponse(
                        content={
                            "response_type": "in_channel",
                            "replace_original": True,
                            "text": f"✅ Post approved and shared successfully by {user}!"
                        }
                    )
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Failed to share post: {error_msg}")
                    return JSONResponse(
                        content={
                            "response_type": "in_channel",
                            "replace_original": True,
                            "text": f"❌ Error sharing post: {error_msg}"
                        }
                    )
                    
            except Exception as e:
                logger.error(f"Error in share agent: {str(e)}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "response_type": "in_channel",
                        "replace_original": True,
                        "text": f"❌ Internal error while sharing post: {str(e)}"
                    }
                )
                
        elif action == "regenerate":
            logger.info(f"Content regeneration requested by {user}")
            
            try:
                # Get scheduler from app state
                scheduler = request.app.state.scheduler
                notification_tool = request.app.state.notification_tool
                
                # Extract the original message content
                message_blocks = payload.get("message", {}).get("blocks", [])
                
                # Get original title from header block
                header_block = next(
                    (block for block in message_blocks if block.get("type") == "header"), 
                    None
                )
                original_title = header_block.get("text", {}).get("text", "").replace("📝 ", "") if header_block else ""
                
                # Send initial notification about regeneration
                notification_result = notification_tool._run({
                    "context": {
                        "title": f"Regenerating: {original_title}",
                        "content": f"🔄 Content regeneration requested by {user}. Starting new generation process..."
                    }
                })
                
                if not notification_result.get("sent"):
                    raise Exception("Failed to send notification")
                
                # Trigger new workflow execution
                await scheduler.execute_crew_workflow()
                
                return JSONResponse(
                    content={
                        "response_type": "in_channel",
                        "replace_original": True,
                        "text": f"🔄 Content regeneration initiated by {user}. A new post will be generated and sent for review."
                    }
                )
                
            except Exception as e:
                logger.error(f"Error during regeneration: {str(e)}")
                return JSONResponse(
                    content={
                        "response_type": "in_channel",
                        "replace_original": True,
                        "text": f"❌ Error regenerating content: {str(e)}"
                    }
                )
            
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    except Exception as e:
        logger.error(f"Error processing Slack interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))