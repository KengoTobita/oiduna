#!/bin/bash
# Demo script for new hierarchical API

set -e

BASE_URL="http://localhost:57122"

echo "=== Oiduna New Architecture Demo ==="
echo

# 1. Register client
echo "1. Registering client..."
RESPONSE=$(curl -s -X POST "$BASE_URL/clients/demo_client" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Demo Client",
    "distribution": "demo",
    "metadata": {"version": "1.0"}
  }')

TOKEN=$(echo $RESPONSE | jq -r '.token')
echo "   Client registered with token: ${TOKEN:0:8}..."
echo

# 2. Create track
echo "2. Creating track..."
curl -s -X POST "$BASE_URL/tracks/demo_track" \
  -H "X-Client-ID: demo_client" \
  -H "X-Client-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "track_name": "kick_track",
    "destination_id": "superdirt",
    "base_params": {"sound": "bd", "orbit": 0, "gain": 0.8}
  }' | jq .
echo

# 3. Create pattern
echo "3. Creating pattern with events..."
curl -s -X POST "$BASE_URL/tracks/demo_track/patterns/demo_pattern" \
  -H "X-Client-ID: demo_client" \
  -H "X-Client-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pattern_name": "main_beat",
    "active": true,
    "events": [
      {"step": 0, "cycle": 0.0, "params": {}},
      {"step": 64, "cycle": 1.0, "params": {"gain": 0.9}},
      {"step": 128, "cycle": 2.0, "params": {"gain": 1.0}},
      {"step": 192, "cycle": 3.0, "params": {"gain": 0.9}}
    ]
  }' | jq .
echo

# 4. Get session state
echo "4. Getting session state..."
curl -s -X GET "$BASE_URL/session/state" \
  -H "X-Client-ID: demo_client" \
  -H "X-Client-Token: $TOKEN" | jq '{
    bpm: .environment.bpm,
    tracks: .tracks | length,
    patterns: (.tracks | to_entries | map(.value.patterns | length) | add)
  }'
echo

# 5. Update environment
echo "5. Updating BPM to 140..."
curl -s -X PATCH "$BASE_URL/session/environment" \
  -H "X-Client-ID: demo_client" \
  -H "X-Client-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bpm": 140.0}' | jq .
echo

# 6. Sync to engine (would fail if engine not running)
echo "6. Syncing session to engine..."
curl -s -X POST "$BASE_URL/playback/sync" \
  -H "X-Client-ID: demo_client" \
  -H "X-Client-Token: $TOKEN" | jq . || echo "   (Sync requires running engine)"
echo

# 7. Admin: List destinations
echo "7. Admin: Listing destinations..."
curl -s -X GET "$BASE_URL/admin/destinations" \
  -H "X-Admin-Password: change_me_in_production" | jq '.destinations | keys'
echo

# 8. Cleanup
echo "8. Cleaning up (delete track)..."
curl -s -X DELETE "$BASE_URL/tracks/demo_track" \
  -H "X-Client-ID: demo_client" \
  -H "X-Client-Token: $TOKEN"
echo "   Track deleted"
echo

echo "=== Demo Complete ==="
echo
echo "Key Features Demonstrated:"
echo "  ✓ Client registration with token auth"
echo "  ✓ Track creation with base parameters"
echo "  ✓ Pattern creation with events"
echo "  ✓ Session state management"
echo "  ✓ Environment updates (BPM)"
echo "  ✓ Admin operations"
echo "  ✓ Resource cleanup"
