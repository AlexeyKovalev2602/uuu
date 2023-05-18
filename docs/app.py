import base64
import os

import matplotlib.pyplot as plt
import numpy as np
import requests
from PIL import Image
from flask import Flask, render_template, request, abort, send_from_directory

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024  # 1 MB limit for uploaded files
UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
RECAPTCHA_SITE_KEY = '6LcWUB0mAAAAAF0-OqdZc2KBcykLOsH6rvf6jC6o'


@app.route('/mywork', methods=['POST'])
def transform():
    file = request.files.get('file')
    function_type = request.form.get('function_type')
    period = float(request.form.get('period'))

    if not file:
        abort(400, 'No file was uploaded')
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        abort(400, 'File is not an image')

    recaptcha_response = request.form.get('g-recaptcha-response')
    if not recaptcha_response:
        abort(400, 'reCAPTCHA verification failed')
    payload = {
        'secret': '6LcWUB0mAAAAAFZTGUKnRsqdPQ81UL5ll02yiZxf',
        'response': recaptcha_response
    }
    response = requests.post('https://www.google.com/recaptcha/api/siteverify', payload).json()
    if not response['success']:
        abort(400, 'reCAPTCHA verification failed')

    img = Image.open(file)
    img_array = np.array(img)
    normalized_array = img_array / 255.0

    x = np.linspace(-np.pi, np.pi, img_array.shape[1])
    y = np.linspace(-np.pi, np.pi, img_array.shape[0])
    X, Y = np.meshgrid(x, y)

    if function_type == 'sin':
        Z = np.sin(2 * np.pi * period * (X + Y))
    elif function_type == 'cos':
        Z = np.cos(2 * np.pi * period * (X + Y))
    else:
        abort(400, 'Invalid function type')

    Z = np.expand_dims(Z, axis=2)
    transformed_array = np.clip(normalized_array * (1 + Z), 0, 1)

    transformed_img = Image.fromarray((transformed_array * 255).astype(np.uint8))

    orig_colors = get_color_distribution(img)
    transformed_colors = get_color_distribution(transformed_img)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    fig.suptitle('Color Distribution')

    ax1.plot(np.arange(len(orig_colors)), [c[0] / 255 for c in orig_colors], color='blue')  # set a single color
    ax1.set_xticks(np.arange(len(orig_colors)))
    ax1.set_xticklabels([c[1] for c in orig_colors], rotation=45)
    ax1.set_title('Original Image')

    ax2.plot(np.arange(len(transformed_colors)), [c[0] / 255 for c in transformed_colors],
             color='red')  # set a single color
    ax2.set_xticks(np.arange(len(transformed_colors)))
    ax2.set_xticklabels([c[1] for c in transformed_colors], rotation=45)
    ax2.set_title('Transformed Image')

    plt.tight_layout()
    plot_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'plot.png')
    plt.savefig(plot_filename)
    transformed_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'transformed.png')
    transformed_img.save(transformed_filename)
    orig_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'orig.png')
    img.save(orig_filename)

    result_filename = os.path.basename(plot_filename)
    with open(plot_filename, 'rb') as f:
        plot_bytes = f.read()

    plot_base64 = base64.b64encode(plot_bytes).decode('utf-8')

    return render_template('result.html', orig=orig_filename, plot=plot_base64, result_filename=result_filename)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', sitekey=RECAPTCHA_SITE_KEY)


def get_color_distribution(img):
    colors = img.getcolors(img.size[0] * img.size[1])
    return sorted(colors, key=lambda x: x[0], reverse=True)[:10]


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.config['UPLOAD_FOLDER'] = 'uploads'
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
