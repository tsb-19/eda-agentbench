# PnR Report QA Task

You are given a Innovus physical implementation report in `report.txt`.

Read the report and answer the following questions. Write your answers to `answers.json` as a JSON object with the field name as key and your answer as value.

**Important:**
- For numeric answers, use the exact value from the report
- For string answers, use the exact text from the report
- For boolean answers, use `true` or `false`

## Questions

- What is the total wirelength?
- How many DRC violations are there?
- How many shorts are there?
- How many opens are there?
- How many antenna violations are there?
- Is route status clean? (true/false)
- What is the max horizontal overflow (in %)?
- What is the max vertical overflow (in %)?
- What is the total overflow?
- How many congested bins are there?
- What is the worst congestion layer?
- Does congestion pass? (true/false)
- What is the standard cell area?
- What is the macro area?
- What is the total cell area?
- How many buffers/inverters are there?

## Output Format

Write your answers to `answers.json`:
```json
{
  "field_name": "your_answer"
}
```

Replace `field_name` with the actual field name (e.g., `setup_wns`, `tool_family`, etc.).
