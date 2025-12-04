#!/usr/bin/env python
"""
Script to embed a PNG image into an SVG file as a base64-encoded data URI.
This ensures the SVG is self-contained and doesn't require external image files.
"""

import sys
import os
import base64
from xml.etree import ElementTree as ET


def embed_png_in_svg(svg_path, png_path, output_path=None):
    """
    Embed a PNG image into an SVG file as a base64-encoded data URI.

    Args:
        svg_path: Path to the input SVG file
        png_path: Path to the PNG image to embed
        output_path: Optional path for output SVG (defaults to overwriting input)
    """
    if not os.path.exists(svg_path):
        print(f"Error: SVG file not found: {svg_path}")
        return False

    if not os.path.exists(png_path):
        print(f"Error: PNG file not found: {png_path}")
        return False

    # Read and encode the PNG
    print(f"Reading PNG file: {png_path}")

    # Get actual PNG dimensions using PIL
    from PIL import Image
    with Image.open(png_path) as img:
        img_width, img_height = img.size

    print(f"PNG dimensions: {img_width} x {img_height} pixels")

    with open(png_path, 'rb') as f:
        png_data = f.read()

    base64_data = base64.b64encode(png_data).decode('utf-8')
    data_uri = f"data:image/png;base64,{base64_data}"

    print(f"PNG encoded to base64 ({len(base64_data)} characters)")

    # Parse the SVG
    print(f"Reading SVG file: {svg_path}")
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Update SVG dimensions to match PNG (in pixels)
    root.set('width', str(img_width))
    root.set('height', str(img_height))
    root.set('viewBox', f'0 0 {img_width} {img_height}')

    print(f"Updated SVG dimensions to {img_width} x {img_height} pixels")

    # Find existing background layer or create new one
    ns = {'svg': 'http://www.w3.org/2000/svg', 'xlink': 'http://www.w3.org/1999/xlink'}
    background_group = root.find('.//svg:g[@id="background-layer"]', ns)

    if background_group is not None:
        # Update existing image
        print("Updating existing background layer...")
        image_elem = background_group.find('.//svg:image', ns)
        if image_elem is not None:
            image_elem.set('width', str(img_width))
            image_elem.set('height', str(img_height))
            image_elem.set('{http://www.w3.org/1999/xlink}href', data_uri)
            print("Updated existing image element with correct dimensions")
        else:
            # Create new image in existing group
            image_elem = ET.SubElement(background_group, 'image')
            image_elem.set('width', str(img_width))
            image_elem.set('height', str(img_height))
            image_elem.set('x', '0')
            image_elem.set('y', '0')
            image_elem.set('{http://www.w3.org/1999/xlink}href', data_uri)
            print("Created new image element in existing group")
    else:
        # Create new background layer at the beginning
        print("Creating new background layer...")
        background_group = ET.Element('g')
        background_group.set('id', 'background-layer')

        # Add comment
        comment = ET.Comment(' Template image with embedded PNG ')
        background_group.append(comment)

        # Create image element
        image_elem = ET.SubElement(background_group, 'image')
        image_elem.set('width', str(img_width))
        image_elem.set('height', str(img_height))
        image_elem.set('x', '0')
        image_elem.set('y', '0')
        image_elem.set('{http://www.w3.org/1999/xlink}href', data_uri)

        # Insert at the beginning
        root.insert(0, background_group)
        print("Created new background layer")

    # Write output
    if output_path is None:
        output_path = svg_path

    print(f"Writing SVG file: {output_path}")
    tree.write(output_path, encoding='utf-8', xml_declaration=True)

    print(f"Successfully embedded PNG into SVG!")
    print(f"Output file size: {os.path.getsize(output_path) / 1024:.1f} KB")

    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python embed_png_in_svg.py <svg_file> <png_file> [output_file]")
        print("\nExample:")
        print("  python embed_png_in_svg.py template.svg template.png")
        print("  python embed_png_in_svg.py template.svg template.png output.svg")
        sys.exit(1)

    svg_path = sys.argv[1]
    png_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    success = embed_png_in_svg(svg_path, png_path, output_path)

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
