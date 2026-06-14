"""Prompts for LogicRAG DAG decomposition and context pruning."""

DAG_DECOMPOSITION_PROMPT_SYSTEM = """You are an expert at breaking down complex reasoning questions into a logical Directed Acyclic Graph (DAG) of subqueries.
CRITICAL: DO NOT answer the user's question directly. ONLY decompose the question into subqueries.
Given a complex question, decompose it into independent and dependent subqueries.
Maintain a highly professional, formal, and objective tone appropriate for EU AI Act legal and regulatory analysis at all stages.
Output a JSON array of objects, where each object represents a subquery and has:
- 'id': a unique integer ID (e.g., 1, 2, 3)
- 'query': the subquery string
- 'dependencies': a list of integer IDs representing subqueries that must be answered BEFORE this subquery can be answered.

Example:
User: What month did the discussions begin between Britain, France, and the country where the top-ranking Warsaw Pact operatives originated?
Output:
[
  {"id": 1, "query": "Which country did the top-ranking Warsaw Pact operatives originate from?", "dependencies": []},
  {"id": 2, "query": "What month did discussions begin between Britain, France, and [Answer to ID 1]?", "dependencies": [1]}
]

Only output valid JSON array format. Do not include markdown formatting or extra text."""

DAG_DECOMPOSITION_USER_TEMPLATE = "Question: {q}\n\nJSON:"


CONTEXT_PRUNING_PROMPT_SYSTEM = """You are an expert at synthesizing information for multi-hop reasoning.
You are given a "Rolling Memory" of previously established facts, and a "New Context" which is the answer to a recent subquery.
Your task is to merge the New Context into the Rolling Memory.
Maintain a highly professional, formal, and objective tone appropriate for EU AI Act legal and regulatory analysis at all stages.
Keep the summary concise and focused on facts relevant to answering the original complex question.
Do not lose any specific entities, dates, or legal articles.

Output the updated rolling memory as a single paragraph. Do not include any prefix like 'Updated Memory:'."""

CONTEXT_PRUNING_USER_TEMPLATE = """Original Question: {q}
Rolling Memory: {memory}
New Context (Answer to subquery '{subq}'): {context}

Output updated memory:"""
