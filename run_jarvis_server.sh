#!/bin/bash

# Navigate to the directory where the script is located
cd "$(dirname "$0")"

# Força o encerramento de qualquer processo na porta 5001 para evitar conflitos
echo "Garantindo que a porta 5001 está livre..."
fuser -k 5001/tcp 2>/dev/null
sleep 1 # Adiciona uma pequena pausa para garantir que a porta seja liberada

echo "========================================="
echo "  Starting JARVIS V12 Server (app.py)"
echo "========================================="

# Run the Python Flask SocketIO server
# The app.py script will print the Cloudflare tunnel URL if successful.
python3 app.py &

# Give app.py a moment to start and possibly generate the Cloudflare URL
sleep 5

echo "------------------------------------------------"
echo "To connect your Android app, use ONE of the following options:"
echo "------------------------------------------------"

echo "1. Cloudflare Tunnel (for remote access, see output above):"
echo "   Look for 'ACESSO REMOTO LIBERADO: <URL>' in the output above."
echo "   Example: https://your-cloudflare-tunnel.trycloudflare.com"

echo ""
echo "2. Local IP Address (if Android and PC are on the same network):"
echo "   Find your PC's local IP address (e.g., 192.168.1.100) and use port 5001."
echo "   Possible Local IPs: $(hostname -I | awk '{print $1}')"
echo "   Example: http://$(hostname -I | awk '{print $1}'):5001"
echo "   If multiple IPs are listed, try each one until you find the correct one."

echo "------------------------------------------------"
echo "Server is running in the background. Press Ctrl+C to stop this script and the server."
echo "========================================="
wait
