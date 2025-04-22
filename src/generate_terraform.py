import os
from pathlib import Path
from typing import Any, Dict, Union, Optional

from agentic_framework.core.agents import BaseSDLCAgent
from agentic_framework.core.configs.llm import set_config, get_config
from agentic_framework.core.executors import LocalCommandLineCodeExecutor
from agentic_framework.core.orchestration import WorkflowOrchestrator
from agentic_framework.core.schemas.schemas import TransitionElement
from agentic_framework.core.tools import (
    get_file_content_tool,
    write_file_content_tool
)
from autogen import OpenAIWrapper
from dotenv import load_dotenv

from src.constants.constants import (
    REQ_ANALYZER_SYSTEM_MESSAGE,
    SCRIPT_GENERATOR_SYSTEM_MESSAGE,
    TOOL_EXECUTOR_SYSTEM_MESSAGE
)
from src.tools.tools import get_image_file_content_tool, read_folder_structure_tool

load_dotenv()
# Configure project and model
src_dir = "/Users/vfedoriv/workspace/product-x/JavaPetClinic"
work_dir_path = Path(src_dir)

set_config([{
    "model": os.getenv("MODEL_NAME"),
    "base_url": os.getenv("OPENAI_API_BASE"),
    "temperature": 0.0,
    "max_tokens": 16000,
}])

# set_config([{
#     "model": os.getenv("LLAMA_MODEL_NAME"),
#     "base_url": os.getenv("LLAMA_API_BASE"),
#     "api_key": "ollama",
#     "temperature": 0.0,
#     "max_tokens": 16000,
# }])

llm_config = get_config()

llm_wrapper = OpenAIWrapper(**get_config())

# Create agents
init_agent = BaseSDLCAgent(
    name="InitAgent"
)

analyzer_agent = BaseSDLCAgent(
    name="RequirementsAnalyzer",
    llm_config=llm_config,
    system_message=REQ_ANALYZER_SYSTEM_MESSAGE,
    human_input_mode="NEVER",
)

generator_agent = BaseSDLCAgent(
    name="ScriptGenerator",
    llm_config=llm_config,
    system_message=SCRIPT_GENERATOR_SYSTEM_MESSAGE,
    human_input_mode="NEVER",
)

tool_executor_agent = BaseSDLCAgent(
    name="ToolExecutor",
    llm_config=get_config(),
    system_message=TOOL_EXECUTOR_SYSTEM_MESSAGE,
    human_input_mode="NEVER",
)


code_executor_agent = BaseSDLCAgent(
    name="TerraformScriptExecutor",
    human_input_mode="NEVER",
    system_message="You are terraform scripts executor. You can be used to deploy infrastructure on the cloud. You can execute terraform commands.",
    code_execution_config={
        "executor": LocalCommandLineCodeExecutor(
            work_dir=work_dir_path,
            timeout=120,
        )
    }
)


# Register tools
def register_tools(work_dir):
    read_folder_structure = read_folder_structure_tool(work_dir)
    get_file_content = get_file_content_tool(work_dir)
    write_file_content = write_file_content_tool(work_dir)

    print(f"Creating tools with work_dir: {work_dir}")

    # Register common tools for both analyzer and generator
    for agent in [analyzer_agent, generator_agent]:
        agent.register_for_llm(
            name="read_folder_structure",
            description="Reads and returns the folder structure from a given root folder.",
        )(read_folder_structure)

        agent.register_for_llm(
            name="get_file_content",
            description="Reads and returns file content by the given filepath.",
        )(get_file_content)

        agent.register_for_llm(
            name="write_file_content",
            description="write content in file in the given filepath.",
        )(write_file_content)

    print("Registering tool executor functions...")

    # Register the same tools for execution by the ToolExecutor
    tool_executor_agent.register_for_execution(
        name="read_folder_structure")(read_folder_structure)
    tool_executor_agent.register_for_execution(
        name="get_file_content")(get_file_content)
    tool_executor_agent.register_for_execution(
        name="write_file_content")(write_file_content)


    # Update in register_tools function:
    tool_executor_agent.register_for_execution(
        name="extract_infrastructure_from_image"
    )(lambda image_path, **kwargs: extract_infrastructure_from_image(
        image_path=image_path,
        work_dir=work_dir,
        llm_client=llm_wrapper,
        **kwargs
    ))

    # Register image recognition for analyzer
    analyzer_agent.register_for_llm(
        name="extract_infrastructure_from_image",
        description="Extract infrastructure from image/diagram file.",
    )(extract_infrastructure_from_image)

    print(f"All tools registered successfully")


