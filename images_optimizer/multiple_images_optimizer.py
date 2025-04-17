#!/usr/bin/env python3
"""
Batch Image Optimizer

This script converts multiple images in a folder from PNG, JPG, or JPEG formats to lighter web-friendly formats
like WebP and AVIF, ensuring the final size is 100KB or less.

Usage:
    python batch_optimizer.py folder_path
    python batch_optimizer.py path/to/images --verbose # If execution information needed.

Dependencies (see requirements.txt for dependencies versions):
    - pillow
    - pillow-avif-plugin (automatically installed if missing)
    - tqdm (for progress bars)

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
    - Format Decision Errors: If the format decision is invalid, the script will exit with an error.
    - Library Import Errors: If auto-installation of pillow-avif-plugin fails, manually install with 'pip install pillow-avif-plugin'.
    - Permission Errors: If the script can't create the "optimized" directory, check write permissions.
    - Corrupt Image Files: Verify image files are valid.
    - Unusual Image Formats: Only .jpg, .jpeg, .png are supported.

Edge Cases:
    - Low-end Hardware: AVIF processing can be slow on low-end hardware.
    - Unusual Color Modes: May struggle with CMYK, LAB, etc.
    - Animated Images: Not designed for GIFs or multi-frame images.
    - Metadata Preservation: Only EXIF data is preserved.
    - Very Large Images: High resolutions may cause memory issues.
    - Progressive Rendering: Not implemented.
"""

import os
import sys
import argparse
import time
import concurrent.futures
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import logging

# Add the utils parent folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from text_color_formatting.colors import Colors
except ImportError:
    # Simple Colors class if the imported module is not available
    class Colors:
        @staticmethod
        def fg_green(text): return f"\033[32m{text}\033[0m"
        
        @staticmethod
        def fg_red(text): return f"\033[31m{text}\033[0m"
        
        @staticmethod
        def fg_yellow(text): return f"\033[33m{text}\033[0m"
        
        @staticmethod
        def fg_blue(text): return f"\033[34m{text}\033[0m"
        
        @staticmethod
        def bold(text): return f"\033[1m{text}\033[0m"
        
        @staticmethod
        def underline(text): return f"\033[4m{text}\033[0m"
        
        @staticmethod
        def italic(text): return f"\033[3m{text}\033[0m"

# Logger config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Install dependencies if not previously installed
try:
    import pillow_avif
except ImportError:
    import subprocess
    logger.info("Installing pillow-avif-plugin...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow-avif-plugin"])
    import pillow_avif

try:
    from tqdm import tqdm
