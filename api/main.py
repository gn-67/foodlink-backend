"""
FoodLink LA - Main FastAPI Application
A 24/7 AI-powered food access network for West Los Angeles
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import (
    ChatRequest,
    ChatResponse,
    ResourceQuery,
    Resource,
    HealthCheck,
)
from agents import RecipientAgent, DonorAgent
from data.database import get_database


# Load environment variables
load_dotenv()

# Verify API key is set
if not os.getenv("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY environment variable must be set")


# Initialize FastAPI app
app = FastAPI(
    title="FoodLink LA API",
    description="AI-powered food access network for West Los Angeles",
    version="1.0.0",
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory session storage (for MVP - would use Redis in production)
agent_sessions: Dict[str, Union[RecipientAgent, DonorAgent]] = {}


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.get("/", response_model=HealthCheck)
async def root():
    """Root endpoint - health check"""
    return HealthCheck(
        status="healthy",
        message="FoodLink LA API is running",
        components={
            "api": "healthy",
            "database": "healthy",
            "anthropic": "configured"
        }
    )


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Detailed health check"""
    db = get_database()
    resource_count = len(db.get_all_resources())
    
    components = {
        "api": "healthy",
        "database": f"healthy ({resource_count} resources loaded)",
        "anthropic_api": "configured" if os.getenv("ANTHROPIC_API_KEY") else "not configured"
    }
    
    status = "healthy" if all(v != "not configured" for v in components.values()) else "degraded"
    
    return HealthCheck(
        status=status,
        message=f"FoodLink LA API - {resource_count} resources available",
        components=components
    )


# ============================================================================
# CHAT ENDPOINT
# ============================================================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for conversing with AI agents
    
    Handles both recipient (finding food) and donor (donating food) conversations
    """
    try:
        # Get or create agent for this session
        if request.session_id not in agent_sessions:
            # Create new agent based on type
            if request.agent_type == "recipient":
                agent = RecipientAgent(
                    session_id=request.session_id,
                    location=request.location
                )
            else:  # donor
                agent = DonorAgent(session_id=request.session_id)
            
            agent_sessions[request.session_id] = agent
        else:
            agent = agent_sessions[request.session_id]
        
        # Update location if provided for recipient agents
        if isinstance(agent, RecipientAgent) and request.location:
            agent.update_location(request.location)
        
        # Process the message
        response_text = await agent.process_message(request.message)
        
        # For recipient agents, try to provide relevant resources
        resources = None
        if isinstance(agent, RecipientAgent):
            # Simple heuristic: if the response mentions specific locations or if user asked about food
            # In a production system, we'd use NLP or function calling to determine when to fetch resources
            should_fetch_resources = any(keyword in request.message.lower() for keyword in [
                "food", "eat", "hungry", "meal", "pantry", "near", "help", "where", "find"
            ])
            
            if should_fetch_resources and agent.location:
                db = get_database()
                # Try to extract location info - for MVP, we'll use known landmarks
                resources = _get_resources_for_location(agent.location, agent.dietary_needs)
        
        return ChatResponse(
            response=response_text,
            resources=resources,
            session_id=request.session_id
        )
    
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RESOURCES ENDPOINT
# ============================================================================

@app.get("/api/resources", response_model=List[Resource])
async def get_resources(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    location_text: Optional[str] = None,
    max_distance_miles: float = 5.0,
    dietary_needs: Optional[str] = None,
    open_now: bool = False,
    limit: int = 10
):
    """
    Get food resources based on search criteria
    
    Query Parameters:
    - lat, lon: User's coordinates
    - location_text: Location description (alternative to lat/lon)
    - max_distance_miles: Search radius
    - dietary_needs: Comma-separated dietary requirements (e.g., "vegan,gluten-free")
    - open_now: Only show resources open right now
    - limit: Maximum number of results
    """
    try:
        db = get_database()
        
        # Parse dietary needs
        dietary_list = []
        if dietary_needs:
            dietary_list = [need.strip() for need in dietary_needs.split(",")]
        
        # If location_text provided, try to geocode it (simplified for MVP)
        if location_text and not (lat and lon):
            lat, lon = _geocode_location_text(location_text)
        
        # Search resources
        resources = db.search_resources(
            lat=lat,
            lon=lon,
            max_distance_miles=max_distance_miles,
            dietary_needs=dietary_list,
            open_now=open_now,
            limit=limit
        )
        
        return resources
    
    except Exception as e:
        print(f"❌ Error in resources endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/resources/{resource_id}", response_model=Resource)
async def get_resource(resource_id: str):
    """Get a specific resource by ID"""
    try:
        db = get_database()
        resource = db.get_resource_by_id(resource_id)
        
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        
        return resource
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get resource endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_resources_for_location(location: str, dietary_needs: List[str]) -> Optional[List[Resource]]:
    """
    Helper to get resources based on a location string
    In production, this would use a proper geocoding service
    """
    db = get_database()
    
    # Known landmark coordinates for West LA
    landmarks = {
        "ucla": (34.0689, -118.4452),
        "westwood": (34.0689, -118.4452),
        "santa monica": (34.0195, -118.4912),
        "venice": (33.9850, -118.4695),
        "culver city": (34.0211, -118.3965),
        "west la": (34.0522, -118.4437),
        "west hollywood": (34.0900, -118.3617),
    }
    
    location_lower = location.lower()
    
    # Find matching landmark
    for landmark, coords in landmarks.items():
        if landmark in location_lower:
            resources = db.search_resources(
                lat=coords[0],
                lon=coords[1],
                max_distance_miles=3.0,
                dietary_needs=dietary_needs,
                limit=3
            )
            return resources if resources else None
    
    return None


def _geocode_location_text(location_text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Simple geocoding for known West LA locations
    In production, use Google Maps API or similar
    """
    landmarks = {
        "ucla": (34.0689, -118.4452),
        "westwood": (34.0689, -118.4452),
        "santa monica": (34.0195, -118.4912),
        "venice": (33.9850, -118.4695),
        "culver city": (34.0211, -118.3965),
        "west la": (34.0522, -118.4437),
        "west hollywood": (34.0900, -118.3617),
    }
    
    location_lower = location_text.lower()
    for landmark, coords in landmarks.items():
        if landmark in location_lower:
            return coords
    
    return None, None


# ============================================================================
# STARTUP EVENT
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database and resources on startup"""
    print("\n" + "="*60)
    print("🚀 FoodLink LA API Starting Up")
    print("="*60)
    
    # Load database
    db = get_database()
    resource_count = len(db.get_all_resources())
    
    print(f"✅ Loaded {resource_count} food resources")
    print(f"✅ Anthropic API configured")
    print(f"✅ Server ready at http://localhost:8000")
    print(f"✅ API docs available at http://localhost:8000/docs")
    print("="*60 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)