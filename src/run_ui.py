import gradio as gr
from src.generate_terraform import generate_terraform_infrastructure

def run_terraform(source_dir, dest_dir):
    try:
        generate_terraform_infrastructure(source_dir, dest_dir)
        return "Terraform generation completed successfully!"
    except Exception as e:
        return f"Error: {str(e)}"

# Create the Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# Infrastructure to Terraform code generator")

    with gr.Row():
        source_dir = gr.Textbox(
            label="Source Repository Directory",
            placeholder="Enter the source repository directory path"
        )
        dest_dir = gr.Textbox(
            label="Destination Repository Directory",
            placeholder="Enter the destination repository directory path"
        )

    generate_button = gr.Button("Generate Terraform scripts")
    output = gr.Textbox(label="Output", lines=10, interactive=False)

    generate_button.click(run_terraform, inputs=[source_dir, dest_dir], outputs=output)

# Launch the Gradio app
if __name__ == "__main__":
    demo.launch()