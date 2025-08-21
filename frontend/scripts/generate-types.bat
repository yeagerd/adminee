@echo off
REM Type generation script for Windows systems
REM Generates TypeScript types from OpenAPI schemas

echo 🚀 Generating TypeScript types from OpenAPI schemas...

REM Change to frontend directory
cd /d "%~dp0\.."

REM Create types directory structure
if not exist "types\api\chat" mkdir "types\api\chat"
if not exist "types\api\meetings" mkdir "types\api\meetings"
if not exist "types\api\office" mkdir "types\api\office"
if not exist "types\api\user" mkdir "types\api\user"
if not exist "types\api\shipments" mkdir "types\api\shipments"
if not exist "types\api\email-sync" mkdir "types\api\email-sync"
if not exist "types\api\vector-db" mkdir "types\api\vector-db"

REM Install dependencies if not already installed
npm list openapi-typescript-codegen >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing openapi-typescript-codegen...
    npm install
)

REM Generate types for each service
echo 📝 Generating types for Chat service...
npx openapi --input ../openapi-schemas/chat-openapi.json --output ./types/api/chat

echo 📝 Generating types for Meetings service...
npx openapi --input ../openapi-schemas/meetings-openapi.json --output ./types/api/meetings

echo 📝 Generating types for Office service...
npx openapi --input ../openapi-schemas/office-openapi.json --output ./types/api/office

echo 📝 Generating types for User service...
npx openapi --input ../openapi-schemas/user-openapi.json --output ./types/api/user

echo 📝 Generating types for Shipments service...
npx openapi --input ../openapi-schemas/shipments-openapi.json --output ./types/api/shipments

echo 📝 Generating types for Email Sync service...
npx openapi --input ../openapi-schemas/email_sync-openapi.json --output ./types/api/email-sync

echo 📝 Generating types for Vector DB service...


REM Create index file
echo 📄 Creating index file...
(
echo // Auto-generated TypeScript types from OpenAPI schemas
echo // Generated on: %date% %time%
echo.
echo export * from './chat';
echo export * from './meetings';
echo export * from './office';
echo export * from './user';
echo export * from './shipments';
echo export * from './email-sync';
echo export * from './vector-db';
) > types\api\index.ts

echo ✅ Type generation completed successfully!
echo 📁 Types saved to: types\api\
echo 🔍 Run 'npm run typecheck' to verify types are valid

pause
