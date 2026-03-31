SUMMARY_PROMPT = """You are an experienced engineering professional. You will be given an article title and content as input.
The article is from an engineering blog written by a big tech company on a technical topic.
Summarize only what is explicitly present in the content — do not infer, expand, or add information not stated in the article.

Your response must be strict JSON only, in this exact format:
{{"short_summary": "...", "key_points": ["...", "..."]}}

"short_summary" — 2-3 sentence TL;DR of the article.
"key_points" — list of up to 7 key points covering what the article actually discusses: facts, decisions, and how things work. Only include points genuinely present in the content. Do not pad to reach 7.

Article title: {title}
Article content: {content}"""
