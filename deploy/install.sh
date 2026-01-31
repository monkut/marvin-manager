#!/bin/bash
# Marvin Installation Script for Ubuntu/Debian
# Run as root: sudo bash install.sh

set -e

INSTALL_DIR="/opt/marvin"
MARVIN_USER="marvin"
LOG_DIR="/var/log/marvin"

echo "=== Marvin Installation Script ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run as root (sudo bash install.sh)"
    exit 1
fi

# Create marvin user if not exists
if ! id "$MARVIN_USER" &>/dev/null; then
    echo "Creating user: $MARVIN_USER"
    useradd --system --home-dir "$INSTALL_DIR" --shell /bin/bash "$MARVIN_USER"
fi

# Create directories
echo "Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"

# Set ownership
chown -R "$MARVIN_USER:$MARVIN_USER" "$INSTALL_DIR"
chown -R "$MARVIN_USER:$MARVIN_USER" "$LOG_DIR"

# Install uv if not present
if ! command -v uv &>/dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Clone or update repository
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    sudo -u "$MARVIN_USER" git pull
else
    echo "Cloning repository..."
    cd "$INSTALL_DIR"
    # If running from source directory, copy files
    if [ -f "$(dirname "$0")/../pyproject.toml" ]; then
        echo "Copying from source directory..."
        cp -r "$(dirname "$0")/.." "$INSTALL_DIR/"
        chown -R "$MARVIN_USER:$MARVIN_USER" "$INSTALL_DIR"
    else
        sudo -u "$MARVIN_USER" git clone https://github.com/kiconiaworks/marvin-manager.git .
    fi
fi

# Install Python dependencies
echo "Installing dependencies..."
cd "$INSTALL_DIR"
sudo -u "$MARVIN_USER" uv sync

# Create environment file if not exists
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "Creating environment file from template..."
    cp "$INSTALL_DIR/deploy/marvin.env.example" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
    chown "$MARVIN_USER:$MARVIN_USER" "$INSTALL_DIR/.env"
    echo ""
    echo "IMPORTANT: Edit $INSTALL_DIR/.env with your configuration!"
    echo ""
fi

# Install systemd services
echo "Installing systemd services..."
cp "$INSTALL_DIR/deploy/marvin-web.service" /etc/systemd/system/
cp "$INSTALL_DIR/deploy/marvin-telegram.service" /etc/systemd/system/
cp "$INSTALL_DIR/deploy/marvin-slack.service" /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit configuration: sudo nano $INSTALL_DIR/.env"
echo "  2. Run database setup: cd $INSTALL_DIR/mrvn && sudo -u $MARVIN_USER uv run python manage.py onboard --non-interactive"
echo "  3. Enable and start web service: sudo systemctl enable --now marvin-web"
echo "  4. (Optional) Enable Telegram: sudo systemctl enable --now marvin-telegram"
echo "  5. (Optional) Enable Slack: sudo systemctl enable --now marvin-slack"
echo ""
echo "View logs:"
echo "  sudo journalctl -u marvin-web -f"
echo "  sudo journalctl -u marvin-telegram -f"
echo "  sudo journalctl -u marvin-slack -f"
echo ""
