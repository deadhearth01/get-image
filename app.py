from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session, jsonify
import requests
from PIL import Image
from io import BytesIO
import os
import secrets
import time

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flash messages and session

# Directory to temporarily store images
temp_dir = 'static/temp_images'
os.makedirs(temp_dir, exist_ok=True)

# Global in-memory store for image tokens
image_tokens = {}

@app.route('/', methods=['GET', 'POST'])
def index():
    image_url = None
    image_token = None
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        user_type = request.form.get('user_type', 'student')
        expiry = 18000  # default 5 hours
        if not user_id:
            flash('Please enter an ID.', 'danger')
            return render_template('index.html')
        if user_type == 'faculty':
            image_url_remote = f"https://gstaff.gitam.edu/img1.aspx?empid={user_id}"
        else:
            image_url_remote = f"https://doeresults.gitam.edu/photo/img.aspx?id={user_id}"
        response = requests.get(image_url_remote)
        if response.status_code == 200:
            try:
                img = Image.open(BytesIO(response.content))
                # Generate a random token for this image
                image_token = secrets.token_urlsafe(16)
                image_filename = f"{image_token}.jpeg"
                image_path = os.path.join(temp_dir, image_filename)
                img.save(image_path, "JPEG")
                # Store the mapping and expiry in the global store
                image_tokens[image_token] = {
                    'filename': image_filename,
                    'expires_at': time.time() + expiry
                }
                return render_template('index.html', image_url=url_for('get_image', token=image_token), image_token=image_token)
            except Exception as e:
                flash('Failed to process image.', 'danger')
        else:
            flash(f'Failed to retrieve image. Status code: {response.status_code}', 'danger')
    return render_template('index.html')


def _get_image_info(token):
    info = image_tokens.get(token)
    if not info:
        return None, 'Image not found or access denied.'
    if time.time() > info['expires_at']:
        return None, 'This link has expired.'
    image_path = os.path.join(temp_dir, info['filename'])
    if not os.path.exists(image_path):
        return None, 'Image file not found.'
    return image_path, None

@app.route('/image/<token>')
def get_image(token):
    image_path, error = _get_image_info(token)
    if image_path:
        return send_file(image_path)
    flash(error, 'danger')
    return redirect(url_for('index'))

@app.route('/download/<token>')
def download_image(token):
    image_path, error = _get_image_info(token)
    if image_path:
        return send_file(image_path, as_attachment=True)
    flash(error, 'danger')
    return redirect(url_for('index'))

@app.route('/set_expiry/<token>', methods=['POST'])
def set_expiry(token):
    data = request.get_json()
    expiry = int(data.get('expiry', 600))
    info = image_tokens.get(token)
    if not info:
        return jsonify({'success': False, 'error': 'Image not found'}), 404
    info['expires_at'] = time.time() + expiry
    image_tokens[token] = info
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True) 