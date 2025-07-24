#!/bin/bash
set -e

# Lint
npm run lint

# Type check
npx tsc --noEmit

# Jest tests
npx jest --ci

# Build
npm run build

echo "\nAll frontend checks passed!" 