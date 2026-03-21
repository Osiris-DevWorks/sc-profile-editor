"""
PDF-based device template manager for loading, rendering, and populating PDFs

This module handles PDF templates with interactive form fields for device visualization.
"""

import json
import logging
import os
from typing import List, Optional, Dict
from dataclasses import dataclass
import fitz  # PyMuPDF
from PyQt6.QtGui import QPixmap, QImage

logger = logging.getLogger(__name__)


@dataclass
class PDFDeviceTemplate:
    """Represents a PDF-based device template"""
    id: str
    name: str
    pdf_path: str
    device_match_patterns: List[str]
    device_type: str
    manufacturer: Optional[str] = None
    button_count: Optional[int] = None
    axis_count: Optional[int] = None
    hat_count: Optional[int] = None
    default_joystick_index: Optional[int] = None
    notes: Optional[str] = None
    deprecated: bool = False
    product_ids: Optional[List[str]] = None  # Product IDs for primary matching
    field_mapping_path: Optional[str] = None  # Custom field mapping path from registry


class PDFTemplateManager:
    """Manages PDF-based device templates"""

    def __init__(self, templates_dir: str):
        """
        Initialize PDF template manager

        Args:
            templates_dir: Path to visual-templates directory
        """
        self.templates_dir = templates_dir
        self.templates: List[PDFDeviceTemplate] = []
        self.load_templates()

    def load_templates(self):
        """Load template registry from JSON (v2.0 schema)"""
        registry_path = os.path.join(self.templates_dir, "template_registry.json")

        if not os.path.exists(registry_path):
            logger.warning(f"Template registry not found at {registry_path}")
            return

        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            schema_version = data.get('schema_version', '1.0')
            logger.info(f"Loading template registry (schema v{schema_version})")

            for template_data in data.get('templates', []):
                # Only load PDF templates (v2.0)
                if 'pdf' not in template_data:
                    logger.debug(f"Skipping non-PDF template: {template_data.get('id')}")
                    continue

                pdf_path = os.path.join(self.templates_dir, template_data['pdf'])

                # Verify PDF exists
                if not os.path.exists(pdf_path):
                    logger.warning(f"PDF not found for template {template_data['id']}: {pdf_path}")
                    continue

                # Resolve field mapping path if specified (only if it's a string path, not inline)
                field_mapping_path = None
                if 'field_mapping' in template_data and isinstance(template_data['field_mapping'], str):
                    field_mapping_path = os.path.join(self.templates_dir, template_data['field_mapping'])

                template = PDFDeviceTemplate(
                    id=template_data['id'],
                    name=template_data['name'],
                    pdf_path=pdf_path,
                    device_match_patterns=template_data['device_match_patterns'],
                    device_type=template_data['type'],
                    manufacturer=template_data.get('manufacturer'),
                    button_count=template_data.get('button_count'),
                    axis_count=template_data.get('axis_count'),
                    hat_count=template_data.get('hat_count'),
                    default_joystick_index=template_data.get('default_joystick_index'),
                    notes=template_data.get('notes'),
                    deprecated=template_data.get('deprecated', False),
                    product_ids=template_data.get('product_ids'),
                    field_mapping_path=field_mapping_path
                )
                self.templates.append(template)

            logger.info(f"Loaded {len(self.templates)} PDF templates")

        except Exception as e:
            logger.error(f"Error loading template registry: {e}", exc_info=True)

    def find_template(self, device_name: str, product_id: Optional[str] = None) -> Optional[PDFDeviceTemplate]:
        """
        Find a template that matches the device by product ID (primary) or device name (fallback)

        Args:
            device_name: Device name from XML (e.g., "VKBsim Gladiator EVO R")
            product_id: Optional product ID from device options (e.g., "0200231D-0000-0000-0000-504944564944")

        Returns:
            Matching PDFDeviceTemplate or None
        """
        if not device_name:
            return None

        # Normalize product ID for comparison (remove whitespace/braces)
        if product_id:
            product_id = product_id.strip().strip('{}')

        # Primary matching: Try product ID first (skip deprecated templates)
        if product_id:
            for template in self.templates:
                if template.deprecated:
                    continue

                if template.product_ids:
                    for pid in template.product_ids:
                        if pid.strip().strip('{}') == product_id:
                            logger.debug(f"Matched device '{device_name}' to template '{template.name}' via product ID {product_id}")
                            return template

        # Fallback matching: Try device name pattern matching (skip deprecated templates)
        device_name_lower = device_name.lower()
        for template in self.templates:
            if template.deprecated:
                continue

            for pattern in template.device_match_patterns:
                if pattern.lower() in device_name_lower:
                    if product_id:
                        logger.debug(f"Matched device '{device_name}' to template '{template.name}' via name pattern (product ID {product_id} not found in templates)")
                    else:
                        logger.debug(f"Matched device '{device_name}' to template '{template.name}' via name pattern")
                    return template

        logger.debug(f"No template found for device: {device_name}" + (f" (product ID: {product_id})" if product_id else ""))
        return None

    def get_template_by_id(self, template_id: str) -> Optional[PDFDeviceTemplate]:
        """Get template by ID"""
        for template in self.templates:
            if template.id == template_id:
                return template
        return None

    def get_all_templates(self) -> List[PDFDeviceTemplate]:
        """Get all available templates (excluding deprecated)"""
        return [t for t in self.templates if not t.deprecated]

    def get_pdf_form_fields(self, template: PDFDeviceTemplate) -> Dict[str, Dict]:
        """
        Extract form fields from a PDF template

        Args:
            template: PDFDeviceTemplate to extract fields from

        Returns:
            Dictionary mapping field names to field info:
            {
                'js1_button1': {'type': 'text', 'rect': [x0, y0, x1, y1], 'value': ''},
                'js1_x': {'type': 'text', 'rect': [x0, y0, x1, y1], 'value': ''},
                ...
            }
        """
        fields = {}

        try:
            doc = fitz.open(template.pdf_path)
            page = doc[0]  # Assume single-page templates

            for widget in page.widgets():
                field_info = {
                    'type': widget.field_type_string,
                    'rect': [widget.rect.x0, widget.rect.y0, widget.rect.x1, widget.rect.y1],
                    'value': widget.field_value or ''
                }
                fields[widget.field_name] = field_info

            doc.close()
            logger.debug(f"Extracted {len(fields)} form fields from {template.name}")

        except Exception as e:
            logger.error(f"Error extracting form fields from {template.pdf_path}: {e}", exc_info=True)

        return fields

    def load_field_mapping(self, template: PDFDeviceTemplate) -> Optional[Dict]:
        """
        Load field mapping for templates with non-standard field names

        Args:
            template: PDFDeviceTemplate to load mapping for

        Returns:
            Mapping dictionary or None if no mapping exists
        """
        # Use explicit field_mapping_path from template if specified
        if template.field_mapping_path:
            mapping_path = template.field_mapping_path
        else:
            # Fallback: look in same directory as PDF
            mapping_path = os.path.join(os.path.dirname(template.pdf_path), "field_mapping.json")

        if not os.path.exists(mapping_path):
            return None

        try:
            with open(mapping_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading field mapping from {mapping_path}: {e}")
            return None

    def populate_pdf(self, template: PDFDeviceTemplate, field_values: Dict[str, str],
                     output_path: Optional[str] = None) -> Optional[str]:
        """
        Populate PDF form fields with values

        Args:
            template: PDFDeviceTemplate to populate
            field_values: Dictionary mapping field names (e.g., "js1_button1") to values
            output_path: Optional path to save populated PDF. If None, creates temp file.

        Returns:
            Path to populated PDF or None on error
        """
        try:
            doc = fitz.open(template.pdf_path)
            page = doc[0]

            # Load field mapping if exists
            field_mapping = self.load_field_mapping(template)

            # Create reverse mapping: PDF field name -> value
            pdf_field_values = {}

            if field_mapping:
                # Template uses custom field names - need to map
                button_mapping = field_mapping.get('button_mapping', {})
                axis_mapping = field_mapping.get('axis_mapping', {})
                hat_mapping = field_mapping.get('hat_mapping', {})
                import re

                # FIRST PASS: Handle literal values (strings in brackets like "[52]")
                for pdf_name, mapped_value in button_mapping.items():
                    if isinstance(mapped_value, str) and mapped_value.startswith('[') and mapped_value.endswith(']'):
                        # Extract literal value (remove brackets)
                        literal_value = mapped_value[1:-1]
                        # Set literal value for all suffix variations
                        pdf_field_values[f"{pdf_name}_1"] = literal_value
                        pdf_field_values[f"{pdf_name}_2"] = literal_value
                        pdf_field_values[pdf_name] = literal_value

                # Similarly for axis mapping
                for pdf_name, mapped_value in axis_mapping.items():
                    if isinstance(mapped_value, str) and mapped_value.startswith('[') and mapped_value.endswith(']'):
                        # Extract literal value (remove brackets)
                        literal_value = mapped_value[1:-1]
                        # Set literal value for all suffix variations
                        pdf_field_values[f"{pdf_name}_1"] = literal_value
                        pdf_field_values[f"{pdf_name}_2"] = literal_value
                        pdf_field_values[pdf_name] = literal_value

                # Similarly for hat mapping
                for pdf_name, mapped_value in hat_mapping.items():
                    if isinstance(mapped_value, str) and mapped_value.startswith('[') and mapped_value.endswith(']'):
                        # Extract literal value (remove brackets)
                        literal_value = mapped_value[1:-1]
                        # Set literal value for all suffix variations
                        pdf_field_values[f"{pdf_name}_1"] = literal_value
                        pdf_field_values[f"{pdf_name}_2"] = literal_value
                        pdf_field_values[pdf_name] = literal_value

                # SECOND PASS: Handle normal button/axis/hat mappings from profile data
                for input_code, value in field_values.items():
                    # Handle button inputs (e.g., "js1_button5" -> 5)
                    button_match = re.match(r'js\d+_button(\d+)', input_code)
                    if button_match:
                        button_num = int(button_match.group(1))

                        # Find PDF field name for this button number
                        for pdf_name, btn_num in button_mapping.items():
                            # Skip literal values (already handled above)
                            if isinstance(btn_num, str) and btn_num.startswith('[') and btn_num.endswith(']'):
                                continue

                            # Convert string button numbers to int
                            try:
                                btn_num_int = int(btn_num)
                            except (ValueError, TypeError):
                                continue

                            if btn_num_int == button_num:
                                # Try both _1 and _2 suffixes (for multi-device PDFs)
                                pdf_field_values[f"{pdf_name}_1"] = value
                                pdf_field_values[f"{pdf_name}_2"] = value
                                # Also try without suffix
                                pdf_field_values[pdf_name] = value

                    # Handle axis inputs (e.g., "js1_x", "js1_y", "js1_rotz", "js1_axis_x", "js1_axis_rotz", "js1_slider1")
                    # The regex handles optional "axis_" prefix for axes
                    axis_match = re.match(r'js\d+_(?:axis_)?(x|y|z|rotx|roty|rotz|slider|throttle|rudder)(\d+)?', input_code, re.IGNORECASE)
                    if axis_match:
                        axis_name = axis_match.group(1).lower()
                        # If there's a number suffix, include it in the axis_name
                        if axis_match.group(2):
                            axis_name += axis_match.group(2)

                        # Find PDF field name for this axis
                        for pdf_name, mapped_axis in axis_mapping.items():
                            # Skip literal values (already handled above)
                            if isinstance(mapped_axis, str) and mapped_axis.startswith('[') and mapped_axis.endswith(']'):
                                continue

                            # Normalize both values for comparison (remove spaces, underscores, make lowercase)
                            mapped_axis_normalized = str(mapped_axis).lower().replace('_', '').replace(' ', '').replace('-', '')
                            axis_name_normalized = axis_name.replace('_', '').replace(' ', '').replace('-', '')

                            # Match if they're equivalent (e.g., "y" matches "y", "Y", "rotz" matches "rot_z" or "RotZ")
                            if mapped_axis_normalized == axis_name_normalized:
                                # Try both _1 and _2 suffixes (for multi-device PDFs)
                                pdf_field_values[f"{pdf_name}_1"] = value
                                pdf_field_values[f"{pdf_name}_2"] = value
                                # Also try without suffix
                                pdf_field_values[pdf_name] = value

                    # Handle hat inputs (e.g., "js2_hat1_up", "js2_hat1_down")
                    hat_match = re.match(r'js\d+_hat(\d+)_(up|down|left|right)', input_code, re.IGNORECASE)
                    if hat_match:
                        hat_num = int(hat_match.group(1))
                        hat_dir = hat_match.group(2).lower()

                        # Create standard hat identifier (e.g., "hat1_up", "hat2_left")
                        hat_identifier = f"hat{hat_num}_{hat_dir}"

                        # Find PDF field name for this hat direction
                        for pdf_name, mapped_hat in hat_mapping.items():
                            # Skip literal values (already handled above)
                            if isinstance(mapped_hat, str) and mapped_hat.startswith('[') and mapped_hat.endswith(']'):
                                continue

                            # Normalize the mapped hat value for comparison
                            mapped_hat_normalized = str(mapped_hat).lower().replace('_', '').replace(' ', '')
                            hat_identifier_normalized = hat_identifier.replace('_', '')

                            # Match if they're equivalent (e.g., "hat1_up" matches "hat1up" or "hat1_up")
                            if mapped_hat_normalized == hat_identifier_normalized:
                                # Try both _1 and _2 suffixes (for multi-device PDFs)
                                pdf_field_values[f"{pdf_name}_1"] = value
                                pdf_field_values[f"{pdf_name}_2"] = value
                                # Also try without suffix
                                pdf_field_values[pdf_name] = value
            else:
                # No mapping - PDF field names match input codes directly
                pdf_field_values = field_values

            # Populate form fields
            for widget in page.widgets():
                field_name = widget.field_name
                if field_name in pdf_field_values:
                    widget.field_value = pdf_field_values[field_name]
                    widget.update()

            # Save populated PDF
            if output_path is None:
                # Create temp file in same directory as template
                import tempfile
                temp_dir = os.path.dirname(template.pdf_path)
                fd, output_path = tempfile.mkstemp(suffix='.pdf', dir=temp_dir, prefix='populated_')
                os.close(fd)

            doc.save(output_path)
            doc.close()

            logger.debug(f"Populated PDF saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error populating PDF {template.pdf_path}: {e}", exc_info=True)
            return None

    def render_pdf_to_pixmap(self, pdf_path: str, dpi: int = 150, page_num: int = 0) -> Optional[QPixmap]:
        """
        Render a PDF page to QPixmap for display in Qt

        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for rendering (default 150)
            page_num: Page number to render (default 0 = first page)

        Returns:
            QPixmap or None on error
        """
        try:
            doc = fitz.open(pdf_path)

            if page_num >= len(doc):
                logger.error(f"Page {page_num} does not exist in {pdf_path}")
                doc.close()
                return None

            page = doc[page_num]

            # Render page to pixmap
            zoom = dpi / 72.0  # 72 DPI is default
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert PyMuPDF pixmap to QImage
            img_data = pix.samples  # raw pixel data
            qimage = QImage(
                img_data,
                pix.width,
                pix.height,
                pix.stride,
                QImage.Format.Format_RGB888 if pix.n == 3 else QImage.Format.Format_RGBA8888
            )

            # Convert QImage to QPixmap
            pixmap = QPixmap.fromImage(qimage)

            doc.close()
            logger.debug(f"Rendered PDF page to {pix.width}x{pix.height} pixmap @ {dpi} DPI")
            return pixmap

        except Exception as e:
            logger.error(f"Error rendering PDF {pdf_path}: {e}", exc_info=True)
            return None

    def render_template(self, template: PDFDeviceTemplate, field_values: Optional[Dict[str, str]] = None,
                        dpi: int = 150) -> Optional[QPixmap]:
        """
        Render a template with optional field values populated

        Args:
            template: PDFDeviceTemplate to render
            field_values: Optional dictionary of field values to populate
            dpi: Resolution for rendering

        Returns:
            QPixmap or None on error
        """
        pdf_path = template.pdf_path

        # If field values provided, create populated PDF first
        if field_values:
            pdf_path = self.populate_pdf(template, field_values)
            if pdf_path is None:
                return None

        # Render PDF to pixmap
        pixmap = self.render_pdf_to_pixmap(pdf_path, dpi=dpi)

        # Clean up temp file if created
        if field_values and pdf_path != template.pdf_path:
            try:
                os.remove(pdf_path)
            except Exception as e:
                logger.warning(f"Could not remove temp file {pdf_path}: {e}")

        return pixmap
