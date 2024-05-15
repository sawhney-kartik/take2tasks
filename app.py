from flask import Flask, request, jsonify, render_template
import requests
import os
import boto3
# from dotenv import load_dotenv
from openai import OpenAI
import json
from pyairtable import Api
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

# Load environment variables
# load_dotenv()

api = Api(os.getenv("airtableKey"))
table = api.table(os.getenv("airtableBase"), os.getenv("airtableTableId"))

client = OpenAI(api_key=os.getenv("oaiKey"))

# Initialize Flask app
app = Flask(__name__)

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('awsKey'),
    aws_secret_access_key=os.getenv('awsSecret'),
    region_name=os.getenv('awsRegion')
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploadAudio', methods=['POST'])
def uploadAudio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    user_id = request.form.get('userId')
    fieldForUrl = request.form.get('fieldForUrl')

    if not user_id or not fieldForUrl:
        return jsonify({'error': 'Missing userId or fieldForUrl'}), 400

    if file and allowed_file(file.filename):
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        s3_file_name = f"{user_id}_audio.{file_extension}"
        try:
            s3_client.upload_fileobj(file, 'taskresponses', s3_file_name)
            file_url = f"https://taskresponses.s3.amazonaws.com/{s3_file_name}"
            
            table.update(user_id, {fieldForUrl: file_url})
            return jsonify({'status': 'completed', 'url': file_url}), 200
        except (NoCredentialsError, PartialCredentialsError) as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Invalid file'}), 400

@app.route('/scoreAudio', methods=['POST'])
def scoreAudio():
    file_url = request.form.get('fileUrl')
    prompt = request.form.get('prompt')
    user_id = request.form.get('userId')
    fieldForScore = request.form.get('fieldForScore')
    fieldForRationale = request.form.get('fieldForRationale')

    if not file_url or not prompt or not user_id or not fieldForScore:
        return jsonify({'error': 'Missing fileUrl, prompt, userId or fieldForScore'}), 400

    try:
        response = requests.get(file_url)
        if response.status_code != 200:
            return jsonify({'error': 'Unable to download file'}), 400

        audio_path = os.path.join('/tmp', 'temp_audio')
        with open(audio_path, 'wb') as audio_file:
            audio_file.write(response.content)

        with open(audio_path, 'rb') as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcription.text}
            ],
            response_format={"type": "json_object"}
        )

        llmResponse = json.loads(completion.choices[0].message.content)
        score = llmResponse['score']
        rationale = llmResponse['rationale']

        table.update(user_id, {fieldForScore: int(score)})

        if fieldForRationale:
            table.update(user_id, {fieldForRationale: rationale})

        return jsonify({'status': 'completed'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'mp3', 'wav', 'ogg', 'm4a'}

if __name__ == '__main__':
    app.run(debug=True)
