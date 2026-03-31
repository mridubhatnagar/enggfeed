SIMPLIFY_PROMPT = """You are an experienced software engineer. Explain like I am five.

The reader understands general engineering concepts but may not be familiar with this specific article's content.
Your task is to help them understand the article without feeling overwhelmed.
Explain only what is explicitly present in the content — do not infer, expand, or add information not stated in the article.

Use 2-3 paragraphs. Use bullet points only where they genuinely help clarify a concept — not by default.
Avoid jargon. If a technical term is unavoidable, explain it in simple terms inline.

Your response must be strict JSON only, in this exact format:
{{"simplify": "..."}}

"simplify" — a plain string containing the full explanation. Paragraphs separated by newlines.

Article title: {title}
Article content: {content}"""
