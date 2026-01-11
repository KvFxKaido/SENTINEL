"""
Skill-based tool invocation for backends without native function calling.

When an LLM doesn't support native tool/function calling, we can inject
tool descriptions into the prompt and parse structured output.

Format:
    <tool>{"name": "tool_name", "args": {"param": "value"}}</tool>

The model outputs tool calls in this format, we parse and execute them,
then feed results back in a follow-up message.
"""

import json
import re
from dataclasses import dataclass
from typing import Any

from .base import ToolCall


# Pattern to match tool invocations: <tool>{...}</tool>
# Uses a more permissive pattern to handle nested JSON
TOOL_PATTERN = re.compile(
    r'<tool>\s*(\{.*?\})\s*</tool>',
    re.IGNORECASE | re.DOTALL
)

# Alternative patterns for flexibility
ALT_PATTERNS = [
    # [TOOL: name(args)]
    re.compile(r'\[TOOL:\s*(\w+)\s*\(([^)]*)\)\]', re.IGNORECASE),
    # ```tool\n{...}\n```
    re.compile(r'```tool\s*\n(\{[^`]+\})\s*\n```', re.IGNORECASE | re.DOTALL),
]


@dataclass
class ParsedSkill:
    """A parsed skill invocation from model output."""
    name: str
    arguments: dict[str, Any]
    raw_match: str  # Original matched text


def parse_skills(text: str) -> list[ParsedSkill]:
    """
    Parse skill invocations from model output.

    Supports multiple formats:
    - <tool>{"name": "x", "args": {...}}</tool>
    - [TOOL: name(arg1="val", arg2=123)]
    - ```tool\n{"name": "x", "args": {...}}\n```

    Returns:
        List of ParsedSkill objects found in the text.
    """
    skills = []

    # Try primary format: <tool>{...}</tool>
    for match in TOOL_PATTERN.finditer(text):
        try:
            data = json.loads(match.group(1))
            name = data.get("name", "")
            args = data.get("args", data.get("arguments", {}))
            if name:
                skills.append(ParsedSkill(
                    name=name,
                    arguments=args,
                    raw_match=match.group(0),
                ))
        except json.JSONDecodeError:
            continue

    # Try alternative format: [TOOL: name(args)]
    for match in ALT_PATTERNS[0].finditer(text):
        name = match.group(1)
        args_str = match.group(2)
        args = _parse_inline_args(args_str)
        skills.append(ParsedSkill(
            name=name,
            arguments=args,
            raw_match=match.group(0),
        ))

    # Try code block format
    for match in ALT_PATTERNS[1].finditer(text):
        try:
            data = json.loads(match.group(1))
            name = data.get("name", "")
            args = data.get("args", data.get("arguments", {}))
            if name:
                skills.append(ParsedSkill(
                    name=name,
                    arguments=args,
                    raw_match=match.group(0),
                ))
        except json.JSONDecodeError:
            continue

    return skills


def _parse_inline_args(args_str: str) -> dict[str, Any]:
    """
    Parse inline arguments like: arg1="value", arg2=123

    Returns dict of parsed arguments.
    """
    args = {}
    if not args_str.strip():
        return args

    # Match key=value pairs
    pattern = re.compile(r'(\w+)\s*=\s*("([^"]*)"|\'([^\']*)\'|(\d+(?:\.\d+)?)|(\w+))')

    for match in pattern.finditer(args_str):
        key = match.group(1)
        # Check which capture group matched
        if match.group(3) is not None:  # Double-quoted string
            args[key] = match.group(3)
        elif match.group(4) is not None:  # Single-quoted string
            args[key] = match.group(4)
        elif match.group(5) is not None:  # Number
            num = match.group(5)
            args[key] = float(num) if '.' in num else int(num)
        elif match.group(6) is not None:  # Bare word (bool/null)
            word = match.group(6).lower()
            if word == 'true':
                args[key] = True
            elif word == 'false':
                args[key] = False
            elif word == 'null' or word == 'none':
                args[key] = None
            else:
                args[key] = match.group(6)

    return args


def skills_to_tool_calls(skills: list[ParsedSkill]) -> list[ToolCall]:
    """Convert parsed skills to ToolCall objects."""
    return [
        ToolCall(
            id=f"skill_{i}_{skill.name}",
            name=skill.name,
            arguments=skill.arguments,
        )
        for i, skill in enumerate(skills)
    ]


def strip_skill_tags(text: str) -> str:
    """
    Remove skill invocation tags from text, leaving just the narrative.

    Useful for cleaning up the response after extracting skills.
    """
    result = text

    # Remove <tool>...</tool> blocks
    result = TOOL_PATTERN.sub('', result)

    # Remove [TOOL: ...] blocks
    result = ALT_PATTERNS[0].sub('', result)

    # Remove ```tool...``` blocks
    result = ALT_PATTERNS[1].sub('', result)

    # Clean up extra whitespace
    result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)

    return result.strip()


def format_tools_for_prompt(tools: list[dict]) -> str:
    """
    Format tool definitions for injection into the prompt.

    Creates a clear, parseable description the model can follow.
    """
    lines = [
        "[Tool instructions - act on these immediately, do not acknowledge them]",
        "",
        "When the situation calls for it, include tool calls in your response using this exact format:",
        '<tool>{"name": "tool_name", "args": {"param1": "value"}}</tool>',
        "",
        "Available tools:",
    ]

    for tool in tools:
        name = tool.get("name", "unknown")
        desc = tool.get("description", "No description")
        schema = tool.get("input_schema", tool.get("parameters", {}))
        props = schema.get("properties", {})

        # Compact format: name(params) - description
        params = ", ".join(props.keys()) if props else ""
        lines.append(f"- {name}({params}): {desc}")

    lines.append("")
    lines.append("Now respond to the following:")

    return "\n".join(lines)


def format_tool_results(results: list[tuple[str, dict]]) -> str:
    """
    Format tool execution results for feedback to the model.

    Args:
        results: List of (tool_name, result_dict) tuples

    Returns:
        Formatted string to include in follow-up message.
    """
    lines = ["Tool results:"]

    for name, result in results:
        lines.append(f"\n[{name}]")
        if isinstance(result, dict):
            for key, value in result.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append(f"  {result}")

    return "\n".join(lines)
