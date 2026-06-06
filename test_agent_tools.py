
from core.agent import AutomyxAgent
from tools.three_d_tools import ThreeDTools
from tools.video_tools import VideoTools
from tools.pc_tools import PCTools
import json
import os

print("=== TESTING AGENT TOOLS ===")

# 1. Initialize agent
agent = AutomyxAgent(model_name="nvidia/gpt-oss-120b")

# 2. Register the key tools
agent.register_tool("generate_professional_3d_video", ThreeDTools.generate_professional_3d_video)
agent.register_tool("professional_color_grading", VideoTools.professional_color_grading)
agent.register_tool("advanced_transition", VideoTools.advanced_transition)
agent.register_tool("professional_audio_mastering", VideoTools.professional_audio_mastering)
agent.register_tool("generate_cinematic_environment", ThreeDTools.generate_cinematic_environment)

print("✅ All key tools registered!")

# 3. Check the system prompt to verify tools are listed
print("\n=== CHECKING SYSTEM PROMPT ===")
print("System prompt exists:", hasattr(agent, 'system_prompt'))
print("'generate_professional_3d_video' in system prompt:", 'generate_professional_3d_video' in agent.system_prompt)
print("'professional_color_grading' in system prompt:", 'professional_color_grading' in agent.system_prompt)

# 4. Test parsing a test JSON
print("\n=== TESTING TOOL PARSING ===")
test_message = '''
Okay, let's create that video!
```json
{
  "action": "generate_professional_3d_video",
  "args": {
    "scene_description": "Un niño nadando a una isla con dos lobos",
    "output_path": "C:\\\\Users\\\\COMPUMAX\\\\Downloads\\\\test_video.mp4"
  }
}
'''
tool_calls = agent._parse_tool_calls(test_message)
print("Tool calls parsed successfully:", len(tool_calls) > 0)
if tool_calls:
    print("First call action:", tool_calls[0].get('action'))
    print("Args output_path:", tool_calls[0].get('args', {}).get('output_path'))

print("\n=== TEST DONE ===")
