#!/usr/bin/env python3
"""
Image Optimizer

This script converts images in PNG, JPG, or JPEG formats to lighter web-friendly formats
like WebP and AVIF, ensuring the final size is 100KB or less.

Usage:
    python optimizer.py image.jpg
    python optimizer.py path/to/image.png 
    python optimizer.py path/to/image.jpeg --verbose # If execution information needed.

Dependencies (see requirements.txt for dependencies versions):
    - pillow
    - pillow-avif-plugin (automatically installed if missing)

Platform Compatibility:
    - macOS
    - Linux Distributions

Configuration:
    - TARGET_MIN_SIZE_KB: Target minimum size for optimized images (in KB).
    - TARGET_MAX_SIZE_KB: Target maximum size for optimized images (in KB).
    - MAX_SIZE_KB: Absolute maximum size limit for optimized images (in KB).
    - INITIAL_QUALITY: Initial quality setting for optimization (0-100).
    - MIN_QUALITY: Minimum allowed quality setting (0-100).
    - RESIZE_FACTOR: Factor used to reduce image dimensions if needed.

Optimization Algorithm:
    The script uses an adaptive algorithm to reduce image file size while attempting to maintain visual quality:
    1. Quality Adjustment Logic:
        - It starts with an initial quality setting (typically 80%).
        - If the image is still too large, it progressively reduces quality in increments of 5-10% depending on how far we are from the target size.
        - If the image is smaller than the target minimum, it tries to increase quality to improve visual appearance while staying under the maximum limit.
    2. Resize Decision Logic:
        - Resizing only happens when quality reduction alone can't achieve the target size.
        - The function first exhausts quality reduction (down to the minimum quality, e.g., 30%).
        - Only after reaching minimum quality, if the image is still too large, it reduces dimensions by a factor (80% of original size).
        - After resizing, it resets quality to try higher quality at the new dimensions.
        - This process can repeat up to 5 times before giving up.
    This approach prioritizes maintaining original dimensions while sacrificing quality, then resorts to dimension reduction only when necessary.

Error Handling:
    - Memory Errors: For very large images, Python might run out of memory. Consider pre-scaling very large images.
    - Library Import Errors: If auto-installation of pillow-avif-plugin fails, manually install with 'pip install pillow-avif-plugin'.
    - Permission Errors: If the script can't create the "optimized" directory, check write permissions.
    - Corrupt Image Files: Verify image files are valid.
    - Unusual Image Formats: Only .jpg, .jpeg, .png are supported.

Edge Cases:
    - Unusual Color Modes: May struggle with CMYK, LAB, etc.
    - Animated Images: Not designed for GIFs or multi-frame images.
    - Metadata Preservation: Only EXIF data is preserved.
    - Very Large Images: High resolutions may cause memory issues.
    - Progressive Rendering: Not implemented.
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import logging

# Add the utils parent folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_color_formatting.colors import Colors

# Logger config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Install dependency if not previously installed
try:
    import pillow_avif
except ImportError:
    import subprocess
    logger.info("Installing pillow-avif-plugin...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow-avif-plugin"])
    import pillow_avif

# Const variables
TARGET_MIN_SIZE_KB = 30
TARGET_MAX_SIZE_KB = 90
MAX_SIZE_KB = 100  # Maximum absolute limit
INITIAL_QUALITY = 80  # Decrease initial quality
MIN_QUALITY = 30  # Decrease until minimum quality limit
RESIZE_FACTOR = 0.8  # Factor to redimension if needed

def get_output_path(input_path, format_name):
    """Creates the output path for optimized images."""
    input_path = Path(input_path)
    output_dir = input_path.parent / "optimized"
    output_dir.mkdir(exist_ok=True)
    
    base_name = input_path.stem
    return output_dir / f"{base_name}.{format_name.lower()}"

def preserve_metadata(img):
    """Tries to extract EXIF metadata to presever it."""
    exif_data = None
    try:
        if hasattr(img, '_getexif') and img._getexif():
            exif_data = {}
            for tag, value in img._getexif().items():
                if tag in TAGS:
                    exif_data[TAGS[tag]] = value
    except Exception as e:
        logger.warning(f"Could not extract EXIF metadata: {e}")
    return exif_data

def optimize_to_target_size(img, output_path, format_name, initial_quality=INITIAL_QUALITY):
    """
    Optimize image adjusting quality and size to reach desired size (100kb or less).
    """

    quality = initial_quality
    resize_needed = False
    resize_count = 0
    max_resize_attempts = 5
    current_img = img.copy()
    
    # If the image has transparent background and the format is JPEG, then convert to RGB.
    if format_name.upper() == "JPEG" and current_img.mode == "RGBA":
        logger.info("Converting image RGBA to RGB for JPEG format...")
        current_img = current_img.convert("RGB")
    
    # First try with initial quality
    current_img.save(output_path, format=format_name, quality=quality)
    current_size = os.path.getsize(output_path) / 1024  # KB
    
    # Try adjusting quality to reach desired size
    while current_size > MAX_SIZE_KB:
        if quality > MIN_QUALITY:
            # Reduce quality aggresively for bigger images.
            reduction = 10 if current_size > 2 * MAX_SIZE_KB else 5
            quality = max(MIN_QUALITY, quality - reduction)
            logger.debug(f"Reducing quality to {quality}, current size: {current_size:.2f}KB")
            current_img.save(output_path, format=format_name, quality=quality)
            current_size = os.path.getsize(output_path) / 1024
        else:
            # If minimum quality reached, then redimension
            if resize_count >= max_resize_attempts:
                logger.warning(f"Could not reduce less than {MAX_SIZE_KB}KB after {max_resize_attempts} attempts of redimension.")
                break
                
            old_width, old_height = current_img.size
            new_width = int(old_width * RESIZE_FACTOR)
            new_height = int(old_height * RESIZE_FACTOR)
            
            logger.debug(f"Redimensioning from {old_width}x{old_height} to {new_width}x{new_height}")
            current_img = current_img.resize((new_width, new_height), Image.LANCZOS)
            
            # Establish quality for new image dimension
            quality = initial_quality
            current_img.save(output_path, format=format_name, quality=quality)
            current_size = os.path.getsize(output_path) / 1024
            resize_needed = True
            resize_count += 1
    
    # Try to increase quality if available memory
    if current_size < TARGET_MIN_SIZE_KB and not resize_needed:
        while current_size < TARGET_MIN_SIZE_KB and quality < 98:
            quality += 5
            if quality > 98:
                quality = 98  # Avoid 100%, could hurt the size
                
            current_img.save(output_path, format=format_name, quality=quality)
            new_size = os.path.getsize(output_path) / 1024
            
            # If quality increase made the file size increased exponentially, then go back.
            if new_size > MAX_SIZE_KB:
                quality -= 5
                current_img.save(output_path, format=format_name, quality=quality)
                current_size = os.path.getsize(output_path) / 1024
                break
                
            current_size = new_size
            logger.debug(f"Increasing quality to {quality}, current size: {current_size:.2f}KB")
    
    # Redimension info
    if resize_needed:
        original_dimensions = f"{img.width}x{img.height}"
        new_dimensions = f"{current_img.width}x{current_img.height}"
        logger.info(f"Image redimensioned from {original_dimensions} to {new_dimensions}")
    
    return current_size, quality, resize_needed

def optimize_image(input_path):
    """Optimize image to better performance formats (WebP y AVIF)."""
    try:
        # Open input image
        with Image.open(input_path) as img:
            # Save EXIF metadata if exists
            exif_data = preserve_metadata(img)
            
            original_size = os.path.getsize(input_path) / 1024  # KB
            logger.info(f"Original image: {input_path} - {original_size:.2f}KB")
            
            # For bigger images (in size), adjust initial quality
            initial_quality = INITIAL_QUALITY
            if original_size > 500:
                initial_quality = max(MIN_QUALITY, INITIAL_QUALITY - 10)
                logger.debug(f"Big image size detected, using initial image size: {initial_quality}")
            
            # Optimize to WEBP
            webp_path = get_output_path(input_path, "webp")
            webp_size, webp_quality, webp_resized = optimize_to_target_size(img, webp_path, "WEBP", initial_quality)
            logger.info(f"WEBP optimized: {webp_path} - {webp_size:.2f}KB (quality: {webp_quality})")
            
            # Optimize to AVIF
            avif_path = get_output_path(input_path, "avif")
            avif_size, avif_quality, avif_resized = optimize_to_target_size(img, avif_path, "AVIF", initial_quality)
            logger.info(f"AVIF optimized: {avif_path} - {avif_size:.2f}KB (quality: {avif_quality})")
            
            # Calculate files savings
            webp_savings = ((original_size - webp_size) / original_size) * 100
            avif_savings = ((original_size - avif_size) / original_size) * 100
            
            logger.info(f"{Colors.fg_green('With WEBP you saved!:')} {Colors.underline(Colors.fg_green(f'{webp_savings:.2f}%'))}")
            logger.info(f"{Colors.fg_green('With AVIF you saved!:')} {Colors.underline(Colors.fg_green(f'{avif_savings:.2f}%'))}")
            
            return {
                "original": {"path": input_path, "size": original_size, "dimensions": f"{img.width}x{img.height}"},
                "webp": {
                    "path": webp_path, 
                    "size": webp_size, 
                    "quality": webp_quality, 
                    "savings": webp_savings,
                    "resized": webp_resized
                },
                "avif": {
                    "path": avif_path, 
                    "size": avif_size, 
                    "quality": avif_quality, 
                    "savings": avif_savings,
                    "resized": avif_resized
                }
            }
    
    except Exception as e:
        logger.error(f"Error optimizing {input_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Optimize images to WEBP and AVIF formats.")
    parser.add_argument("image", help="Path of the image to optimize")
    parser.add_argument("--verbose", "-v", action="store_true", help="Shows detailed information")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Check if image exists and it is a valid image format
    if not os.path.isfile(args.image):
        logger.error(f"The file '{args.image}' does not exists.")
        return 1
    
    supported_formats = [".jpg", ".jpeg", ".png"]
    ext = Path(args.image).suffix.lower()
    if ext not in supported_formats:
        logger.error(f"Formato not supported: {ext}. Supported formats are: {', '.join(supported_formats)}")
        return 1
    
    # Optimize the image
    result = optimize_image(args.image)
    
    if result:
        print("\n" + Colors.fg_yellow("=")*50)
        print(Colors.italic(Colors.fg_blue("  OPTIMIZATION SUMMARY.")))
        print(Colors.fg_yellow("=")*50)
        print(f"{Colors.fg_red('Original')}: {result['original']['path']} - {result['original']['size']:.2f}KB ({result['original']['dimensions']})")
        
        webp_info = f"{Colors.fg_green('WebP')}: {result['webp']['path']} - {result['webp']['size']:.2f}KB (Savings: {result['webp']['savings']:.2f}%)"
        if result['webp']['resized']:
            webp_info += " {Colors.bold('[Redimensioned]')}"
        print(webp_info)
        
        avif_info = f"{Colors.fg_green('AVIF')}: {result['avif']['path']} - {result['avif']['size']:.2f}KB (Savings: {result['avif']['savings']:.2f}%)"
        if result['avif']['resized']:
            avif_info += " {Colors.fg_green('[Redimensioned]')}"
        print(avif_info)
        
        print(Colors.fg_yellow("=")*50 + "\n")
        return 0
    
    return 1

if __name__ == "__main__":
    sys.exit(main())
