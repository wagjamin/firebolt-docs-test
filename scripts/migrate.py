#!/usr/bin/env python3

"""
This script helps migrate Jekyll markdown files to Mintlify MDX format.
It includes utilities for:
- Converting frontmatter 
- Moving files to correct output directories
- Updating image and link references
- Converting Jekyll-specific syntax
- Renaming .md files to .mdx_mintlify_ignore
"""

import os
import re
import shutil
from pathlib import Path
import yaml

def convert_frontmatter(content):
    """Convert Jekyll frontmatter to Mintlify frontmatter"""
    # Extract Jekyll frontmatter between --- markers
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not frontmatter_match:
        return content
        
    # Parse Jekyll frontmatter
    jekyll_frontmatter = yaml.safe_load(frontmatter_match.group(1))
    
    # Create Mintlify frontmatter
    mintlify_frontmatter = {
        "title": jekyll_frontmatter.get("title", ""),
        "sidebarTitle": jekyll_frontmatter.get("title", ""),
    }
    
    # Convert to YAML string
    new_frontmatter = yaml.dump(mintlify_frontmatter, default_flow_style=False)
    
    # Replace old frontmatter with new
    new_content = f"---\n{new_frontmatter}---\n\n"
    new_content += content[frontmatter_match.end():]
    
    return new_content

def convert_links(content):
    """Convert Jekyll-style links to Mintlify format"""
    # Convert {% link foo/bar.md %} to /foo/bar
    content = re.sub(r'{%\s*link\s+([^%}]+)\s*%}', r'/\1', content)
    
    # Remove .md and .html extensions from links
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\.(?:md|html)\)', r'[\1](\2)', content)
    
    return content

def convert_images(content):
    """Convert image paths and formatting to use Mintlify conventions"""
    # First convert basic image paths from ../assets to /assets
    content = re.sub(r'!\[(.*?)\]\((\.\.)?/assets/', r'![/1](/assets/', content)
    
    # Convert HTML img tags with relative paths
    content = re.sub(
        r'<img\s+src="(?:\.\.\/)*assets\/([^"]+)"([^>]*)(?<!/)>',
        r'<img src="/assets/\1"\2 />',
        content
    )
    
    # Convert Jekyll-style image attributes to Mintlify HTML format
    content = re.sub(
        r'!\[(.*?)\]\((.*?)\)(?:\s*{:\s*(?:width="(\d+)")?\s*(?:\.centered)?\s*(?:style="([^}]*)")?\s*})?(?:\s*<br\s*/>)?\s*(?:\*\*(.*?)\*\*)?(?:\s*{:\s*style="([^}]*)"}\s*)?',
        lambda m: format_image_html(m),
        content,
        flags=re.DOTALL
    )
    
    return content

def format_image_html(match):
    """Helper function to format image HTML based on attributes"""
    alt_text = match.group(1)
    src = match.group(2)
    width = match.group(3)
    style1 = match.group(4)
    caption = match.group(5)
    style2 = match.group(6)
    
    # Start building the image tag
    img_attrs = []
    
    if width:
        img_attrs.append(f'width="{width}"')
    
    # Center the image if .centered was specified
    if '.centered' in match.group(0):
        img_attrs.append('className="mx-auto"')
    
    # Combine all attributes - note the self-closing />
    img_html = f'<img src="{src}" alt="{alt_text}" {" ".join(img_attrs)} />'
    
    # Add caption if present
    if caption:
        return f'<div className="text-center">\n  {img_html}\n  <p className="text-sm text-gray-500 mt-2">{caption}</p>\n</div>'
    
    return img_html

