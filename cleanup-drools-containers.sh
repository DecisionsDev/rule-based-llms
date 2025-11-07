#!/bin/bash
# Cleanup script for orphaned Drools containers

echo "Cleaning up orphaned Drools containers..."

# Find and remove all containers starting with "drools-" except the main one
docker ps -a --filter "name=drools-" --format "{{.Names}}" | grep -v "^drools$" | while read container; do
    echo "Removing container: $container"
    docker rm -f "$container"
done

# Also remove associated volumes
docker volume ls --filter "name=drools-" --format "{{.Name}}" | grep -v "maven-repository" | while read volume; do
    echo "Removing volume: $volume"
    docker volume rm "$volume"
done

echo "Cleanup complete!"
echo ""
echo "Remaining containers:"
docker ps -a --filter "name=drools"
