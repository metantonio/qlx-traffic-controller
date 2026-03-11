import os
import base64
import requests
import logging
from backend.core.config import settings
from backend.tools.mcp_registry import MCPTool, system_registry

logger = logging.getLogger("QLX-TC.Tools.Vision")

async def ocr_extract_text(file_path: str) -> str:
    """Uses a specialized OCR model (maternion/LightOnOCR-2:1b) to extract text from an image."""
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found."
    
    try:
        logger.info(f"Performing OCR on {file_path} using maternion/LightOnOCR-2:1b")
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        payload = {
            "model": "maternion/LightOnOCR-2:1b",
            "prompt": "Extract all text from this image exactly as it is, maintaining formatting and code structure if present.",
            "images": [encoded_string],
            "stream": False
        }
        
        response = requests.post(f"{settings.OLLAMA_BASE_URL}/api/generate", json=payload, timeout=60)
        
        if response.status_code == 200:
            text = response.json().get("response", "").strip()
            if not text:
                return "OCR completed but no text was detected in the image."
            return text
        else:
            return f"Error from Ollama (Status {response.status_code}): {response.text}"
            
    except requests.exceptions.Timeout:
        return "Error: OCR process timed out. The image might be too complex or the model is slow."
    except Exception as e:
        logger.error(f"OCR Tool Error: {str(e)}")
        return f"OCR Error: {str(e)}"

ocr_tool = MCPTool(
    name="ocr_extract_text",
    description="Extracts all text and code from an image file (png, jpg, jpeg, bmp) using a specialized vision model. Use this when you need to read content from an image.",
    parameters={
        "file_path": {"type": "string", "description": "Absolute path to the image file"}
    },
    handler=ocr_extract_text
)

# Register the tool
system_registry.register(ocr_tool)
