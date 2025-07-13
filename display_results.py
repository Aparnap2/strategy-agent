import json
from datetime import datetime
from typing import Dict, Any

def format_date(date_str: str) -> str:
    """Format ISO date string to a more readable format."""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except (ValueError, AttributeError):
        return date_str

def display_project_plan(plan: list) -> str:
    """Format project plan as markdown."""
    if not plan:
        return "No project plan available.\n"
    
    output = ["## Project Plan\n"]
    
    # Gantt chart section
    output.append("### Gantt Chart\n")
    output.append("```mermaid")
    output.append("gantt")
    output.append("    title Project Timeline")
    output.append("    dateFormat  YYYY-MM-DD")
    output.append("    axisFormat %m-%d")
    output.append("    ")
    
    for task in plan:
        task_id = task.get('id', 'T')
        desc = task.get('description', 'Unnamed Task')
        start = task.get('start_date', '').split('T')[0]
        duration = task.get('duration', 1)
        output.append(f"    section {task_id}")
        output.append(f"    {desc} :{task_id}, {start}, {duration}d")
    
    output.append("```\n")
    
    # Task list
    output.append("### Task Details\n")
    output.append("| ID | Description | Start Date | End Date | Duration | Dependencies |")
    output.append("|----|-------------|------------|----------|----------|--------------|")
    
    for task in plan:
        task_id = task.get('id', '')
        desc = task.get('description', '')
        start = format_date(task.get('start_date', ''))
        end = format_date(task.get('end_date', ''))
        duration = f"{task.get('duration', 0)} days"
        deps = ", ".join(task.get('dependencies', [])) or 'None'
        output.append(f"| {task_id} | {desc} | {start} | {end} | {duration} | {deps} |")
    
    return "\n".join(output) + "\n"

def display_technical_architecture(arch: Dict[str, Any]) -> str:
    """Format technical architecture as markdown."""
    if not arch:
        return "No technical architecture available.\n"
    
    output = ["## Technical Architecture\n"]
    
    # Technology Stack
    if 'technology_stack' in arch:
        output.append("### Technology Stack\n")
        for category, items in arch['technology_stack'].items():
            output.append(f"#### {category.title()}")
            for item in items:
                name = item.get('name', 'Unknown')
                version = item.get('version', 'N/A')
                justification = item.get('justification', '')
                output.append(f"- **{name}** (v{version}): {justification}")
                if 'alternatives' in item:
                    output.append(f"  - *Alternatives*: {item['alternatives']}")
            output.append("")
    
    # System Architecture Diagram
    if 'system_architecture' in arch and 'diagram' in arch['system_architecture']:
        output.append("### System Architecture\n")
        output.append("```mermaid")
        output.append(arch['system_architecture']['diagram'])
        output.append("```\n")
    
    return "\n".join(output)

def display_client_feedback(feedback: Dict[str, Any]) -> str:
    """Format client feedback as markdown."""
    if not feedback:
        return "No client feedback available.\n"
    
    output = ["## Client Feedback\n"]
    consolidated = feedback.get('consolidated_feedback', {})
    all_feedback = consolidated.get('all_feedback', {})
    
    # Consolidated Feedback
    if consolidated:
        output.append("### Consolidated Feedback\n")
        if 'summary' in consolidated:
            output.append(f"**Summary**: {consolidated['summary']}")
        if 'critical_issues' in consolidated and consolidated['critical_issues']:
            output.append("\n**Critical Issues**:")
            for issue in consolidated['critical_issues']:
                output.append(f"- {issue}")
        output.append("")
    
    # Individual Persona Feedback
    for persona, data in all_feedback.items():
        if not data:
            continue
        output.append(f"### {persona.replace('_', ' ').title()} Feedback\n")
        if 'feedback_summary' in data:
            output.append(f"**Summary**: {data['feedback_summary']}")
        if 'strengths' in data and data['strengths']:
            output.append("\n**Strengths**:")
            for strength in data['strengths']:
                output.append(f"- {strength}")
        if 'suggestions' in data and data['suggestions']:
            output.append("\n**Suggestions**:")
            for suggestion in data['suggestions']:
                output.append(f"- {suggestion}")
        output.append("")
    
    return "\n".join(output)

def display_results(data: Dict[str, Any]) -> str:
    """Display all results in a formatted way."""
    if not data or 'result' not in data:
        return "No valid results to display."
    
    result = data['result']
    if not isinstance(result, dict) or 'result' not in result:
        return "Invalid result format."
    
    result_data = result['result']
    output = []
    
    # Project Plan
    if 'project_plan' in result_data and result_data['project_plan']:
        output.append(display_project_plan(result_data['project_plan']))
    
    # Technical Architecture
    if 'technical_architecture' in result_data and result_data['technical_architecture']:
        output.append(display_technical_architecture(result_data['technical_architecture']))
    
    # Client Feedback
    if 'client_feedbacks' in result_data and result_data['client_feedbacks']:
        output.append(display_client_feedback({
            'consolidated_feedback': result_data.get('consolidated_feedback', {}),
            'all_feedback': result_data['client_feedbacks']
        }))
    
    return "\n---\n".join(output)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], 'r') as f:
                data = json.load(f)
            print(display_results(data))
        except Exception as e:
            print(f"Error loading or processing file: {e}")
    else:
        print("Usage: python display_results.py <path_to_json_file>")
        print("Please provide the path to a JSON file containing the results.")
