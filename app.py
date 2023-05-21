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
RECAPTCHA_SITE_KEY = '6LdlLBAmAAAAADEkPEp1BIl_lbDYwzeE_n6lkhBt'


@app.route('/mywork', methods=['POST'])
def transform():
    file = request.files.get('file')
    order = request.form.get('order')

    if not file:
        abort(400, 'No file was uploaded')
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        abort(400, 'File is not an image')

    recaptcha_response = request.form.get('g-recaptcha-response')
    if not recaptcha_response:
        abort(400, 'reCAPTCHA verification failed')
    payload = {
        'secret': '6LdlLBAmAAAAABbqK-N4kGXshV9m_96TNR9Ka6ER',
        'response': recaptcha_response
    }
    response = requests.post('https://www.google.com/recaptcha/api/siteverify', payload).json()
    if not response['success']:
        abort(400, 'reCAPTCHA verification failed')

    img = Image.open(file).convert('RGB')
    img_array = np.array(img)

    # Color Distribution
    color_distribution = get_color_distribution(img)

    # Color Order
    order = order.lower()
    valid_colors = ['r', 'g', 'b']
    if not set(order).issubset(valid_colors):
        abort(400, 'Invalid color order')

    order_indices = [valid_colors.index(c) for c in order]

    img_array = img_array[:, :, order_indices]
    transformed_img = Image.fromarray(img_array)

    # Calculate mean values
    mean_values = np.mean(img_array, axis=(0, 1))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    fig.suptitle('Color Distribution and Mean Values')

    ax1.plot(np.arange(len(color_distribution)), [c[0] / np.prod(img_array.shape[:2]) for c in color_distribution], color='blue')
    ax1.set_xticks(np.arange(len(color_distribution)))
    ax1.set_xticklabels([c[1] for c in color_distribution], rotation=45)
    ax1.set_title('Color Distribution')

    ax2.plot(valid_colors, mean_values, color='green')
    ax2.set_title('Mean Values')

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
