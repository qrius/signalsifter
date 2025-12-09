#!/bin/bash
"""
Discord Setup Script for SignalSifter
Helps set up the Discord module and verify configuration.

Usage:
  ./discord_setup.sh
  ./discord_setup.sh --check-only
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in check-only mode
CHECK_ONLY=false
if [[ "$1" == "--check-only" ]]; then
    CHECK_ONLY=true
fi

echo "🤖 SignalSifter Discord Module Setup"
echo "====================================="

# Check Python version
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
if [[ $(python3 -c "import sys; print(sys.version_info >= (3, 8))") == "True" ]]; then
    print_success "Python version: $python_version ✓"
else
    print_error "Python 3.8+ required, found: $python_version"
    exit 1
fi

# Check if .env file exists
print_status "Checking environment configuration..."
if [[ ! -f ".env" ]]; then
    print_error ".env file not found!"
    echo "Please create a .env file with the following variables:"
    echo "DISCORD_BOT_TOKEN=your_discord_bot_token_here"
    echo "GEMINI_API_KEY=your_gemini_api_key_here"
    exit 1
else
    print_success ".env file exists ✓"
fi

# Check environment variables
check_env_var() {
    local var_name="$1"
    local var_value=$(grep "^$var_name=" .env 2>/dev/null | cut -d'=' -f2)
    
    if [[ -z "$var_value" || "$var_value" == "your_${var_name,,}_here" ]]; then
        print_warning "$var_name is not configured in .env"
        return 1
    else
        print_success "$var_name is configured ✓"
        return 0
    fi
}

env_configured=true
if ! check_env_var "DISCORD_BOT_TOKEN"; then
    env_configured=false
fi

if ! check_env_var "GEMINI_API_KEY"; then
    print_warning "GEMINI_API_KEY not configured (AI analysis will be skipped)"
fi

# Install dependencies if not in check-only mode
if [[ "$CHECK_ONLY" == "false" ]]; then
    print_status "Installing Python dependencies..."
    
    # Check if virtual environment should be used
    if [[ -d "venv" ]] || [[ -d ".venv" ]]; then
        print_status "Virtual environment detected, make sure it's activated"
    fi
    
    if pip install -r requirements.txt; then
        print_success "Dependencies installed successfully ✓"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
fi

# Check if discord.py is installed
print_status "Checking discord.py installation..."
if python3 -c "import discord; print(f'discord.py version: {discord.__version__}')" 2>/dev/null; then
    print_success "discord.py is installed ✓"
else
    print_error "discord.py is not installed"
    if [[ "$CHECK_ONLY" == "false" ]]; then
        print_status "Installing discord.py..."
        pip install discord.py==2.3.2
    else
        exit 1
    fi
fi

# Create necessary directories
if [[ "$CHECK_ONLY" == "false" ]]; then
    print_status "Creating data directories..."
    mkdir -p data/{raw,media,discord_analysis,ocr}
    print_success "Data directories created ✓"
fi

# Test database schema
print_status "Testing database schema..."
if python3 -c "
import sqlite3
import os
from discord_extractor import ensure_discord_schema

try:
    ensure_discord_schema()
    print('Database schema initialized successfully')
except Exception as e:
    print(f'Database schema error: {e}')
    exit(1)
"; then
    print_success "Database schema is ready ✓"
else
    print_error "Database schema initialization failed"
    exit 1
fi

# Test Discord bot token if configured
if [[ "$env_configured" == "true" ]]; then
    print_status "Testing Discord bot connection..."
    
    # Create a simple test script
    cat > /tmp/discord_test.py << 'EOF'
import asyncio
import discord
import os
from dotenv import load_dotenv

load_dotenv()

async def test_bot():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("DISCORD_BOT_TOKEN not found")
        return False
    
    intents = discord.Intents.default()
    intents.message_content = True
    
    try:
        client = discord.Client(intents=intents)
        
        @client.event
        async def on_ready():
            print(f"Bot connected as: {client.user}")
            await client.close()
        
        await client.login(token)
        await client.connect()
        return True
        
    except discord.LoginFailure:
        print("Invalid Discord bot token")
        return False
    except discord.PrivilegedIntentsRequired:
        print("Message Content Intent not enabled")
        return False
    except Exception as e:
        print(f"Connection error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_bot())
    exit(0 if result else 1)
EOF

    if python3 /tmp/discord_test.py; then
        print_success "Discord bot connection successful ✓"
    else
        print_error "Discord bot connection failed"
        echo ""
        echo "Common issues:"
        echo "1. Invalid bot token"
        echo "2. Message Content Intent not enabled in Discord Developer Portal"
        echo "3. Bot not invited to any servers"
        echo ""
        echo "Please check your Discord bot configuration:"
        echo "https://discord.com/developers/applications"
    fi
    
    rm -f /tmp/discord_test.py
fi

echo ""
echo "🎉 Setup Complete!"
echo ""

if [[ "$env_configured" == "true" ]]; then
    echo "✅ Ready to extract Discord messages!"
    echo ""
    echo "Next steps:"
    echo "1. Invite your bot to a Discord server"
    echo "2. Get a Discord channel URL like: https://discord.com/channels/123456/789012"
    echo "3. Run: python run_discord_pipeline.py --url \"your_discord_url\""
else
    echo "⚠️  Configuration needed:"
    echo "1. Add your Discord bot token to .env file"
    echo "2. Optionally add Gemini API key for AI analysis"
    echo "3. Run this setup script again to verify"
fi

echo ""
echo "📚 For detailed instructions, see README_DISCORD.md"