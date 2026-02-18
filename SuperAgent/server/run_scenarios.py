
import asyncio
import httpx
import json
import time

BASE_URL = "http://localhost:8000"

async def get_session(client: httpx.AsyncClient):
    """Get a new session token."""
    try:
        response = await client.post(f"{BASE_URL}/api/session")
        if response.status_code != 200:
            print(f"Error creating session: {response.status_code}")
            print(response.text)
            return None
        return response.json()
    except Exception as e:
        print(f"Connection error: {e}")
        return None

async def run_chat(token: str, message: str):
    """Send a message and stream the response."""
    print(f"\n--- Sending: '{message}' ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # We will send the message using a different client or request, 
    # but for SSE we need a persistent connection often.
    # However, the API is POST /api/chat which returns the stream.
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            async with client.stream("POST", f"{BASE_URL}/api/chat", json={"message": message}, headers=headers) as response:
                if response.status_code != 200:
                    print(f"Error: {response.status_code}")
                    await response.aread()
                    print(response.text)
                    return

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_str)
                        if data.get("type") == "token":
                            print(data.get("content", ""), end="", flush=True)
                        elif data.get("type") == "error":
                            print(f"\n[ERROR] {data.get('content')}")
                        elif data.get("type") == "done":
                            print("\n[DONE]")
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
           print(f"Error during chat: {e}")

async def run_scenarios():
    """Run a list of scenarios."""
    scenarios = [
        "Hello",
        "I need internet for 123 Market St, Philadelphia, PA 19107",
        "What is the speed of Fiber 5G?",
        "I'd like to get a quote for Fiber 5G at that address.",
    ]
    
    async with httpx.AsyncClient() as client:
        print("Authenticating...")
        session_data = await get_session(client)
        if not session_data:
            print("Failed to authenticate. Is the server running?")
            return

        token = session_data["token"]
        session_id = session_data["session_id"]
        print(f"Authenticated. Session ID: {session_id}")

        for scenario in scenarios:
            await run_chat(token, scenario)
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(run_scenarios())
    except KeyboardInterrupt:
        print("\nStopped.")
