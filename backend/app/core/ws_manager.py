from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # room_id -> {player_id: websocket}
        self.rooms: dict[str, dict[str, WebSocket]] = {}
        # room_id -> host websocket
        self.hosts: dict[str, WebSocket] = {}

    async def connect_player(self, room_id: str, player_id: str, ws: WebSocket):
        await ws.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        self.rooms[room_id][player_id] = ws

    async def connect_host(self, room_id: str, ws: WebSocket):
        await ws.accept()
        self.hosts[room_id] = ws

    def disconnect_player(self, room_id: str, player_id: str):
        if room_id in self.rooms:
            self.rooms[room_id].pop(player_id, None)
            if not self.rooms[room_id]:
                del self.rooms[room_id]

    def disconnect_host(self, room_id: str):
        self.hosts.pop(room_id, None)

    async def send_to_player(self, room_id: str, player_id: str, data: dict):
        ws = self.rooms.get(room_id, {}).get(player_id)
        if ws:
            await ws.send_json(data)

    async def broadcast_to_players(self, room_id: str, data: dict):
        for ws in self.rooms.get(room_id, {}).values():
            await ws.send_json(data)

    async def send_to_host(self, room_id: str, data: dict):
        ws = self.hosts.get(room_id)
        if ws:
            await ws.send_json(data)

    async def broadcast_to_all(self, room_id: str, data: dict):
        """Send to all players AND host."""
        await self.broadcast_to_players(room_id, data)
        await self.send_to_host(room_id, data)

    def get_player_count(self, room_id: str) -> int:
        return len(self.rooms.get(room_id, {}))


ws_manager = ConnectionManager()