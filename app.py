from flask import Flask, request, render_template, send_file
import matplotlib
matplotlib.use('Agg')  # Use the 'Agg' backend
import matplotlib.pyplot as plt
from matplotlib import font_manager
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import numpy as np
import os
from io import BytesIO

app = Flask(__name__)

# Define the upload folder
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Path to the static base image
BASE_IMAGE_PATH = os.path.join('static', 'base_image.jpg')

def add_arabic_text_to_image(ax, text, x, y, font_path, font_size, text_color, letter_spacing=None, alpha=1.0, noise=False):
    """
    Adds Arabic text to an image at specified coordinates with optional letter spacing and noise effect.
    """
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    font_prop = font_manager.FontProperties(fname=font_path, size=font_size)

    if noise:
        for _ in range(10):
            noise_alpha = alpha * np.random.uniform(0.3, 0.6)
            noise_x_offset = x + np.random.uniform(-1, 1)
            noise_y_offset = y + np.random.uniform(-1, 1)
            ax.text(
                x=noise_x_offset, y=noise_y_offset, s=bidi_text,
                fontproperties=font_prop, color=text_color,
                alpha=noise_alpha, zorder=-1,
            )

    if letter_spacing is not None:
        x_offset = x
        for char in bidi_text:
            ax.text(
                x=x_offset, y=y, s=char,
                fontproperties=font_prop, color=text_color,
                alpha=alpha,
            )
            x_offset += letter_spacing
    else:
        ax.text(
            x=x, y=y, s=bidi_text,
            fontproperties=font_prop, color=text_color,
            alpha=alpha,
        )

    return ax

def overlay_image(base_image, overlay_image_path, position, size):
    """
    Overlays an image on top of the base image at the specified position and size.
    """
    overlay_image = Image.open(overlay_image_path).convert("RGBA")
    overlay_image = overlay_image.resize(size)
    base_image = base_image.copy().convert("RGBA")
    base_image.paste(overlay_image, position, overlay_image)
    return base_image

def add_scanned_effects(image):
    """
    Adds scanned effects like ink splashes, dirt, and paper texture to the image while keeping it colorful.
    """
    # Add paper texture (ensure the texture is in color)
    paper_texture = Image.open("static/paper_texture.jpg").convert("RGB")  # Load a paper texture image in color
    paper_texture = paper_texture.resize(image.size)
    image = Image.blend(image.convert("RGB"), paper_texture, alpha=0.03)  # Blend the texture with the image

    # Add a slight blur to simulate scanning imperfections
    image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

    # Adjust brightness and contrast
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(0.9)  # Reduce brightness slightly
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.4)  # Increase contrast slightly

    return image

def generate_image(base_image_path, stamp_image_path, front_id_path, back_id_path, customer_name, central_name, date, phone_number):
    """
    Generates the final image with overlays and text.
    """
    base_image = Image.open(base_image_path).convert("RGBA")

    # Overlay stamp image
    base_image = overlay_image(base_image, stamp_image_path, (1900, 2100), (600, 290))

    # Overlay front ID image
    base_image = overlay_image(base_image, front_id_path, (250, 2500), (1000, 700))

    # Overlay back ID image
    base_image = overlay_image(base_image, back_id_path, (1400, 2500), (1000, 700))

    # Format the date: single-digit month and two spaces between day, month, and year
    # Example: 20-01-2025 -> 20  1  2025
    day, month, year = date.split("-")
    formatted_date = f"{day}    {int(month)}    {year}"  # Convert month to int to remove leading zero

    # Define text elements
    text_elements = [
        {"text": formatted_date, "x": 1960, "y": 900, "font_path": "fonts/Molhim.ttf", "font_size": 7, "text_color": "#140a72", "alpha": 1, "noise": False},
        {"text": customer_name, "x": 1430, "y": 1360, "font_path": "fonts/Dima Font.ttf", "font_size": 7.5, "text_color": "#140a72", "alpha": 1, "noise": False},
        {"text": central_name, "x": 1670, "y": 1500, "font_path": "fonts/Dima Font.ttf", "font_size": 7, "text_color": "#140a72", "alpha": 1, "noise": False},
        {"text": phone_number, "x": 300, "y": 1360, "font_path": "fonts/Molhim.ttf", "font_size": 8.5, "text_color": "#140a72", "alpha": 1, "noise": False},
        {"text": phone_number, "x": 1020, "y": 2160, "font_path": "fonts/Molhim.ttf", "font_size": 10, "text_color": "#140a72", "alpha": 1, "noise": False},
        {"text": customer_name, "x": 170, "y": 2180, "font_path": "fonts/manual.otf", "font_size": 6, "text_color": "#140a72", "alpha": 1, "noise": False},
    ]

    # Create a figure and axis
    fig, ax = plt.subplots()
    ax.imshow(base_image)

    # Add all text elements to the image
    for element in text_elements:
        ax = add_arabic_text_to_image(ax, **element)

    # Hide axes
    ax.axis("off")

    # Save the image to a BytesIO object
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='jpg', bbox_inches="tight", pad_inches=0, dpi=300)
    img_buffer.seek(0)
    plt.close('all')  # Close all figures to free up memory

    # Convert the BytesIO object to a PIL image
    final_image = Image.open(img_buffer)

    # Add scanned effects
    final_image = add_scanned_effects(final_image)

    # Save the final image to a new BytesIO object
    final_buffer = BytesIO()
    final_image.save(final_buffer, format='JPEG')
    final_buffer.seek(0)

    return final_buffer

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # Get form data
            stamp_image = request.files['stamp_image']
            front_id = request.files['front_id']
            back_id = request.files['back_id']
            customer_name = request.form['customer_name']
            central_name = request.form['central_name']
            date = request.form['date']
            phone_number = request.form['phone_number']

            # Validate required fields
            if not all([stamp_image, front_id, back_id, customer_name, central_name, date, phone_number]):
                return "All fields are required!", 400

            # Save uploaded files
            stamp_image_path = os.path.join(app.config['UPLOAD_FOLDER'], stamp_image.filename)
            front_id_path = os.path.join(app.config['UPLOAD_FOLDER'], front_id.filename)
            back_id_path = os.path.join(app.config['UPLOAD_FOLDER'], back_id.filename)

            stamp_image.save(stamp_image_path)
            front_id.save(front_id_path)
            back_id.save(back_id_path)

            # Generate the final image using the static base image
            img_buffer = generate_image(BASE_IMAGE_PATH, stamp_image_path, front_id_path, back_id_path, customer_name, central_name, date, phone_number)

            # Save the generated image
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'result.jpg')
            with open(output_path, 'wb') as f:
                f.write(img_buffer.getvalue())

            return render_template('index.html', image_generated=True, image_path='uploads/result.jpg')

        except Exception as e:
            return f"An error occurred: {str(e)}", 500

    return render_template('index.html', image_generated=False)

@app.route('/download/<filename>')
def download(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)  # Disable Flask auto-reloader