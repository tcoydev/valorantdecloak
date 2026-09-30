import time
import websockets
import websockets.client
import ssl
import base64
import json
import asyncio

# How often to force a refresh while idling in a given state, even if no
# state-change event arrives (e.g. someone joins the party, mode changes,
# or agents get picked in agent select).
REFRESH_INTERVALS = {
    "MENUS": 5,    # lobby: party members / game mode
    "PREGAME": 2,  # agent select: selected agents
}

class Ws:
    def __init__(self, lockfile, Requests, cfg, rpc=None):
        self.lockfile = lockfile
        self.Requests = Requests
        self.log = Requests.log  # Inherit logger from Requests
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self.cfg = cfg
        if self.cfg.get_feature_flag("discord_rpc"):
            self.rpc = rpc

    async def recconect_to_websocket(self, initial_game_state):
        local_headers = {
            'Authorization': 'Basic ' + base64.b64encode(('riot:' + self.lockfile['password']).encode()).decode()
        }
        url = f"wss://127.0.0.1:{self.lockfile['port']}"
        
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                async with websockets.connect(url, ssl=self.ssl_context, extra_headers=local_headers) as websocket:
                    await websocket.send('[5, "OnJsonApiEvent_chat_v4_presences"]')

                    # Force a periodic refresh on a fixed interval. We use an
                    # absolute deadline so that a busy stream of presence events
                    # (other players in the lobby) can't keep pushing it back.
                    refresh_interval = REFRESH_INTERVALS.get(initial_game_state)
                    deadline = time.monotonic() + refresh_interval if refresh_interval else None

                    while True:
                        if deadline is not None:
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                # Re-render the current state (party/mode/agents).
                                return initial_game_state
                            recv_timeout = remaining
                        else:
                            recv_timeout = 5

                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=recv_timeout)
                        except asyncio.TimeoutError:
                            if deadline is not None:
                                return initial_game_state
                            continue
                        result = self.handle(response, initial_game_state)
                        if result is not None:
                            return result
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.InvalidURI, websockets.exceptions.InvalidHandshake, ConnectionRefusedError, OSError) as e:
                self.log(f"Websocket failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.log(f"Websocket failed after {max_retries} attempts.")
                    return "DISCONNECTED"
            except Exception as e:
                self.log(f"Unexpected websocket error: {e}")
                return "DISCONNECTED"
        
        return "DISCONNECTED"

    def handle(self, m, initial_game_state):
        try:
            if not m or len(m) <= 10:
                return None
            resp_json = json.loads(m)
        except (json.JSONDecodeError, TypeError):
            self.log(f"JSONDecodeError: Failed to parse websocket message. Data: {m}")
            return None

        if resp_json[2].get("uri") == "/chat/v4/presences":
            presence = resp_json[2].get("data", {}).get("presences", [{}])[0]
            if presence.get('puuid') == self.Requests.puuid:
                
                if presence.get("product") == "league_of_legends":
                    return None
                
                try:
                    private_data = json.loads(base64.b64decode(presence['private']))
                    
                    # Temp fix: Riot is swapping between nested and flat API structures.
                    state = None
                    if "matchPresenceData" in private_data: # Check for nested structure
                        state = private_data.get("matchPresenceData", {}).get("sessionLoopState")
                    elif "sessionLoopState" in private_data: # Check for flattened structure
                        state = private_data.get("sessionLoopState")
                    else:
                        # No known structure found, log and fail
                        self.log(f"ERROR: Unknown presence API structure in 'websocket.handle': {private_data}")
                        state = private_data["matchPresenceData"]["sessionLoopState"]

                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    self.log(f"Failed to decode private presence data: {e}")
                    state = None

                if state is not None:
                    if self.cfg.get_feature_flag("discord_rpc") and private_data:
                        self.rpc.set_rpc(private_data)
                    if state != initial_game_state:
                        return state

        return None
