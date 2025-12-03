#!/usr/bin/env python
"""
Script to format an SVG file for better readability.
"""

import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom


def format_svg(input_path, output_path=None):
    """
    Format an SVG file with proper indentation and line breaks.

    Args:
        input_path: Path to the input SVG file
        output_path: Optional path for output SVG (defaults to overwriting input)
    """
    if output_path is None:
        output_path = input_path

    print(f"Reading SVG file: {input_path}")

    # Register namespaces
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

    # Parse the SVG
    tree = ET.parse(input_path)
    root = tree.getroot()

    # Convert to string with minidom for pretty printing
    xml_string = ET.tostring(root, encoding='utf-8')
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8')

    # Remove extra blank lines and fix formatting
    lines = pretty_xml.decode('utf-8').split('\n')
    formatted_lines = []
    prev_blank = False

    for line in lines:
        # Skip the minidom XML declaration since we'll add our own
        if line.startswith('<?xml'):
            continue
        # Remove multiple consecutive blank lines
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        formatted_lines.append(line)
        prev_blank = is_blank

    # Add proper XML declaration
    final_content = "<?xml version='1.0' encoding='utf-8'?>\n" + '\n'.join(formatted_lines)

    # Write output
    print(f"Writing formatted SVG file: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"Successfully formatted SVG file!")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python format_svg.py <svg_file> [output_file]")
        print("\nExample:")
        print("  python format_svg.py template.svg")
        print("  python format_svg.py template.svg formatted.svg")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    success = format_svg(input_path, output_path)

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
