from fastapi import APIRouter, File, UploadFile
from .parser import parse_eml_content
from .router import EmailSandbox

router = APIRouter()

@router.post("/analyze")
async def analyze_email(file: UploadFile = File(...)):
    """
    Receives an .eml file and forwards it to the EmailSandbox.
    """
    try:
        content = await file.read()
        parsed_email = parse_eml_content(content)
        
        sandbox = EmailSandbox()
        # Ensure we await the async method
        result = await sandbox.analyze_email_components(parsed_email)
        
        return {
            "success": True,
            "filename": file.filename,
            "analysis": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
