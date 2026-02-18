## Response Format

Provide your evaluation as follows:

## Analysis
[Your detailed evaluation from your specialized perspective, referencing specific evidence from the resume]

## Key Strengths
[Bullet points of strengths relevant to your evaluation focus]

## Concerns
[Bullet points of concerns or red flags from your perspective]

## Verdict
[One-paragraph final assessment]

Finally, provide your structured payload in a JSON code block:

```json
{
  "score": X,
  "verdict": "your one-paragraph verdict",
  "strengths": ["strength1", "strength2"],
  "concerns": ["concern1", "concern2"]
}
```

Where score is 1-5 (1=poor fit, 5=excellent fit). This block is machine-parsed.
