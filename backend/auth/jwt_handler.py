from datetime import datetime, timedelta
from typing import Dict, Optional
from jose import jwt, JWTError
from fastapi import WebSocket, WebSocketException, status
from config import settings

def create_access_token(user_id: str, tenant_id: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role
    }
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[Dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

async def authenticate_websocket(websocket: WebSocket) -> Dict:
    """Validate token passed as a query parameter for WebSocket connection."""
    token = websocket.query_params.get("token")
    if not token:
        # Check first header if no query param
        auth_header = websocket.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        
    claims = decode_token(token)
    if not claims:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        
    return claims
