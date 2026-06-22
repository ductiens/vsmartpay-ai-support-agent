import cloudinary
import cloudinary.uploader
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Configure Cloudinary if credentials are provided
if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True
    )
    is_cloudinary_configured = True
else:
    is_cloudinary_configured = False
    logger.warning("Cloudinary credentials are not fully configured. File upload to Cloudinary will be skipped.")

async def upload_file_to_cloudinary(file_bytes: bytes, file_name: str) -> str | None:
    """
    Uploads a file to Cloudinary and returns the secure URL.
    Returns None if Cloudinary is not configured or upload fails.
    """
    if not is_cloudinary_configured:
        return None

    try:
        # Determine resource type based on extension
        # Cloudinary uses 'raw' for non-image/video files like docs, pdfs, etc., unless specified otherwise.
        # But 'auto' tells Cloudinary to automatically detect.
        # Keep extension for raw files so Cloudinary serves with correct Content-Type
        ext = ""
        if '.' in file_name:
            ext = "." + file_name.split('.')[-1]
        base_name = file_name.split('.')[0]
        
        result = cloudinary.uploader.upload(
            file_bytes,
            resource_type="raw",
            public_id=base_name + "_" + str(hash(file_bytes))[:8] + ext,
            use_filename=True,
            unique_filename=True
        )
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"Failed to upload file to Cloudinary: {e}")
        with open("cloudinary_error.log", "a") as f:
            f.write(f"Failed to upload {file_name}: {str(e)}\n")
        return None
