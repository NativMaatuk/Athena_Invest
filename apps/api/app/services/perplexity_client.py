from __future__ import annotations

import httpx

from ..schemas import PerplexityCitation


class PerplexityClient:
    BASE_URL = "https://api.perplexity.ai/chat/completions"

    async def ask(
        self,
        *,
        api_key: str,
        question: str,
        model: str,
        ticker_context: str | None = None,
    ) -> tuple[str, list[PerplexityCitation], str]:
        user_prompt = question.strip()
        if ticker_context:
            user_prompt = (
                f"שאלה פיננסית עבור הטיקר {ticker_context.strip().upper()}:\n"
                f"{question.strip()}"
            )

        payload = {
            "model": model,
            "search_mode": "web",
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "ענה בעברית ברורה, מדויקת ותמציתית עם דגש פיננסי."},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(self.BASE_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        answer = ""
        if choices:
            answer = str((choices[0].get("message") or {}).get("content") or "").strip()
        citations = [
            PerplexityCitation(
                title=item.get("title"),
                url=item.get("url"),
                date=item.get("date"),
            )
            for item in (data.get("search_results") or [])
            if isinstance(item, dict)
        ]
        model_name = str(data.get("model") or model)
        return answer, citations, model_name
