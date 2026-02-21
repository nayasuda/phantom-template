#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")" || exit 1
git pull origin main --ff-only
echo ""
echo "Update complete!"