def convert_content(content):
    """Convert Jekyll-specific syntax to Mintlify format"""
    # Remove top-level title that matches the frontmatter title
    content = re.sub(
        r'^(---\n.*?\n---\n\n*)(?:[^\n#]*\n)*?#\s+[^\n]+\n+',
        r'\1',
        content,
        flags=re.DOTALL
    )
    
    # Replace standalone <br> tags with newlines
    content = re.sub(r'\s*<br\s*/?\>\s*', '\n\n', content)
    
    # Remove {: .no_toc} markers
    content = re.sub(r'{:\s*\.no_toc\s*}', '', content)
    # Remove "* Topic Toc" line and {: toc} markers
    content = re.sub(r'{:\s*\.?toc\s*}', '', content)
    content = re.sub(r'\*\s*Topic Toc\s*', '', content)

    # Convert {: .note} blocks to <Note> components
    # Look for {: .note} followed by the next paragraph
    content = re.sub(
        r'{:\s*\.?note\s*}\s*\n+(.*?)(?=\n\n|\Z)', 
        r'<Note>\1</Note>',
        content,
        flags=re.DOTALL
    )
    
    # Clean up any newlines before closing Note tags. Mintlify doesn't like newlines in Note tags.
    content = re.sub(r'\n\s*</Note>', r'</Note>', content)

    # Convert {: .warning} blocks to <Warning> components
    # Look for {: .warning} followed by the next paragraph
    content = re.sub(
        r'{:\s*\.?warning\s*}\s*\n+(.*?)(?=\n\n|\Z)', 
        r'<Warning>\1</Warning>',
        content,
        flags=re.DOTALL
    )
    
    # Clean up any newlines before closing Note tags. Mintlify doesn't like newlines in Note tags.
    content = re.sub(r'\n\s*</Warning>', r'</Warning>', content)
    
    return content

def migrate_file(src_path, dest_path):
    """Migrate a single file from Jekyll to Mintlify format"""
    print(f"Migrating {src_path} to {dest_path}")
    
    # Read source file
    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if file is marked as unpublished
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if frontmatter_match:
        frontmatter = yaml.safe_load(frontmatter_match.group(1))
        if frontmatter.get('published') is False:
            print(f"Skipping unpublished file: {src_path}")
            return
    
    # Convert content
    content = convert_frontmatter(content)
    content = convert_links(content)
    content = convert_images(content)
    content = convert_content(content)
    
    # Create destination directory if needed
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    # Write converted file
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(content)

def migrate_directory(src_dir, dest_dir):
    """Recursively migrate all markdown files in a directory"""
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)
    
    # Create destination directory
    os.makedirs(dest_path, exist_ok=True)
    
    for src_file in src_path.rglob('*.md_mintlify_ignore'):
        # Get relative path to maintain directory structure
        rel_path = src_file.relative_to(src_path)
        
        # Handle index files specially
        if src_file.name == 'index.md_mintlify_ignore':
            # Convert index.md to overview.mdx in the same directory
            dest_file = dest_path / rel_path.parent / 'overview.mdx'
            
            # Create parent directory if needed
            os.makedirs(dest_file.parent, exist_ok=True)
            
            # Read the source file
            with open(src_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace or add frontmatter with Overview title
            content = re.sub(
                r'^---\n.*?\n---\n',
                '---\ntitle: Overview\nsidebarTitle: Overview\n---\n',
                content,
                flags=re.DOTALL
            )
            
            # Migrate the content
            content = convert_links(content)
            content = convert_images(content)
            content = convert_content(content)
            
            # Write the overview file
            with open(dest_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"Migrated index to overview: {dest_file}")
            continue
            
        # Handle all other files normally
        dest_file = dest_path / rel_path.with_suffix('.mdx')
        migrate_file(src_file, dest_file)

def rename_md_files(directory):
    """Rename all .md files in directory to .md_mintlify_ignore"""
    path = Path(directory)
    
    # Find all .md files recursively
    for md_file in path.rglob('*.md'):
        # Construct new filename with .mdx_mintlify_ignore extension
        new_name = md_file.with_suffix('.md_mintlify_ignore')
        
        # Rename the file
        md_file.rename(new_name)
        print(f"Renamed {md_file} to {new_name}")

def main():
    # Rename all .md files in old_docs. Otherwise `mintlify dev` will not work.
    rename_md_files("old_docs")
    
    # Migrate the "Overview" directory
    migrate_directory("old_docs/Overview", "overview")
    
    print("Migration complete!")

if __name__ == "__main__":
    main()
