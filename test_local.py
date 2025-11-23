"""
Simple test script for FoodLink LA
Run this after starting the server to test the API
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_health_check():
    """Test the health check endpoint"""
    print_section("Testing Health Check")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200


def test_resources():
    """Test the resources endpoint"""
    print_section("Testing Resources Endpoint")
    
    # Test 1: Get all resources near UCLA
    print("\n📍 Test: Resources near UCLA")
    response = requests.get(
        f"{BASE_URL}/api/resources",
        params={
            "location_text": "UCLA",
            "limit": 5
        }
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        resources = response.json()
        print(f"Found {len(resources)} resources")
        for r in resources[:3]:
            print(f"  - {r['name']} ({r.get('distance_miles', 'N/A')} miles)")
    
    # Test 2: Get resources open now
    print("\n🟢 Test: Resources open right now")
    response = requests.get(
        f"{BASE_URL}/api/resources",
        params={
            "location_text": "Santa Monica",
            "open_now": True,
            "limit": 3
        }
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        resources = response.json()
        print(f"Found {len(resources)} resources open now")
        for r in resources:
            print(f"  - {r['name']}")
    
    # Test 3: Dietary preferences
    print("\n🥗 Test: Vegan options near Venice")
    response = requests.get(
        f"{BASE_URL}/api/resources",
        params={
            "location_text": "Venice",
            "dietary_needs": "vegan",
            "limit": 3
        }
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        resources = response.json()
        print(f"Found {len(resources)} vegan-friendly resources")
        for r in resources:
            print(f"  - {r['name']}")


def test_chat_recipient():
    """Test the chat endpoint with recipient agent"""
    print_section("Testing Recipient Agent Chat")
    
    session_id = f"test-{datetime.now().timestamp()}"
    
    # Conversation 1: Initial greeting
    print("\n💬 User: Hi, I need help finding food")
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "session_id": session_id,
            "message": "Hi, I need help finding food",
            "agent_type": "recipient"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"🤖 Agent: {data['response'][:200]}...")
    else:
        print(f"❌ Error: {response.status_code}")
        return
    
    # Conversation 2: Provide location
    print("\n💬 User: I'm near UCLA and I'm hungry right now")
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "session_id": session_id,
            "message": "I'm near UCLA and I'm hungry right now",
            "agent_type": "recipient",
            "location": "UCLA"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"🤖 Agent: {data['response'][:300]}...")
        
        if data.get('resources'):
            print(f"\n📍 Resources returned: {len(data['resources'])}")
            for r in data['resources']:
                print(f"  - {r['name']}")
    else:
        print(f"❌ Error: {response.status_code}")


def test_chat_donor():
    """Test the chat endpoint with donor agent"""
    print_section("Testing Donor Agent Chat")
    
    session_id = f"test-donor-{datetime.now().timestamp()}"
    
    print("\n💬 User: I want to donate food")
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "session_id": session_id,
            "message": "I want to donate food from my grocery store",
            "agent_type": "donor"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"🤖 Agent: {data['response'][:300]}...")
    else:
        print(f"❌ Error: {response.status_code}")


def main():
    """Run all tests"""
    print("\n" + "🧪"*30)
    print("  FoodLink LA - Test Suite")
    print("🧪"*30)
    
    try:
        # Test 1: Health check
        if not test_health_check():
            print("\n❌ Health check failed - is the server running?")
            print("Start the server with: uvicorn api.main:app --reload")
            return
        
        # Test 2: Resources
        test_resources()
        
        # Test 3: Recipient chat
        test_chat_recipient()
        
        # Test 4: Donor chat
        test_chat_donor()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60 + "\n")
    
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to server!")
        print("Make sure the server is running:")
        print("  cd backend")
        print("  source venv/bin/activate  # or venv\\Scripts\\activate on Windows")
        print("  uvicorn api.main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
