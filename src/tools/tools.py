import base64
import mimetypes
import os
from pathlib import Path
from typing import Optional, Callable, Annotated

from agentic_framework.settings import settings

def read_folder_structure_tool(
        work_dir: Optional[str | Path],
) -> Callable[[str], str]:

    work_dir = str(work_dir) if work_dir else settings.WORK_DIR

    def read_folder_structure(path: str) -> str:
        path = os.path.normpath(path)
        tree_structure = ""
        if work_dir and not path.startswith(work_dir):
            path = os.path.join(work_dir, path)

        def build_tree(dir_path: str, prefix: str = "") -> str:
            entries = sorted(os.listdir(dir_path))
            tree = ""
            for index, entry in enumerate(entries):
                entry_path = os.path.join(dir_path, entry)
                connector = "└── " if index == len(entries) - 1 else "├── "
                tree += f"{prefix}{connector}{entry}/\n" if os.path.isdir(entry_path) else f"{prefix}{connector}{entry}\n"
                if os.path.isdir(entry_path):
                    new_prefix = f"{prefix}    " if index == len(entries) - 1 else f"{prefix}│   "
                    tree += build_tree(entry_path, new_prefix)
            return tree

        tree_structure = f"{os.path.basename(path)}/\n" + build_tree(path)
        return tree_structure

    return read_folder_structure

# def get_file_content_tool(
#         work_dir: Optional[str | Path],
# ) -> Callable[[str], str]:
#
#     work_dir = str(work_dir) if work_dir else settings.WORK_DIR
#
#     def get_file_content(file_path: Annotated[str, "file_path"]) -> list[dict[str, str | dict[str, str]]] | str:
#
#         file_path = os.path.normpath(file_path)
#         if work_dir and not file_path.startswith(work_dir):
#             file_path = os.path.join(work_dir, file_path)
#
#         if not os.path.isfile(file_path):
#             raise FileNotFoundError(f"The file '{file_path}' does not exist.")
#
#         # Check if the file is an image
#         mime_type, _ = mimetypes.guess_type(file_path)
#         if mime_type and mime_type.startswith("image"):
#             # Read and encode the image file as base64
#             with open(file_path, "rb") as image_file:
#                 base64_image = base64.b64encode(image_file.read()).decode("utf-8")
#             return [
#                 {
#                     "type": "image_url",
#                     "image_url": {
#                         "url": f"data:{mime_type};base64,{base64_image}",
#                         "detail": "auto"
#                     }
#                 }
#             ]
#         else:
#             # Handle non-image files
#             with open(file_path, "r", encoding="utf-8") as file:
#                 return [{"type": "text", "content": file.read()}]
#
#     # Return the function to be used as a tool
#
#     return get_file_content


def get_image_file_content_tool(
        work_dir: Optional[str | Path],
) -> Callable[[str], dict[str, str]]:
    """
    Tool to get the image content as a dictionary containing the image URL.
    """
    work_dir = str(work_dir) if work_dir else settings.WORK_DIR

    def get_image_file_content(file_path: Annotated[str, "file_path"]) -> dict[str, str]:
        file_path = os.path.normpath(file_path)
        if work_dir and not file_path.startswith(work_dir):
            file_path = os.path.join(work_dir, file_path)

        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"The file '{file_path}' does not exist.")

        # Check if the file is an image
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith("image"):
            # Read and encode the image file as base64
            with open(file_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            return {
                "url": f"data:{mime_type};base64,{base64_image}",
                "detail": "auto"
            }
        else:
            raise ValueError(f"The file '{file_path}' is not a valid image.")

    return get_image_file_content



