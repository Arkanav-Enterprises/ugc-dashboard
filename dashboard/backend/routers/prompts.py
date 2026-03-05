"""Router for prompt generation endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.prompt_generator import generate_prompt, PERSONAS

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class PromptRequest(BaseModel):
    persona: str
    scene_description: str
    prompt_type: str = "image"
    mode: str = "existing_character"
    reference_image_base64: str | None = None


class PromptResponse(BaseModel):
    prompt_json: dict
    persona: str
    prompt_type: str
    mode: str


@router.get("/personas")
async def list_personas():
    return {
        name: {
            "app_primary": data["app_primary"],
            "expression_style": data["expression_style"],
        }
        for name, data in PERSONAS.items()
    }


@router.post("/generate", response_model=PromptResponse)
async def generate(req: PromptRequest):
    if req.persona not in PERSONAS:
        raise HTTPException(400, f"Unknown persona: {req.persona}. Available: {list(PERSONAS.keys())}")
    if req.prompt_type not in ("image", "video"):
        raise HTTPException(400, "prompt_type must be 'image' or 'video'")
    if req.mode not in ("new_character", "existing_character", "mood_reference"):
        raise HTTPException(400, "mode must be 'new_character', 'existing_character', or 'mood_reference'")

    prompt_json = await generate_prompt(
        persona=req.persona,
        scene_description=req.scene_description,
        prompt_type=req.prompt_type,
        mode=req.mode,
        reference_image_base64=req.reference_image_base64,
    )

    return PromptResponse(
        prompt_json=prompt_json,
        persona=req.persona,
        prompt_type=req.prompt_type,
        mode=req.mode,
    )
