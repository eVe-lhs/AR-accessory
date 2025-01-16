from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
import os
from PIL import Image
from io import BytesIO
import base64
from bson.objectid import ObjectId  # For handling MongoDB ObjectId
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Cloudinary Configuration
cloudinary.config(
    cloud_name='drpup6lci',
    api_key='191398282626259',
    api_secret='9p65Sb30nyjMv7R5vb8LnmleZ3U'
)

app = Flask(__name__)
app.secret_key = "secret_key_for_flash_messages"

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client['accessory_db']  # Database name
accessories_collection = db['accessories']  # Collection name

# Helper function to check for duplicate accessory names


def is_duplicate(name):
    return accessories_collection.find_one({"name": name}) is not None

# Route to display the main screen


@app.route('/')
def index():
    return render_template('index.html')

# Route to register accessories


@app.route('/register', methods=['GET', 'POST'])
def register_accessory():
    if request.method == 'POST':
        name = request.form['name']
        type_of_accessory = request.form['type']
        # For drawing data (base64)
        image_data = request.form.get('image_data')

        if is_duplicate(name):
            flash("Accessory with this name already exists!", "danger")
        else:
            # If drawing data exists, process it
            if image_data:
                # Convert base64 to image
                img_data = base64.b64decode(image_data.split(',')[1])
                img = Image.open(BytesIO(img_data))
                img.save('temp_image.png')

                # Upload to Cloudinary
                result = cloudinary.uploader.upload('temp_image.png')
                cloudinary_image_url = result['url']
                os.remove('temp_image.png')  # Clean up the temporary file

            else:
                # If file upload exists, save the uploaded image to Cloudinary
                file = request.files['image']
                result = cloudinary.uploader.upload(file)
                cloudinary_image_url = result['url']

            # Insert the accessory into MongoDB
            accessories_collection.insert_one({
                'name': name,
                'type': type_of_accessory,
                'image': cloudinary_image_url
            })
            flash("Accessory registered successfully!", "success")
            return redirect(url_for('index'))

    return render_template('register_accessory.html')

# Route to try on accessories (with live webcam)


@app.route('/tryon', methods=['GET', 'POST'])
def try_on():
    # Fetch the accessories from MongoDB
    accessories = list(accessories_collection.find())
    return render_template('try_on.html', accessories=accessories)

# Route to manage accessories


@app.route('/manage_accessories')
def manage_accessories():
    accessories = list(accessories_collection.find())
    return render_template('manage_accessories.html', accessories=accessories)

# Route to edit an accessory


@app.route('/edit_accessory/<id>', methods=['GET', 'POST'])
def edit_accessory(id):
    accessory = accessories_collection.find_one({"_id": ObjectId(id)})
    if not accessory:
        flash("Accessory not found!", "danger")
        return redirect(url_for('manage_accessories'))

    if request.method == 'POST':
        name = request.form['name']
        type_of_accessory = request.form['type']

        # Check if new name already exists (excluding current accessory)
        if name != accessory['name'] and is_duplicate(name):
            flash("Accessory with this name already exists!", "danger")
        else:
            # Update accessory details
            update_data = {"name": name, "type": type_of_accessory}

            # Handle new image upload to Cloudinary
            if 'image' in request.files and request.files['image'].filename:
                file = request.files['image']
                result = cloudinary.uploader.upload(file)
                update_data['image'] = result['url']

            accessories_collection.update_one(
                {"_id": ObjectId(id)}, {"$set": update_data})
            flash("Accessory updated successfully!", "success")
            return redirect(url_for('manage_accessories'))

    return render_template('edit_accessory.html', accessory=accessory)

# Route to delete an accessory


@app.route('/delete_accessory/<id>')
def delete_accessory(id):
    accessory = accessories_collection.find_one({"_id": ObjectId(id)})
    if accessory:
        # Remove the image from Cloudinary
        cloudinary.uploader.destroy(
            accessory['image'].split("/")[-1].split(".")[0])

        # Remove accessory from the database
        accessories_collection.delete_one({"_id": ObjectId(id)})
        flash("Accessory deleted successfully!", "success")
    else:
        flash("Accessory not found!", "danger")
    return redirect(url_for('manage_accessories'))


if __name__ == '__main__':
    app.run(debug=True)
