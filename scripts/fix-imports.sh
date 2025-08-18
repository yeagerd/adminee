#!/bin/bash

# Fix import statements that have extra quotes from sed replacement
# This script fixes the remaining import issues in the frontend

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Function to print colored output
print_status() {
    local level=$1
    local message=$2
    
    case $level in
        "info")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
        "success")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "error")
            echo -e "${RED}❌ $message${NC}"
            ;;
    esac
}

print_status "info" "Fixing import statements in frontend files..."

# Fix the extra quote issues
cd "$PROJECT_ROOT/frontend"

# Fix imports with extra quotes using a simpler approach
print_status "info" "Fixing imports with extra quotes..."

# Create a temporary script to handle the replacement
cat > fix_imports_temp.sh << 'EOF'
#!/bin/bash
# Fix the specific pattern we're seeing
find . -name "*.ts" -o -name "*.tsx" | xargs sed -i '' 's|from "@/types/api/office"'"'"';|from "@/types/api/office";|g'
find . -name "*.ts" -o -name "*.tsx" | xargs sed -i '' 's|from "@/types/api/user"'"'"';|from "@/types/api/user";|g'
EOF

chmod +x fix_imports_temp.sh
./fix_imports_temp.sh
rm fix_imports_temp.sh

print_status "success" "Import statements fixed"

# Check if there are any remaining issues
print_status "info" "Checking for remaining import issues..."

remaining_issues=$(find . -name "*.ts" -o -name "*.tsx" | xargs grep -l 'from.*"'"'"';' 2>/dev/null || true)

if [[ -n "$remaining_issues" ]]; then
    print_status "warning" "Found remaining import issues in:"
    echo "$remaining_issues"
else
    print_status "success" "No remaining import issues found"
fi

print_status "success" "Import fix script completed"
