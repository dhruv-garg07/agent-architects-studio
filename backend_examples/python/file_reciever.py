from flask import Flask, request, render_template_string
import os
import html   # <-- use built-in html.escape()

app = Flask(__name__)
UPLOAD_DIR = "received_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----- ORIGINAL HTML PAGE -----
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Upload File to Laptop A</title>
    <style>
        body { font-family: Arial; margin: 50px; }
        .box { width: 400px; padding: 20px; border: 1px solid #ccc; border-radius: 10px; }
        button { padding: 8px 20px; font-size: 16px; }
    </style>
</head>
<body>

    <h2>Send File to Laptop A</h2>

    <div class="box">
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <label>Select a file:</label><br><br>
            <input type="file" name="file" required><br><br>
            <button type="submit">Send</button>
        </form>
    </div>

    <br><br>
    <a href="/show_code">Show Server Code</a>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

# ----- UPLOAD ENDPOINT -----
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return "No file uploaded", 400

    file = request.files["file"]
    if file.filename == "":
        return "Invalid filename", 400

    save_path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(save_path)

    return f"File '{file.filename}' uploaded successfully!"

# ----- SHOW CODE ENDPOINT -----
@app.route("/show_code")
def show_code():
    # Read this exact file
    with open(__file__, "r") as f:
        code = f.read()

    # Escape special HTML chars so code displays safely
    escaped_code = html.escape(code)

    html_page = f"""
    <html>
        <head>
            <title>Server Code</title>
            <style>
                body {{ font-family: monospace; white-space: pre-wrap; margin: 20px; }}
                .code-box {{
                    background: #f4f4f4;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #ccc;
                }}
            </style>
        </head>
        <body>
            <h2>Flask Server Code</h2>
            <div class="code-box">{escaped_code}</div>
        </body>
    </html>
    """

    return html_page

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
