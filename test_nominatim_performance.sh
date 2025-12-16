#!/bin/bash
# Performance test script for self-hosted Nominatim

echo "=========================================="
echo "Nominatim Performance Test"
echo "=========================================="
echo ""

NOMINATIM_URL="${NOMINATIM_URL:-http://localhost:8080}"
TEST_COUNT=10

echo "Testing Nominatim at: $NOMINATIM_URL"
echo "Number of tests per query: $TEST_COUNT"
echo ""

# Test 1: Search queries
echo "=== Test 1: Search Queries ==="
echo "Query: 'Kuala Lumpur'"
total_time=0
for i in $(seq 1 $TEST_COUNT); do
    start=$(date +%s.%N)
    curl -s "${NOMINATIM_URL}/search?q=Kuala+Lumpur&format=json" > /dev/null 2>&1
    end=$(date +%s.%N)
    elapsed=$(echo "$end - $start" | bc)
    elapsed_ms=$(echo "$elapsed * 1000" | bc | cut -d. -f1)
    total_time=$(echo "$total_time + $elapsed" | bc)
    if [ $i -eq 1 ]; then
        echo "  First query (cold cache): ${elapsed_ms}ms"
    fi
done
avg_time=$(echo "scale=2; ($total_time / $TEST_COUNT) * 1000" | bc)
echo "  Average (after warmup): ${avg_time}ms"
echo ""

# Test 2: Reverse geocoding
echo "=== Test 2: Reverse Geocoding ==="
echo "Coordinates: 3.1390, 101.6869 (Kuala Lumpur)"
total_time=0
for i in $(seq 1 $TEST_COUNT); do
    start=$(date +%s.%N)
    curl -s "${NOMINATIM_URL}/reverse?lat=3.1390&lon=101.6869&format=json" > /dev/null 2>&1
    end=$(date +%s.%N)
    elapsed=$(echo "$end - $start" | bc)
    elapsed_ms=$(echo "$elapsed * 1000" | bc | cut -d. -f1)
    total_time=$(echo "$total_time + $elapsed" | bc)
    if [ $i -eq 1 ]; then
        echo "  First query (cold cache): ${elapsed_ms}ms"
    fi
done
avg_time=$(echo "scale=2; ($total_time / $TEST_COUNT) * 1000" | bc)
echo "  Average (after warmup): ${avg_time}ms"
echo ""

# Test 3: Concurrent requests
echo "=== Test 3: Concurrent Requests (5 simultaneous) ==="
start=$(date +%s.%N)
for i in {1..5}; do
    curl -s "${NOMINATIM_URL}/search?q=Penang&format=json" > /dev/null 2>&1 &
done
wait
end=$(date +%s.%N)
elapsed=$(echo "$end - $start" | bc)
elapsed_ms=$(echo "$elapsed * 1000" | bc | cut -d. -f1)
echo "  Time for 5 concurrent requests: ${elapsed_ms}ms"
echo ""

# Test 4: Different locations
echo "=== Test 4: Multiple Locations ==="
locations=("Ipoh" "Malacca" "Johor Bahru" "Kota Kinabalu")
for location in "${locations[@]}"; do
    start=$(date +%s.%N)
    curl -s "${NOMINATIM_URL}/search?q=${location}&format=json" > /dev/null 2>&1
    end=$(date +%s.%N)
    elapsed=$(echo "$end - $start" | bc)
    elapsed_ms=$(echo "$elapsed * 1000" | bc | cut -d. -f1)
    echo "  ${location}: ${elapsed_ms}ms"
done
echo ""

# Check container stats
echo "=== Container Resource Usage ==="
docker stats nominatim --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "  (Nominatim container not running or not named 'nominatim')"
echo ""

echo "=========================================="
echo "Performance Test Complete"
echo "=========================================="
echo ""
echo "Expected performance for self-hosted Nominatim:"
echo "  - Search queries: 10-50ms (after cache warmup)"
echo "  - Reverse geocoding: 5-20ms (after cache warmup)"
echo "  - Concurrent requests: Should handle multiple requests efficiently"
echo ""

