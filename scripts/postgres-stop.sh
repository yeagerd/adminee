#!/bin/bash
set -e

# Parse command line arguments
REMOVE_CONTAINER=false
REMOVE_VOLUME=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --remove)
            REMOVE_CONTAINER=true
            shift
            ;;
        --remove-volume)
            REMOVE_CONTAINER=true
            REMOVE_VOLUME=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --remove         Stop and remove the container (preserves volume data)"
            echo "  --remove-volume  Stop and remove the container AND volume (WILL DELETE DATA)"
            echo "  --force          Force stop without confirmation"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0               # Stop PostgreSQL container"
            echo "  $0 --remove      # Stop and remove container (keep data)"
            echo "  $0 --remove-volume # Stop and remove container and data"
            echo "  $0 --force       # Force stop without confirmation"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🛑 Stopping Briefly PostgreSQL instance..."

# Find running PostgreSQL containers
RUNNING_CONTAINERS=()
if docker ps | grep -q briefly-postgres; then
    RUNNING_CONTAINERS+=("briefly-postgres")
fi
if docker ps | grep -q briefly-db-1; then
    RUNNING_CONTAINERS+=("briefly-db-1")
fi

# Find stopped PostgreSQL containers
STOPPED_CONTAINERS=()
if docker ps -a | grep -q briefly-postgres; then
    if ! docker ps | grep -q briefly-postgres; then
        STOPPED_CONTAINERS+=("briefly-postgres")
    fi
fi
if docker ps -a | grep -q briefly-db-1; then
    if ! docker ps | grep -q briefly-db-1; then
        STOPPED_CONTAINERS+=("briefly-db-1")
    fi
fi

# Check if any containers exist
if [ ${#RUNNING_CONTAINERS[@]} -eq 0 ] && [ ${#STOPPED_CONTAINERS[@]} -eq 0 ]; then
    echo "📋 No PostgreSQL containers found"
    echo "   No containers named 'briefly-postgres' or 'briefly-db-1' exist"
    exit 0
fi

# Show what we found
if [ ${#RUNNING_CONTAINERS[@]} -gt 0 ]; then
    echo "📋 Found running container(s): ${RUNNING_CONTAINERS[*]}"
fi
if [ ${#STOPPED_CONTAINERS[@]} -gt 0 ]; then
    echo "📋 Found stopped container(s): ${STOPPED_CONTAINERS[*]}"
fi

# Handle removal options
if [ "$REMOVE_CONTAINER" = true ]; then
    if [ "$REMOVE_VOLUME" = true ]; then
        echo "⚠️  WARNING: This will remove the container AND all data!"
        if [ "$FORCE" = false ]; then
            echo ""
            read -p "Are you sure you want to delete all data? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "❌ Operation cancelled"
                exit 1
            fi
        fi

        # Stop and remove containers with volumes
        for container in "${RUNNING_CONTAINERS[@]}" "${STOPPED_CONTAINERS[@]}"; do
            echo "🧹 Removing container and data: $container"
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
        done

        # Remove volume
        echo "🗑️  Removing volume: briefly_postgres_data"
        docker volume rm briefly_postgres_data 2>/dev/null || true

        echo "✅ Container and data removed"

    else
        echo "📦 Removing containers (preserving data)..."
        for container in "${RUNNING_CONTAINERS[@]}" "${STOPPED_CONTAINERS[@]}"; do
            echo "🧹 Removing container: $container"
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
        done
        echo "✅ Containers removed (data preserved in volume)"
    fi

else
    # Just stop running containers
    if [ ${#RUNNING_CONTAINERS[@]} -gt 0 ]; then
        echo "🛑 Stopping running containers..."
        for container in "${RUNNING_CONTAINERS[@]}"; do
            echo "⏹️  Stopping: $container"
            docker stop "$container"
        done
        echo "✅ Containers stopped"
    else
        echo "📋 No running containers to stop"
    fi

    if [ ${#STOPPED_CONTAINERS[@]} -gt 0 ]; then
        echo "📋 Stopped containers remain: ${STOPPED_CONTAINERS[*]}"
        echo "   Use --remove to clean them up"
    fi
fi

echo ""
echo "📋 Summary:"
if [ "$REMOVE_CONTAINER" = true ]; then
    if [ "$REMOVE_VOLUME" = true ]; then
        echo "   ✅ Containers and data removed"
        echo "   🗑️  Volume 'briefly_postgres_data' removed"
    else
        echo "   ✅ Containers removed"
        echo "   💾 Data preserved in volume 'briefly_postgres_data'"
    fi
else
    echo "   ⏹️  Containers stopped"
    echo "   💾 Data preserved"
fi

echo ""
echo "💡 To start again:"
echo "   ./scripts/start-postgres.sh --restart"
echo "   ./scripts/start-postgres.sh --fresh-install"
