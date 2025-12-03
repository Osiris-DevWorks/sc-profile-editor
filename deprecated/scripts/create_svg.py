#!/usr/bin/env python
"""
Script to create an SVG overlay with accurately positioned button labels
for the VKB Gunfighter MCGU joystick template.
"""

import xml.etree.ElementTree as ET
from PIL import Image

# Get image dimensions
img = Image.open('visual-templates/vkb_gunfighter_mcgu/vkb_gunfighter_mcgu.png')
img_width, img_height = img.size

print(f"Image dimensions: {img_width} x {img_height}")

# Define button positions based on visual analysis of the image
# Each entry: (button_number, x_position, y_position, max_width, max_height)
# Sorted in numerical ascending order
button_positions = [
    # Main Trigger section (left side)
    (1, 130, 400, 320, 30),
    (2, 130, 430, 320, 30),

    # Flip Trigger section (left side)
    (3, 130, 505, 320, 30),    # Click

    # AP OFF section (top left)
    (4, 130, 155, 320, 30),

    # LVLNG section (top right)
    (5, 1030, 172, 320, 30),

    # GUN section (right side)
    (6, 1030, 232, 320, 30),

    # Ring Finger Button section (bottom left)
    (7, 130, 895, 320, 30),

    # MASTER MODE section (top center)
    (8, 500, 170, 320, 30),    # Circle symbol

    # RESET section (bottom left)
    (9, 130, 795, 320, 30),    # Circle symbol
    (10, 130, 825, 320, 30),   # Up arrow
    (11, 130, 885, 320, 30),   # Left arrow
    (12, 130, 855, 320, 30),   # Down arrow
    (13, 130, 915, 320, 30),   # Right arrow

    # MANVR section (right side)
    (14, 1030, 535, 320, 30),  # Up arrow
    (15, 1030, 625, 320, 30),  # Right arrow
    (16, 1030, 565, 320, 30),  # Down arrow
    (17, 1030, 595, 320, 30),  # Left arrow
    (18, 1030, 505, 320, 30),  # Circle symbol

    # DC section (right side)
    (19, 1030, 345, 320, 30),  # Up arrow
    (20, 1030, 435, 320, 30),  # Right arrow
    (21, 1030, 375, 320, 30),  # Down arrow
    (22, 1030, 405, 320, 30),  # Left arrow
    (23, 1030, 315, 320, 30),  # Circle symbol

    # GATE CONT section (left side) - buttons with modifier symbols
    (24, 130, 225, 320, 30),   # Up arrow
    (25, 100, 315, 320, 30),   # Right arrow
    (26, 130, 255, 320, 30),   # Down arrow
    (27, 130, 285, 320, 30),   # Left arrow

    # MASTER MODE section (top center) continued
    (28, 500, 200, 320, 30),   # Up arrow
    (29, 500, 290, 320, 30),   # Right arrow
    (30, 500, 230, 320, 30),   # Down arrow
    (31, 500, 260, 320, 30),   # Left arrow

    # GATE CONT section (left side)
    (33, 130, 195, 320, 30),   # Circle symbol

    # Flip Trigger section (left side)
    (35, 100, 535, 320, 30),   # Stage 1
]

# Create SVG structure
svg_ns = "http://www.w3.org/2000/svg"
xlink_ns = "http://www.w3.org/1999/xlink"

ET.register_namespace('', svg_ns)
ET.register_namespace('xlink', xlink_ns)

root = ET.Element('svg', {
    'xmlns': svg_ns,
    'xmlns:xlink': xlink_ns,
    'width': str(img_width),
    'height': str(img_height),
    'viewBox': f'0 0 {img_width} {img_height}',
    'version': '1.1'
})

# Add comment
root.append(ET.Comment(' This will be populated by embed_png_in_svg.py '))

# Create overlay layer group
overlay_group = ET.SubElement(root, 'g', {'id': 'overlay-layer'})

# Add text elements for each button
for button_num, x, y, max_width, max_height in button_positions:
    text_elem = ET.SubElement(overlay_group, 'text', {
        'id': f'button{button_num}',
        'x': str(x),
        'y': str(y),
        'font-family': 'Arial, sans-serif',
        'font-size': '14',
        'fill': 'black',
        'text-anchor': 'left',
        'data-button': str(button_num),
        'data-max-width': str(max_width),
        'data-max-height': str(max_height)
    })
    text_elem.text = f'{{{{ Button {button_num} }}}}'

# Write SVG file
tree = ET.ElementTree(root)
output_path = 'visual-templates/vkb_gunfighter_mcgu/vkb_gunfighter_mcgu_overlay.svg'
tree.write(output_path, encoding='utf-8', xml_declaration=True)

print(f"SVG file created: {output_path}")
print(f"Total buttons: {len(button_positions)}")
