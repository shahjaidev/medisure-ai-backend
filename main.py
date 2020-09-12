from flask import Flask, request
from werkzeug.utils import secure_filename
from flask_cors import CORS

import os
from dotenv import load_dotenv, find_dotenv

from scripts.gpt import GPT, Example, set_openai_key

from google.cloud import storage

from scripts.vision import parse_table

UPLOAD_FOLDER = os.path.join(".", "uploads")
ALLOWED_EXTENSIONS = {"pdf"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
CORS(app)

load_dotenv(find_dotenv(), override=True)
set_openai_key(os.getenv("GPT_SECRET_KEY", ""))

BUCKET_NAME = os.getenv("GOOGLE_BUCKET_NAME", "")
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)


@app.route("/")
def hello_world():
    return "Hello, World!"


@app.route("/vision", methods=["GET", "POST"])
def parse_pdf():
    file = request.files["file"]
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return parse_table(filename)


vision_GPT = GPT(engine="davinci", temperature=0.5, max_tokens=200)
vision_examples = [
    [
        "What is not included in the out of pocket limit?",
        "Premiums and health cares this plan does not cover are not included. Even though you pay these expenses, they do not count towards the limit",
    ],
    [
        "Do I need a referral to see a specialist?",
        "No. You can see a specialist you choose without permission from this plan.",
    ],
    [
        "Are diagnostic x-rays covered?",
        "In network diagnostics are a maximum of $10 copay while out of network diagnostics are not covered.",
    ],
]
for example in vision_examples:
    vision_GPT.add_example(Example(example[0], example[1]))


@app.route("/vision/qa", methods=["GET", "POST"])
def question_answer():
    blob = bucket.blob(request.args.get("doc"))
    text = blob.download_as_text()
    vision_GPT.set_premise(text)
    prompt = request.data.decode("UTF-8")
    return vision_GPT.get_top_reply(prompt)


summarize_GPT = GPT(engine="davinci", temperature=0.5, max_tokens=100)
summarize_GPT.set_premise("My fifth grader asked me what this passage means")
summarize_GPT = GPT(engine="davinci", temperature=0.5, max_tokens=300)
summarize_examples = [
    [
        "Cancer symptoms and signs depend on the specific type and grade of cancer; although general signs and symptoms are not very specific the following can be found in patients with different cancers: fatigue, weight loss, pain, skin changes, change in bowel or bladder function, unusual bleeding, persistent cough or voice change, fever, lumps, or tissue masses.",
        "Cancer can have many symptoms including fatigue, pain, and tissue masses.",
    ],
    [
        "Diabetes mellitus is a disorder in which blood sugar (glucose) levels are abnormally high because the body does not produce enough insulin to meet its needs. Urination and thirst are increased, and people may lose weight even if they are not trying to.",
        "Diabetes is a disease where your blood sugar levels are too high.",
    ],
    [
        "A copayment or copay is a fixed amount for a covered service, paid by a patient to the provider of service before receiving the service. It may be defined in an insurance policy and paid by an insured person each time a medical service is accessed. ",
        "A copay is a fixed out-of-pocket amount paid by an insured for covered services.",
    ],
]
for example in summarize_examples:
    summarize_GPT.add_example(Example(example[0], example[1]))


@app.route("/summarize", methods=["GET", "POST"])
def gpt3():
    prompt = request.data.decode("UTF-8")
    return summarize_GPT.get_top_reply(prompt)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
