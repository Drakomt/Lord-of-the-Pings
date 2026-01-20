# Lord of the Pings - JSON Message Protocol

## Overview
The client-server communication has been refactored from string-based messages to a clean JSON protocol. All messages follow a standard envelope format.

## Message Envelope Format
```json
{
  "type": "MESSAGE_TYPE",
  "data": { /* type-specific fields */ }
}
```

## Message Types

### 1. CHAT - Regular Chat Messages
**Sent by:** Client to Server
**Purpose:** Send regular chat messages to general or private chats

```json
{
  "type": "CHAT",
  "data": {
    "sender": "username",
    "recipient": "general | username",
    "text": "message content"
  }
}
```

---

### 2. SYSTEM - System Messages
**Sent by:** Server to Client
**Purpose:** Broadcast system events (user joined/left)

```json
{
  "type": "SYSTEM",
  "data": {
    "text": "username joined the chat",
    "chat_id": "general | username"
  }
}
```

---

### 3. USERLIST - Online Users List
**Sent by:** Server to Client
**Purpose:** Update list of currently online users

```json
{
  "type": "USERLIST",
  "data": {
    "users": ["user1", "user2", "user3"]
  }
}
```

---

### 4. AVATAR - Avatar Update
**Sent by:** Server to all clients OR Client to Server
**Purpose:** Update a user's avatar

**Server → Client:**
```json
{
  "type": "AVATAR",
  "data": {
    "username": "username",
    "avatar": "avatar_filename.png"
  }
}
```

**Client → Server (SET_AVATAR):**
```json
{
  "type": "SET_AVATAR",
  "data": {
    "avatar": "avatar_filename.png"
  }
}
```

---

### 5. AVATAR_ERROR - Avatar Change Failed
**Sent by:** Server to Client
**Purpose:** Notify client that avatar change failed

```json
{
  "type": "AVATAR_ERROR",
  "data": {}
}
```

---

### 6. GAME_INVITE - Game Invitation
**Sent by:** Client to Server
**Purpose:** Send a game invite to another player

```json
{
  "type": "GAME_INVITE",
  "data": {
    "opponent": "opponent_username"
  }
}
```

---

### 7. GAME_ACCEPTED - Game Invite Accepted
**Sent by:** Client to Server
**Purpose:** Accept a game invite and specify chosen symbol

```json
{
  "type": "GAME_ACCEPTED",
  "data": {
    "player": "accepting_username",
    "symbol": "X | O"
  }
}
```

---

### 8. GAME_MOVE - Game Move
**Sent by:** Client to Server
**Purpose:** Send game board state and current player

```json
{
  "type": "GAME_MOVE",
  "data": {
    "board": [null, "X", "O", null, "X", null, null, null, "O"],
    "current_player": "X | O"
  }
}
```

---

### 9. GAME_END - Game Ended
**Sent by:** Client to Server
**Purpose:** Notify opponent that game is over with result

```json
{
  "type": "GAME_END",
  "data": {
    "result": "X | O | DRAW"
  }
}
```

---

### 10. GAME_RESET - New Game Started
**Sent by:** Client to Server
**Purpose:** Initiate new game with chosen symbol

```json
{
  "type": "GAME_RESET",
  "data": {
    "player": "username",
    "symbol": "X | O"
  }
}
```

---

### 11. GAME_LEFT - Game Exit
**Sent by:** Client to Server
**Purpose:** Notify opponent that player left the game

```json
{
  "type": "GAME_LEFT",
  "data": {
    "player": "username"
  }
}
```

---

## Implementation Notes

### Client-Side Helpers
Two helper functions handle JSON serialization/deserialization:

```python
def send_json_message(sock, msg_type, data):
    """Send a JSON-encoded message through socket"""
    payload = {"type": msg_type, "data": data}
    sock.sendall(json.dumps(payload).encode())

def parse_json_message(raw_string):
    """Try to parse string as JSON, return dict or None"""
    try:
        return json.loads(raw_string)
    except:
        return None
```

### Message Routing
The client's `route_json_message()` method handles incoming JSON messages and routes them to appropriate handlers based on message type.

### Backward Compatibility
The `listen_to_server()` method first attempts to parse messages as JSON. If JSON parsing fails, it falls back to the legacy string protocol, ensuring partial backward compatibility during transition.

## Advantages

1. **Extensibility** - Easy to add new fields without breaking parsing
2. **Clarity** - Human-readable format for debugging
3. **Type Safety** - Clear structure for each message
4. **Scalability** - Supports complex data like nested game board state
5. **Professional** - Industry-standard approach
6. **Maintainability** - Reduces brittle string parsing logic

## Migration Path

If the server needs updating:
1. Server should also adopt the same JSON envelope format
2. Messages should be serialized/deserialized consistently
3. Consider phased migration with fallback to old format
4. Use same message type names and data structure

## Example Flow

### Chat Message
```
Client sends:
{"type": "CHAT", "data": {"sender": "Alice", "recipient": "general", "text": "Hello!"}}

Server broadcasts to all clients:
{"type": "CHAT", "data": {"sender": "Alice", "recipient": "general", "text": "Hello!"}}
```

### Game Invitation Flow
```
1. Client sends invite:
   {"type": "GAME_INVITE", "data": {"opponent": "Bob"}}

2. Server broadcasts to Bob:
   {"type": "GAME_INVITE", "data": {"opponent": "Alice"}}

3. Bob accepts:
   {"type": "GAME_ACCEPTED", "data": {"player": "Bob", "symbol": "O"}}

4. Server broadcasts acceptance to Alice:
   {"type": "GAME_ACCEPTED", "data": {"player": "Bob", "symbol": "O"}}

5. Game begins with move exchange using GAME_MOVE messages
```
