# ==============================================================================
#           APP.PY - FINAL VERSION (Erase Tool Implemented)
# ==============================================================================

import streamlit as st
import os
from dotenv import load_dotenv
import io
import requests
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Service function imports
from services import (
    enhance_prompt,
    generate_hd_image,
    create_packshot,
    add_shadow,
    lifestyle_shot_by_text,
    generative_fill
)

# --- App Configuration ---
st.set_page_config(
    page_title="Artifex Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Environment Variable Loading ---
load_dotenv()

# --- Helper Functions ---
def download_image(url):
    """Download image from URL and return as bytes."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.error(f"Error downloading image: {str(e)}")
        return None

# --- State Initialization ---
def initialize_session_state():
    """Initialize all session state variables."""
    states = {
        'api_key': os.getenv('BRIA_API_KEY'),
        'start_choice': None,
        'generated_image_urls': [],
        'prompt': "",
        'enhanced_prompt': "",
        'uploaded_image_data': None,
        'editing_hub_choice': None,
        'packshot_url': None,
        'shadow_url': None,
        'lifestyle_url': None,
        'erase_url': None,
        'lifestyle_prompt': "",
        'enhanced_lifestyle_prompt': ""
    }
    for key, value in states.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_all_state():
    """Resets all session state variables to their defaults, keeping the API key."""
    api_key = st.session_state.get('api_key')
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session_state()
    if api_key:
        st.session_state.api_key = api_key


# --- UI Rendering Functions for Each Page ---

def render_homepage():
    st.title("Artifex Studio")
    st.header("How would you like to start?")
    st.markdown("Create a visual from scratch using AI, or work with an image you already have.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎨 Generate a New Image from an Idea", use_container_width=True, type="primary"):
            st.session_state.start_choice = 'generate'
            st.rerun()
    with col2:
        if st.button("🖼️ Upload an Existing Image", use_container_width=True):
            st.session_state.start_choice = 'upload'
            st.rerun()

def render_generate_page():
    st.header("🎨 Generate a New Image")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.session_state.prompt = st.text_area("Enter your prompt", value=st.session_state.prompt, height=100)
        if st.button("✨ Enhance Prompt"):
            if st.session_state.prompt:
                with st.spinner("Enhancing prompt..."):
                    st.session_state.enhanced_prompt = enhance_prompt(st.session_state.api_key, st.session_state.prompt)
            else: st.warning("Please enter a prompt to enhance.")
        if st.session_state.enhanced_prompt:
            st.markdown(f"**Enhanced Prompt:** *{st.session_state.enhanced_prompt}*")
    with col2:
        num_images = st.slider("Number of images", 1, 4, 1)
        aspect_ratio = st.selectbox("Aspect ratio", ["1:1", "16:9", "9:16", "4:3", "3:4"])
    if st.button("Generate Image", type="primary"):
        prompt_to_use = st.session_state.enhanced_prompt or st.session_state.prompt
        if prompt_to_use:
            with st.spinner("🎨 Generating your masterpiece..."):
                result = generate_hd_image(prompt=prompt_to_use, api_key=st.session_state.api_key, num_results=num_images, aspect_ratio=aspect_ratio)
                if result and result.get("result"):
                    urls = [item["urls"][0] for item in result["result"] if item.get("urls")]
                    st.session_state.generated_image_urls = urls
                else: st.error("Image generation failed to return URLs.")
        else: st.warning("Please enter a prompt.")
    if st.session_state.generated_image_urls:
        st.subheader("Your Generated Images")
        cols = st.columns(len(st.session_state.generated_image_urls))
        for idx, url in enumerate(st.session_state.generated_image_urls):
            with cols[idx]:
                st.image(url, use_column_width=True)
                if st.button("➡️ Send to Editor", key=f"edit_{idx}", use_container_width=True):
                    with st.spinner("Preparing image for editor..."):
                        image_data = download_image(url)
                        if image_data:
                            st.session_state.uploaded_image_data = image_data
                            st.session_state.start_choice = 'upload'
                            st.rerun()
    st.markdown("---")
    if st.button("← Back to Start"):
        reset_all_state()
        st.rerun()

def render_packshot_tool():
    st.subheader("Tool: Create Professional Packshot")
    if st.session_state.shadow_url:
        st.image(st.session_state.shadow_url, caption="Final Result with Shadow")
    elif st.session_state.packshot_url:
        st.image(st.session_state.packshot_url, caption="Packshot Result")
    if not st.session_state.shadow_url:
        if not st.session_state.packshot_url:
            bg_color = st.color_picker("Background color:", "#FFFFFF")
            if st.button("Generate Packshot", type="primary"):
                with st.spinner("Creating packshot..."):
                    result = create_packshot(api_key=st.session_state.api_key, image_data=st.session_state.uploaded_image_data, background_color=bg_color)
                    if result and result.get("result_url"):
                        st.session_state.packshot_url = result["result_url"]
                        st.rerun()
                    else: st.error("Packshot creation failed.")
        else:
            st.markdown("---")
            if st.button("Add Realistic Shadow", type="primary"):
                with st.spinner("Adding shadow..."):
                    result = add_shadow(api_key=st.session_state.api_key, image_url=st.session_state.packshot_url)
                    if result and result.get("result_url"):
                        st.session_state.shadow_url = result["result_url"]
                        st.rerun()
                    else: st.error("Shadow creation failed.")
    st.markdown("---")
    if st.button("↩️ Back to Editing Hub"):
        st.session_state.editing_hub_choice = None
        st.session_state.packshot_url = None
        st.session_state.shadow_url = None
        st.rerun()

def render_lifestyle_tool():
    """Renders the UI for the Lifestyle Shot tool with robust parsing."""
    st.subheader("Tool: Place in a Lifestyle Scene")
    
    st.session_state.lifestyle_prompt = st.text_area("Describe the scene you want to create:", value=st.session_state.lifestyle_prompt)

    if st.button("✨ Enhance Prompt"):
        if st.session_state.lifestyle_prompt:
            with st.spinner("Enhancing prompt..."):
                st.session_state.enhanced_lifestyle_prompt = enhance_prompt(st.session_state.api_key, st.session_state.lifestyle_prompt)
        else:
            st.warning("Please enter a scene description to enhance.")
    
    if st.session_state.enhanced_lifestyle_prompt:
        st.markdown(f"**Enhanced Prompt:** *{st.session_state.enhanced_lifestyle_prompt}*")

    if st.button("Generate Scene", type="primary"):
        prompt_to_use = st.session_state.enhanced_lifestyle_prompt or st.session_state.lifestyle_prompt
        if prompt_to_use:
            with st.spinner("Generating lifestyle scene..."):
                try:
                    result = lifestyle_shot_by_text(
                        api_key=st.session_state.api_key,
                        image_data=st.session_state.uploaded_image_data,
                        scene_description=prompt_to_use,
                        sync=True,
                        num_results=1
                    )
                    
                    # Final robust parsing logic
                    lifestyle_url = None
                    if result and result.get("result"):
                        try:
                            # The first item in result["result"] is a list, and the first element is the URL
                            lifestyle_url = result["result"][0][0]
                        except (KeyError, IndexError, TypeError):
                            lifestyle_url = None
                    
                    if lifestyle_url:
                        st.session_state.lifestyle_url = lifestyle_url
                    else:
                        st.error("The API did not return a URL in a format the app could understand.")
                        st.subheader("Full API Response:")
                        st.json(result)

                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.warning("Please describe the scene.")

    if st.session_state.lifestyle_url:
        st.success("Lifestyle scene generated successfully!")
        st.image(st.session_state.lifestyle_url, caption="Lifestyle Scene Result")

    if st.button("↩️ Back to Editing Hub"):
        st.session_state.editing_hub_choice = None
        st.session_state.lifestyle_url = None
        st.session_state.lifestyle_prompt = ""
        st.session_state.enhanced_lifestyle_prompt = ""
        st.rerun()

def render_erase_tool():
    """Renders the UI for the Erase tool."""
    st.subheader("Tool: Erase an Element")
    
    # Show the result if it exists
    if st.session_state.erase_url:
        st.success("Object erased successfully!")
        st.image(st.session_state.erase_url, caption="Erased Result")
    # Otherwise, show the canvas and controls
    else:
        st.markdown("Draw a mask over the object you want to remove.")
        image_pil = Image.open(io.BytesIO(st.session_state.uploaded_image_data))
        
        canvas_result = st_canvas(
            fill_color="rgba(255, 100, 100, 0.5)",
            stroke_width=20,
            background_image=image_pil,
            height=image_pil.height,
            width=image_pil.width,
            drawing_mode="freedraw",
            key="canvas",
        )

        if st.button("Erase Selected Area", type="primary"):
            if canvas_result.image_data is not None:
                # Convert the canvas drawing to a mask file
                mask_pil = Image.fromarray(canvas_result.image_data).split()[3]
                mask_bytes = io.BytesIO()
                mask_pil.save(mask_bytes, format="PNG")
                mask_bytes.seek(0)

                with st.spinner("Erasing..."):
                    try:
                        # We use generative_fill with an empty prompt to "erase"
                        result = generative_fill(
                            api_key=st.session_state.api_key,
                            image_data=st.session_state.uploaded_image_data,
                            mask_data=mask_bytes.getvalue(),
                            prompt="",
                            sync=True
                        )
                        if result and result.get("result_url"):
                            st.session_state.erase_url = result["result_url"]
                            st.rerun()
                        elif result and result.get("urls"):
                            st.session_state.erase_url = result["urls"][0]
                            st.rerun()
                        else:
                            st.error("Erase operation failed. The API did not return a valid URL.")
                            st.json(result)
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
            else:
                st.warning("Please draw on the image to select an area.")

    if st.button("↩️ Back to Editing Hub"):
        st.session_state.editing_hub_choice = None
        st.session_state.erase_url = None
        st.rerun()


def render_upload_page():
    st.header("🖼️ Edit an Existing Image")
    if st.session_state.uploaded_image_data is None:
        uploaded_file = st.file_uploader("Choose a file", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        if uploaded_file:
            st.session_state.uploaded_image_data = uploaded_file.getvalue()
            st.rerun()
    else:
        if st.session_state.editing_hub_choice is None:
            st.image(st.session_state.uploaded_image_data, caption="Your Image", width=400)
            st.markdown("---")
            st.subheader("What would you like to do?")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Create Professional Packshot", use_container_width=True):
                    st.session_state.editing_hub_choice = 'packshot'
                    st.rerun()
            with col2:
                if st.button("Place in a Lifestyle Scene", use_container_width=True):
                    st.session_state.editing_hub_choice = 'lifestyle'
                    st.rerun()
            with col3:
                if st.button("Erase an Element", use_container_width=True):
                    st.session_state.editing_hub_choice = 'erase'
                    st.rerun()
        elif st.session_state.editing_hub_choice == 'packshot':
            render_packshot_tool()
        elif st.session_state.editing_hub_choice == 'lifestyle':
            render_lifestyle_tool()
        elif st.session_state.editing_hub_choice == 'erase':
            render_erase_tool()
    st.markdown("---")
    if st.button("← Back to Start"):
        reset_all_state()
        st.rerun()

# --- Main App Router ---
def main():
    """Main function to route the user through the app."""
    initialize_session_state()
    with st.sidebar:
        st.header("Settings")
        st.session_state.api_key = st.text_input("Enter your API key:", value=st.session_state.api_key or "", type="password")
    if st.session_state.start_choice is None:
        render_homepage()
    elif st.session_state.start_choice == 'generate':
        render_generate_page()
    elif st.session_state.start_choice == 'upload':
        render_upload_page()

if __name__ == "__main__":
    main()