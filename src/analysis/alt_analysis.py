import base64
import requests
import json
from openai import OpenAI


def get_image_base64(image_url: str) -> str:
    response = requests.get(image_url)
    response.raise_for_status()
    return base64.b64encode(response.content).decode("utf-8")


def get_alt_suggestion(image_url: str, openai_api_key: str) -> str:
    client = OpenAI(api_key=openai_api_key)
    b64_image = get_image_base64(image_url)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an accessibility assistant. Describe images accurately as alt text."
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{b64_image}"}},
                    {"type": "text", "text": "What would be a good alt text for this image?"}
                ]
            }
        ]
    )

    return response.choices[0].message.content.strip()


def evaluate_alt(existing_alt: str, suggested_alt: str) -> str:
    if not existing_alt:
        return "❌ puuttuu"
    if existing_alt.strip().lower() == suggested_alt.strip().lower():
        return "✅ ok"
    else:
        return "⚠️ epätarkka"


def run_alt_analysis(images: list[dict], openai_api_key: str) -> list[dict]:
    results = []
    for img in images:
        try:
            suggestion = get_alt_suggestion(img["src"], openai_api_key)
            evaluation = evaluate_alt(img.get("alt", ""), suggestion)
            results.append({
                "src": img["src"],
                "alt_current": img.get("alt", ""),
                "alt_suggested": suggestion,
                "evaluation": evaluation
            })
        except Exception as e:
            results.append({
                "src": img["src"],
                "alt_current": img.get("alt", ""),
                "alt_suggested": f"[Virhe: {str(e)}]",
                "evaluation": "⚠️ ei analysoitu"
            })
    return results


def save_analysis_to_json(results: list[dict], output_path: str = "alt_analysis.json"):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


# Esimerkkikäyttö:
if __name__ == "__main__":
    example_images = [
        {"src": "https://example.com/image1.jpg", "alt": "vanha alt"},
        {"src": "https://example.com/image2.jpg", "alt": ""}
    ]
    api_key = "YOUR_OPENAI_API_KEY"
    output = run_alt_analysis(example_images, api_key)
    save_analysis_to_json(output)
