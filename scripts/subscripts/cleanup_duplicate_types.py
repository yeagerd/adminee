#!/usr/bin/env python3
"""
Script to clean up duplicate TypeScript type definitions.
This script removes duplicate type/interface declarations while preserving the first occurrence.
"""

import re
import sys
from pathlib import Path


def cleanup_duplicate_types(file_path):
    """Clean up duplicate types in a single TypeScript file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Handle empty files
        if not content.strip():
            return True
        
        # Split content into lines for processing
        lines = content.split('\n')
        result_lines = []
        seen_types = set()
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check if this line starts a type/interface declaration
            type_match = re.match(r'^(export\s+)?(type|interface)\s+([A-Za-z_][A-Za-z0-9_]*)', line)
            
            if type_match:
                type_name = type_match.group(3)
                
                if type_name in seen_types:
                    # This is a duplicate - skip until we find the end
                    print(f'Found duplicate type: {type_name} in {file_path}', file=sys.stderr)
                    
                    # Count braces starting from the current line
                    brace_count = 0
                    if '{' in line:
                        brace_count += line.count('{')
                    
                    # If no opening brace on this line, check the next line
                    if brace_count == 0:
                        i += 1
                        if i < len(lines):
                            next_line = lines[i]
                            if '{' in next_line:
                                brace_count += next_line.count('{')
                    
                    # Skip lines until we find the end of this type definition
                    # Handle both multi-line and single-line type definitions
                    start_i = i  # Track where we started to prevent infinite loops
                    while i < len(lines) and brace_count > 0:
                        current_line = lines[i]
                        # Count braces in the current line
                        opening_braces = current_line.count('{')
                        closing_braces = current_line.count('}')
                        brace_count += opening_braces - closing_braces
                        i += 1
                        
                        # Safety check to prevent infinite loops
                        if i - start_i > 1000:  # Arbitrary limit to prevent infinite loops
                            print(f'Warning: Possible infinite loop detected for type {type_name} in {file_path}', file=sys.stderr)
                            break
                    
                    # If we still have unclosed braces, we've reached the end of the file
                    # This indicates a malformed type definition
                    if brace_count > 0:
                        print(f'Warning: Unclosed braces in type definition for {type_name} in {file_path}', file=sys.stderr)
                        # Ensure we don't go beyond the file bounds
                        if i >= len(lines):
                            break
                    
                    # Check if we ended with a semicolon (single-line types)
                    if i < len(lines) and ';' in lines[i-1]:
                        continue
                    
                    # If we didn't find a semicolon, we might have reached the end of the file
                    # or encountered a malformed type definition. Skip to the next line.
                    if i >= len(lines):
                        break
                    
                    continue
                else:
                    # First occurrence - keep it
                    seen_types.add(type_name)
            
            # Only add the line if we haven't already processed it as part of a duplicate
            # and if we're not currently in the middle of processing a duplicate
            if i < len(lines):
                result_lines.append(line)
            i += 1
        
        # Clean up empty lines and write the cleaned content back
        cleaned_lines = [line for line in result_lines if line.strip() or line == '']
        
        # Ensure we don't write empty files
        if not cleaned_lines:
            print(f'Warning: File {file_path} would be empty after cleanup, skipping', file=sys.stderr)
            return True
        
        # Validate that the cleaned content is not significantly shorter than expected
        if len(cleaned_lines) < len(lines) * 0.5:  # If we removed more than 50% of lines, something might be wrong
            print(f'Warning: File {file_path} had significant content removed ({len(cleaned_lines)}/{len(lines)} lines), reviewing...', file=sys.stderr)
            # Revert to original content if too much was removed
            with open(file_path, 'w') as f:
                f.write(content)
            return False
        
        with open(file_path, 'w') as f:
            f.write('\n'.join(cleaned_lines))
            
    except Exception as e:
        print(f'Error processing {file_path}: {e}', file=sys.stderr)
        return False
    
    return True


def cleanup_service_directory(service_dir):
    """Clean up duplicate types in all TypeScript files in a service directory."""
    service_path = Path(service_dir)
    if not service_path.is_dir():
        print(f'Service directory not found: {service_dir}', file=sys.stderr)
        return False
    
    # Find all TypeScript files in the service directory
    ts_files = list(service_path.rglob('*.ts'))
    
    if not ts_files:
        print(f'No TypeScript files found in {service_dir}')
        return True
    
    print(f'Processing {len(ts_files)} TypeScript files in {service_dir}')
    
    success = True
    processed_count = 0
    for ts_file in ts_files:
        if cleanup_duplicate_types(str(ts_file)):
            processed_count += 1
        else:
            success = False
    
    print(f'Successfully processed {processed_count}/{len(ts_files)} files')
    return success


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print('Usage: python3 cleanup_duplicate_types.py <types_directory>', file=sys.stderr)
        sys.exit(1)
    
    types_dir = sys.argv[1]
    
    # Process the service directory
    if cleanup_service_directory(types_dir):
        print('✅ Duplicate type cleanup completed successfully')
        sys.exit(0)
    else:
        print('❌ Duplicate type cleanup failed', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