def extract_infrastructure_from_image(
        image_path: str,
        llm_client: Any = None,
        work_dir: Optional[str | Path] = None,
        text_content: Optional[str] = None
) -> Dict[str, Union[str, Any]]:
    """
    Send a multimodal message to the LLM to recognize/describe the image.
    """
    try:
        # Import OpenAIWrapper at the top level
        from autogen import OpenAIWrapper

        # If llm_client is not provided, create one using OpenAIWrapper
        if llm_client is None:
            config = get_config()
            llm_client = OpenAIWrapper(**config)

        # Get the image content using the tool
        get_image_file_content = get_image_file_content_tool(work_dir)
        image_url = get_image_file_content(image_path)

        # Prepare content for the request
        content = [
            {
                "type": "image_url",
                "image_url": image_url
            }
        ]

        if text_content:
            content.insert(0, {"type": "text", "text": text_content})
        else:
            content.insert(0, {
                "type": "text",
                "text": "Please describe the image. At first, assume it is a diagram of cloud infrastructure. If it is not, please return text 'it's not a infrastructure related image/diagram`."
            })

        messages = [
            {"role": "system", "content": "You are an AI that recognizes and describes images/diagrams."},
            {"role": "user", "content": content}
        ]

        # For OpenAIWrapper from autogen
        response = llm_client.create(messages=messages)
        # Extract the content from OpenAIWrapper response
        choices = OpenAIWrapper.extract_text_or_completion_object(response)
        if choices and len(choices) > 0:
            return {"content": choices[0]}

        return {"status": "error", "message": "Failed to get response from LLM"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Main execution function
def generate_terraform_infrastructure(project_path, message=None):
    """
    Analyze project and generate Terraform infrastructure

    Args:
        project_path: Path to the project directory
        message: Optional custom message with requirements
    """
    # Add debug tracing
    print("Setting up workspace for project path:", project_path)

    # Register tools for agents
    register_tools(project_path)
    print("Tools registered successfully")

    # Define transitions
    edges = [
        TransitionElement(
            agent=init_agent,
            next_agent=analyzer_agent
        ),
        TransitionElement(
            agent=analyzer_agent,
            next_agent=tool_executor_agent,
            condition=lambda msg: ("NEED_TOOL" in str(msg) or msg.get("tool_calls"))
        ),
        TransitionElement(
            agent=tool_executor_agent,
            next_agent=analyzer_agent,
            condition=lambda msg: ("TOOL_RESULT" in str(msg) or msg.get("tool_responses"))
        ),
        TransitionElement(
            agent=analyzer_agent,
            next_agent=generator_agent,
            condition=lambda msg: "ANALYSIS_COMPLETE" in str(msg)
        ),
        TransitionElement(
            agent=generator_agent,
            next_agent=tool_executor_agent,
            condition=lambda msg: ("NEED_TOOL" in str(msg) or msg.get("tool_calls"))
        ),
        TransitionElement(
            agent=tool_executor_agent,
            next_agent=generator_agent,
            condition=lambda msg: "TOOL_RESULT" in str(msg)
        ),
        TransitionElement(
            agent=generator_agent,
            next_agent=code_executor_agent,
            condition=lambda msg: "SCRIPTS_GENERATED" in str(msg)
        ),
        TransitionElement(
            agent=code_executor_agent,
            next_agent=generator_agent,
            condition=lambda msg: "EXECUTION_ERROR" in str(msg),
            max_rounds=3
        )
    ]

    workflow = WorkflowOrchestrator(edges)

    # Default message if none provided
    if not message:
        message = f"I want to recognize cloud infrastructure for the project and create Terraform scripts/modules to implement it. Project folder: {project_path}"

    result = workflow.run_core(message=message, llm_config=llm_config, max_round=100)

    return result


# Run the generator when executed directly
if __name__ == "__main__":
    src_dir = "/Users/vfedoriv/workspace/product-x/JavaPetClinic"
    result = generate_terraform_infrastructure(src_dir)
    print("Terraform generation complete!")
    print(f"Generated files in: {src_dir}")
