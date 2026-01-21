#!/bin/bash
# Quick fix script for line ending issues on Windows
# Run this if you get "exec /code/serverStart.sh: no such file or directory" error

echo "=========================================="
echo "Fixing Line Endings for Docker Build"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    echo "Please run this script from the repository root directory"
    exit 1
fi

echo "✓ Found docker-compose.yml - in correct directory"
echo ""

# Check if dos2unix is available
if command -v dos2unix &> /dev/null; then
    echo "✓ Using dos2unix to fix line endings..."
    dos2unix rule-agent/serverStart.sh
    dos2unix rule-agent/deploy_ruleapp_to_odm.sh
else
    echo "ℹ dos2unix not found, using sed instead..."
    sed -i 's/\r$//' rule-agent/serverStart.sh
    sed -i 's/\r$//' rule-agent/deploy_ruleapp_to_odm.sh
fi

echo "✓ Fixed line endings in shell scripts"
echo ""

# Make scripts executable
chmod +x rule-agent/serverStart.sh
chmod +x rule-agent/deploy_ruleapp_to_odm.sh
echo "✓ Made scripts executable"
echo ""

# Verify
echo "Verifying line endings..."
if file rule-agent/serverStart.sh | grep -q "CRLF"; then
    echo "⚠ Warning: serverStart.sh still has CRLF line endings"
    echo "Try running: sed -i 's/\r$//' rule-agent/serverStart.sh"
else
    echo "✓ serverStart.sh has correct line endings (LF)"
fi

if file rule-agent/deploy_ruleapp_to_odm.sh | grep -q "CRLF"; then
    echo "⚠ Warning: deploy_ruleapp_to_odm.sh still has CRLF line endings"
    echo "Try running: sed -i 's/\r$//' rule-agent/deploy_ruleapp_to_odm.sh"
else
    echo "✓ deploy_ruleapp_to_odm.sh has correct line endings (LF)"
fi

echo ""
echo "=========================================="
echo "Fix Complete!"
echo "=========================================="
echo ""
echo "Now rebuild the Docker container:"
echo "  docker-compose down"
echo "  docker rmi backend"
echo "  docker-compose build backend"
echo "  docker-compose up -d"
echo ""
