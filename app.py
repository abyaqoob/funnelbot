"""Hugging Face Spaces Gradio entrypoint serving FunnelBot FastAPI application."""
import os
import uvicorn

try:
    import gradio as gr
    from app.main import app

    # Mount Gradio onto the existing FastAPI application
    app = gr.mount_gradio_app(app, gr.Blocks(title="FunnelBot"), path="/_gradio")
except Exception:
    from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
