"""
Pydantic models for FoodLink LA
Defines data structures for API requests/responses and internal data handling
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from datetime import datetime


# ============================================================================
# MESSAGE MODELS
# ============================================================================

class Message(BaseModel):
    """A single message in a conversation"""
    role: Literal["user", "assistant"]
    content: str


# ============================================================================
# RESOURCE MODELS
# ============================================================================

class Hours(BaseModel):
    """Operating hours for a single day"""
    open: Optional[str] = None
    close: Optional[str] = None
    status: Literal["open", "closed", "variable"] = "closed"


class Resource(BaseModel):
    """A food resource (pantry, meal service, etc.)"""
    id: str
    name: str
    type: str
    address: str
    lat: float
    lon: float
    phone: str
    email: Optional[str] = None
    website: Optional[str] = None
    hours: Dict[str, Hours]
    offerings: List[str]
    dietary_options: List[str]
    requirements: str
    accessibility: str
    languages: List[str]
    notes: str
    target_population: str
    
    # Computed fields (added at runtime)
    distance_miles: Optional[float] = None
    is_open_now: Optional[bool] = None


# ============================================================================
# CHAT API MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """Request to the chat endpoint"""
    session_id: str = Field(..., description="Unique session identifier for conversation continuity")
    message: str = Field(..., description="User's message")
    agent_type: Literal["recipient", "donor"] = Field(
        default="recipient",
        description="Type of agent to use"
    )
    location: Optional[str] = Field(
        None,
        description="User's location (address, intersection, or landmark)"
    )


class ChatResponse(BaseModel):
    """Response from the chat endpoint"""
    response: str = Field(..., description="Agent's response message")
    resources: Optional[List[Resource]] = Field(
        None,
        description="Relevant food resources (if applicable)"
    )
    session_id: str = Field(..., description="Session identifier")


# ============================================================================
# DONATION MODELS
# ============================================================================

class DonationRequest(BaseModel):
    """Request to donate food"""
    donor_type: Literal["grocery", "restaurant", "household"]
    food_items: List[str] = Field(..., description="List of food items to donate")
    quantity: str = Field(..., description="Quantity/amount of food")
    expiration_date: Optional[str] = Field(None, description="Expiration date (if applicable)")
    location: str = Field(..., description="Pickup location")
    contact_phone: str = Field(..., description="Contact phone number")
    notes: Optional[str] = Field(None, description="Additional notes")


class DonationResponse(BaseModel):
    """Response to donation submission"""
    donation_id: str
    status: Literal["accepted", "pending_review", "rejected"]
    message: str
    matched_organization: Optional[str] = None


# ============================================================================
# RESOURCE QUERY MODELS
# ============================================================================

class ResourceQuery(BaseModel):
    """Query parameters for searching resources"""
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_text: Optional[str] = None
    max_distance_miles: float = Field(default=5.0, ge=0.1, le=50.0)
    dietary_needs: List[str] = Field(default_factory=list)
    open_now: bool = False
    resource_types: List[str] = Field(default_factory=list)


# ============================================================================
# AGENT SESSION MODELS
# ============================================================================

class AgentSession(BaseModel):
    """Represents an ongoing agent conversation session"""
    session_id: str
    agent_type: Literal["recipient", "donor"]
    conversation_history: List[Message] = Field(default_factory=list)
    user_location: Optional[str] = None
    dietary_needs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)


# ============================================================================
# SYSTEM MODELS
# ============================================================================

class HealthCheck(BaseModel):
    """Health check response"""
    status: Literal["healthy", "degraded", "unhealthy"]
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    components: Dict[str, str] = Field(default_factory=dict)