except ImportError:
    import subprocess
    logger.info("Installing tqdm for progress bars...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
    from tqdm import tqdm

# Const variables
TARGET_MIN_SIZE_KB = 30
TARGET_MAX_SIZE_KB = 90
MAX_SIZE_KB = 100  # Maximum absolute limit
INITIAL_QUALITY = 80  # Decrease initial quality
MIN_QUALITY = 30  # Decrease until minimum quality limit
RESIZE_FACTOR = 0.8  # Factor to redimension if needed
MAX_WORKERS = 4  # Number of concurrent workers for parallel processing
USER_INPUT_DIR_NAME = input(f"\n{Colors.fg_cyan('How would you like to name the folder?')}\n{Colors.blink(Colors.underline('R:'))} ").strip()

# Ask user for desired web formate, either WebP, AVIF, or both.
format_decision = int(input(f"\n\n{Colors.fg_cyan('Type just the number with no lead and trailing spaces, to decide if want the output files in:')} \n1) WebP format.\n2) AVIF format.\n3) Both.\n{Colors.blink(Colors.underline('R:'))} ").strip())


def get_output_path(input_path, format_name):
    """Creates the output path for optimized images."""
    input_path = Path(input_path)
    output_dir = input_path.parent / USER_INPUT_DIR_NAME
    output_dir.mkdir(exist_ok=True)
    
    base_name = input_path.stem
    return output_dir / f"{base_name}.{format_name.lower()}"

def preserve_metadata(img):
    """Tries to extract EXIF metadata to preserve it."""
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

def get_optimal_workers(format_name):
    """Determine optimal number of workers based on format and system resources"""
    if format_name.upper() == "AVIF":
        return max(1, min(2, MAX_WORKERS // 2))  # Max 2 workers for AVIF on low-end hardware
    return MAX_WORKERS  # Keep original for WebP

def get_initial_quality(format_name, original_size):
    """Get format-specific initial quality to reduce processing time"""
    if format_name.upper() == "AVIF":
        # More aggressive quality reduction for AVIF to improve processing speed
        if original_size > 500:
            return max(MIN_QUALITY, INITIAL_QUALITY - 20)
        return max(MIN_QUALITY, INITIAL_QUALITY - 15)
    # For WebP, keep original logic but slightly more aggressive for large files
    if original_size > 500:
        return max(MIN_QUALITY, INITIAL_QUALITY - 10)
    return INITIAL_QUALITY

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
        logger.debug("Converting image RGBA to RGB for JPEG format...")
        current_img = current_img.convert("RGB")
    
    # First try with initial quality
    current_img.save(output_path, format=format_name, quality=quality)
    current_size = os.path.getsize(output_path) / 1024  # KB
    
    # Try adjusting quality to reach desired size
    while current_size > MAX_SIZE_KB:
        if quality > MIN_QUALITY:
            # Reduce quality aggressively for bigger images.
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
        logger.debug(f"Image redimensioned from {original_dimensions} to {new_dimensions}")
    
    return current_size, quality, resize_needed

def optimize_image(input_path):
    """Optimize image to better performance formats (WebP and AVIF)."""
    try:
        # Check if output files already exist
        webp_path = get_output_path(input_path, "webp")
        avif_path = get_output_path(input_path, "avif")
        
        if webp_path.exists() and avif_path.exists():
            logger.debug(f"Skipping already optimized image: {input_path}")
            return {
                "status": "skipped",
                "path": input_path,
                "reason": "Already optimized"
            }
        
        # Open input image
        with Image.open(input_path) as img:
            # Save EXIF metadata if exists
            exif_data = preserve_metadata(img)
            
            original_size = os.path.getsize(input_path) / 1024  # KB
            logger.debug(f"Original image: {input_path} - {original_size:.2f}KB")
            
            match format_decision:
                case 1:
                    # Optimize to WEBP
                    initial_quality = get_initial_quality("WEBP", original_size)
                    webp_size, webp_quality, webp_resized = optimize_to_target_size(img, webp_path, "WEBP", initial_quality)
                    logger.debug(f"WEBP optimized: {webp_path} - {webp_size:.2f}KB (quality: {webp_quality})")
                    
                    # Calculate file savings.
                    webp_savings = ((original_size - webp_size) / original_size) * 100
                    
                    return {
                            "status": "success",
                            "original": {"path": input_path, "size": original_size, "dimensions": f"{img.width}x{img.height}"},
                            "webp": {
                            "path": webp_path,
                            "size": webp_size,
                            "quality": webp_quality,
                            "savings": webp_savings,
                            "resized": webp_resized
                    }}

                case 2:
                    # Optimize to AVIF
                    initial_quality = get_initial_quality("AVIF", original_size)
                    avif_size, avif_quality, avif_resized = optimize_to_target_size(img, avif_path, "AVIF", initial_quality)
                    logger.debug(f"AVIF optimized: {avif_path} - {avif_size:.2f}KB (quality: {avif_quality})")
                    
                    # Calculate file savings.
                    avif_savings = ((original_size - avif_size) / original_size) * 100

                    return {
                            "status": "success",
                            "original": {"path": input_path, "size": original_size, "dimensions": f"{img.width}x{img.height}"},
                            "avif": {
                            "path": avif_path,
                            "size": avif_size,
                            "quality": avif_quality,
                            "savings": avif_savings,
                            "resized": avif_resized
                    }}

                case 3:
                    # Optimize to both formats
                    webp_initial_quality = get_initial_quality("WEBP", original_size)
                    avif_initial_quality = get_initial_quality("AVIF", original_size)
                    
                    # Optimize to WEBP
                    webp_size, webp_quality, webp_resized = optimize_to_target_size(img, webp_path, "WEBP", webp_initial_quality)
                    logger.debug(f"WEBP optimized: {webp_path} - {webp_size:.2f}KB (quality: {webp_quality})")
                    
                    # Optimize to AVIF
                    avif_size, avif_quality, avif_resized = optimize_to_target_size(img, avif_path, "AVIF", avif_initial_quality)
                    logger.debug(f"AVIF optimized: {avif_path} - {avif_size:.2f}KB (quality: {avif_quality})")
                    
                    # Calculate files savings
                    webp_savings = ((original_size - webp_size) / original_size) * 100
                    avif_savings = ((original_size - avif_size) / original_size) * 100
                    
                    return {
                        "status": "success",
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
                    }}
                
                case _:
                    logger.error(f"Invalid format decision: {format_decision}")
                    return {
                        "status": "error",
                        "path": input_path,
                        "error": "Invalid format decision"
                    }
    
    except Exception as e:
        logger.error(f"Error optimizing {input_path}: {e}")
        return {
            "status": "error",
            "path": input_path,
            "error": str(e)
        }

def find_images_in_folder(folder_path):
    """Find all image files in the specified folder."""
    supported_formats = [".jpg", ".jpeg", ".png"]
    folder_path = Path(folder_path)
    
    if not folder_path.exists():
        logger.error(f"The folder '{folder_path}' does not exist.")
        return []
    
    if not folder_path.is_dir():
        logger.error(f"'{folder_path}' is not a directory.")
        return []
    
    image_files = []
    for format_ext in supported_formats:
        image_files.extend(list(folder_path.glob(f"*{format_ext}")))
        image_files.extend(list(folder_path.glob(f"*{format_ext.upper()}")))
    
    return image_files

def process_batch(image_files, max_workers=MAX_WORKERS):
    """Process a batch of images in parallel."""
    results = {
        "total": len(image_files),
        "successful": 0,
        "skipped": 0,
        "failed": 0,
        "details": [],
        "total_savings": {"webp": 0, "avif": 0},
        "start_time": time.time()
    }
    
    # Determine optimal worker count based on format
    optimal_workers = get_optimal_workers("AVIF" if format_decision == 2 else "WEBP")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=optimal_workers) as executor:
        # Submit all tasks
        future_to_image = {executor.submit(optimize_image, str(img_path)): img_path for img_path in image_files}
        
        # Process results as they complete with a progress bar
        with tqdm(total=len(image_files), desc="Optimizing images", unit="img") as pbar:
            for future in concurrent.futures.as_completed(future_to_image):
                img_path = future_to_image[future]
                try:
                    result = future.result()
                    results["details"].append(result)
                    
                    if result["status"] == "success":
                        results["successful"] += 1
                        if format_decision == 1:
                            results["total_savings"]["webp"] += result.get("webp", {}).get("savings", 0)
                        elif format_decision == 2:
                            results["total_savings"]["avif"] += result.get("avif", {}).get("savings", 0)
                        else:
                            results["total_savings"]["webp"] += result.get("webp", {}).get("savings", 0)
                            results["total_savings"]["avif"] += result.get("avif", {}).get("savings", 0)
                    elif result["status"] == "skipped":
                        results["skipped"] += 1
                    else:
                        results["failed"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing {img_path}: {e}")
                    results["failed"] += 1
                    results["details"].append({
                        "status": "error",
                        "path": str(img_path),
                        "error": str(e)
                    })
                
                pbar.update(1)
    
    # Calculate average savings
    if results["successful"] > 0:
        results["average_savings"] = {
            "webp": results["total_savings"]["webp"] / results["successful"],
            "avif": results["total_savings"]["avif"] / results["successful"]
        }
    else:
        results["average_savings"] = {"webp": 0, "avif": 0}
    
    results["total_time"] = time.time() - results["start_time"]
    
    return results

def print_summary(results):
    """Print a summary of the batch processing results."""
    print("\n" + Colors.fg_yellow("=")*70)
    print(Colors.italic(Colors.fg_blue("  BATCH OPTIMIZATION SUMMARY")))
    print(Colors.fg_yellow("=")*70)
    
    print(f"Total images processed: {results['total']}")
    print(f"Successfully optimized: {Colors.fg_green(str(results['successful']))}")
    print(f"Skipped (already optimized): {Colors.fg_yellow(str(results['skipped']))}")
    print(f"Failed: {Colors.fg_red(str(results['failed']))}")
    
    if results['successful'] > 0:
        print(f"\nAverage savings:")

        if format_decision == 1:
            print(f"  WebP: {results['average_savings']['webp']:.2f}%")
        elif format_decision == 2:
            print(f"  AVIF: {results['average_savings']['avif']:.2f}%")
        else:
            print(f"  WebP: {results['average_savings']['webp']:.2f}%")
            print(f"  AVIF: {results['average_savings']['avif']:.2f}%")
    
    print(f"\nTotal processing time: {results['total_time'] / 60:.2f} minutes")
    
    # Print errors if any
    errors = [detail for detail in results["details"] if detail.get("status") == "error"]
    if errors:
        print(f"\n{Colors.fg_red('Errors:')} (Total: {len(errors)})")
        for error in errors[:5]:  # Show only the first 5 errors
            print(f"  - {error['path']}: {error['error']}")
        
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")
    
    print(Colors.fg_yellow("=")*70 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Batch optimize images to WEBP and AVIF formats.")
    parser.add_argument("folder", help="Path of the folder containing images to optimize")
    parser.add_argument("--verbose", "-v", action="store_true", help="Shows detailed information")
    parser.add_argument("--workers", "-w", type=int, default=MAX_WORKERS, help=f"Number of concurrent workers (default: {MAX_WORKERS})")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Find images in the specified folder
    image_files = find_images_in_folder(args.folder)
    
    if not image_files:
        logger.error(f"No supported image files found in '{args.folder}'.")
        return 1
    
    logger.info(f"Found {len(image_files)} image(s) to process.")
    
    # Process images
    results = process_batch(image_files, max_workers=args.workers)
    
    # Print summary
    print_summary(results)
    
    # Create detailed report
    report_path = Path(args.folder) / "optimization_report.txt"
    try:
        with open(report_path, "w") as f:
            f.write(f"BATCH IMAGE OPTIMIZATION REPORT\n")
            f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"Total images: {results['total']}\n")
            f.write(f"Successfully optimized: {results['successful']}\n")
            f.write(f"Skipped (already optimized): {results['skipped']}\n")
            f.write(f"Failed: {results['failed']}\n\n")
            
            if results['successful'] > 0:
                f.write(f"Average savings:\n")
                if format_decision == 1:
                    f.write(f"  WebP: {results['average_savings']['webp']:.2f}%\n")
                elif format_decision == 2:
                    f.write(f"  AVIF: {results['average_savings']['avif']:.2f}%\n")
                else:
                    f.write(f"  WebP: {results['average_savings']['webp']:.2f}%\n")
                    f.write(f"  AVIF: {results['average_savings']['avif']:.2f}%\n")
            
            f.write(f"Total processing time: {results['total_time'] / 60:.2f} minutes\n\n")
            
            f.write("SUCCESSFULLY OPTIMIZED IMAGES:\n")
            for detail in results["details"]:
                if detail.get("status") == "success":
                    original = detail["original"]
                    if format_decision == 1:
                        webp = detail["webp"]
                        avif = None
                    elif format_decision == 2:
                        webp = None
                        avif = detail["avif"]
                    else:
                        webp = detail["webp"]
                        avif = detail["avif"]
                    
                    f.write(f"\n- Original: {original['path']}\n")
                    f.write(f"  Size: {original['size']:.2f}KB, Dimensions: {original['dimensions']}\n")
                    if webp:
                        f.write(f"  WebP: {webp['path']} - {webp['size']:.2f}KB (Savings: {webp['savings']:.2f}%, Quality: {webp['quality']})\n")
                    if avif:
                        f.write(f"  AVIF: {avif['path']} - {avif['size']:.2f}KB (Savings: {avif['savings']:.2f}%, Quality: {avif['quality']})\n")

            if results['skipped'] > 0:
                f.write("\nSKIPPED IMAGES:\n")
                for detail in results["details"]:
                    if detail.get("status") == "skipped":
                        f.write(f"- {detail['path']} ({detail['reason']})\n")
            
            if results['failed'] > 0:
                f.write("\nFAILED IMAGES:\n")
                for detail in results["details"]:
                    if detail.get("status") == "error":
                        f.write(f"- {detail['path']}: {detail['error']}\n")
        
        logger.info(f"Detailed report saved to: {report_path}")
        
    except Exception as e:
        logger.error(f"Failed to write detailed report: {e}")
    
    return 0 if results["failed"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
