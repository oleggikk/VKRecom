import torch
from diffusers import StableDiffusionPipeline

def generate_image(prompt: str, seed: int = 42, num_inference_steps: int = 50, guidance_scale: float = 8.5):
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Using device: {device}")

    # Загружаем модель с Hugging Face
    model_id = "stabilityai/stable-diffusion-2-1-base"
    pipeline = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
    pipeline.to(device)

    # Устанавливаем генератор с заданным seed
    generator = torch.manual_seed(seed)

    # Генерируем изображение
    with torch.autocast(device_type=device.type if device.type != "cpu" else "cpu"):
        image = pipeline(prompt=prompt, num_inference_steps=num_inference_steps, guidance_scale=guidance_scale, generator=generator).images[0]

    return image
