import matplotlib
matplotlib.use('Agg')  # ✅ Use non-GUI backend (important on macOS servers)
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
import pandas as pd
import google.generativeai as genai
import io
import uuid
import base64
import os
import re
import logging
import json
from contextlib import redirect_stdout
from werkzeug.utils import secure_filename
from flask_session import Session
import config
from config import *

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Configure sessions to use filesystem (for persistence between requests)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False

# Initialize session
Session(app)

# Configure Gemini API
if GEMINI_API_KEY == 'your-gemini-api-key-here':
    logger.warning("Gemini API key not set. Please set GEMINI_API_KEY environment variable.")
genai.configure(api_key=GEMINI_API_KEY)

# Configure upload folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
IMAGES_FOLDER = os.path.join(STATIC_FOLDER, 'images')
TEMPLATES_FOLDER = os.path.join(BASE_DIR, 'templates')

# Update config
config.UPLOAD_FOLDER = UPLOAD_FOLDER
config.STATIC_FOLDER = STATIC_FOLDER
config.IMAGES_FOLDER = IMAGES_FOLDER
config.TEMPLATES_FOLDER = TEMPLATES_FOLDER

# Create directories if they don't exist
for folder in [UPLOAD_FOLDER, STATIC_FOLDER, IMAGES_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_dataframe(file_path, max_rows=100):
    """Process uploaded CSV file and return dataframe info for large files"""
    try:
        # First, read just the header to get column info and dtypes
        df_header = pd.read_csv(file_path, nrows=0)

        # Get total row count efficiently
        total_rows = sum(1 for line in open(file_path)) - 1  # subtract 1 for header

        # For very large files, limit sample size
        if total_rows > 10000:
            max_rows = min(max_rows, 50)  # Reduce sample size for very large files

        # Read only first max_rows for sample data
        df_sample = pd.read_csv(file_path, nrows=max_rows)

        # Get column names and sample values
        columns = df_sample.columns.tolist()
        head_values = df_sample.head(min(3, len(df_sample))).to_dict('records')

        # Get data types from the sample (should be representative)
        dtypes = df_sample.dtypes.to_dict()

        return {
            'columns': columns,
            'head_values': head_values,
            'shape': (total_rows, len(columns)),  # actual total rows, not just sample
            'dtypes': dtypes,
            'sample_size': len(df_sample),
            'total_rows': total_rows
        }
    except Exception as e:
        raise ValueError(f"Error processing CSV file: {str(e)}")

def get_matplotlib_code_from_gemini(data_info):
    """Get matplotlib code from Gemini API based on dataframe info"""
    try:
        # Create model instance (API already configured at top of file)
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"""
        I have a dataset with the following information:
        - Columns: {data_info['columns']}
        - Sample data: {data_info['head_values']}
        - Data shape: {data_info['shape']}
        - Data types: {data_info['dtypes']}

        Please generate a Python matplotlib code snippet that creates a meaningful visualization for this data.
        The code should:
        1. Import necessary libraries (matplotlib.pyplot as plt, pandas as pd)
        2. Create a sample dataframe with the same structure and column names
        3. Generate an appropriate plot (bar, line, scatter, histogram, etc.)
        4. Include proper labels, title, and formatting
        5. Save the plot as 'plot.png'

        Important: The code should work in an isolated environment where only plt, pd, and basic Python functions are available.
        Create sample data that represents the same data types and structure as the original dataset.

        Provide only the Python code without any markdown formatting or explanations.
        """

        response = model.generate_content(prompt)

        # Ensure we get a proper response
        if not hasattr(response, 'text') or not response.text:
            raise ValueError("Invalid response from Gemini API")

        result = response.text.strip()

        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        return result
    except Exception as e:
        raise ValueError(f"Error getting code from Gemini API: {str(e)}")

def get_preprocessing_code_from_gemini(data_info):
    """Get preprocessing code from Gemini API based on dataframe info"""
    try:
        # Create model instance (API already configured at top of file)
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"""
        I have a dataset with the following information:
        - Columns: {data_info['columns']}
        - Sample data: {data_info['head_values']}
        - Data shape: {data_info['shape']}
        - Data types: {data_info['dtypes']}

        Please generate a Python preprocessing code snippet that demonstrates common data preprocessing techniques for this dataset.
        The code should:
        1. Import necessary libraries (pandas as pd, numpy as np, sklearn preprocessing tools if needed)
        2. Create a sample dataframe with the same structure and column names
        3. Include common preprocessing steps like:
           - Handling missing values
           - Data type conversions if needed
           - Encoding categorical variables (if any)
           - Scaling/normalization (if applicable)
           - Feature engineering suggestions
        4. Be well-commented and educational
        5. Show before/after results with print statements

        Important: The code should work in an isolated environment where only basic Python libraries are available.
        Create sample data that represents the same data types and structure as the original dataset.
        Include error handling where appropriate.

        Provide only the Python code without any markdown formatting or explanations.
        """

        response = model.generate_content(prompt)

        # Ensure we get a proper response
        if not hasattr(response, 'text') or not response.text:
            raise ValueError("Invalid response from Gemini API")

        result = response.text.strip()

        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        return result
    except Exception as e:
        raise ValueError(f"Error getting preprocessing code from Gemini API: {str(e)}")

def execute_matplotlib_code_from_file(snippet_file, data_info=None):
    """
    Read matplotlib code from file and execute it in a headless environment (macOS-safe).
    Returns the generated image filename.
    """
    try:
        # Read the code from file
        with open(snippet_file, 'r') as f:
            code_str = f.read()

        if not code_str.strip():
            raise ValueError("Code file is empty")

        # Use the existing execute_matplotlib_code function
        return execute_matplotlib_code(code_str, data_info)

    except Exception as e:
        raise RuntimeError(f"Error reading/executing code from file: {e}")

def execute_matplotlib_code(code_str, data_info=None):
    """
    Safely execute Matplotlib code in a headless environment (macOS-safe).
    Returns the generated image filename.
    """
    plt.close('all')
    fig = plt.figure()

    # Create execution environment with limited but necessary access
    exec_globals = {
        'plt': plt,
        'pd': pd,
        'data_info': data_info,
        '__builtins__': {
            'print': print,
            'len': len,
            'range': range,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
            'round': round,
            '__import__': __import__
        }
    }

    f = io.StringIO()
    with redirect_stdout(f):
        try:
            exec(code_str, exec_globals)
        except Exception as e:
            raise RuntimeError(f"Error executing generated code: {e}")

    # Save the figure
    os.makedirs("static/plots", exist_ok=True)
    image_filename = f"{uuid.uuid4().hex}.png"
    image_path = os.path.join("static", "plots", image_filename)
    plt.savefig(image_path, bbox_inches="tight")
    plt.close(fig)
    return image_filename

def clean_matplotlib_code(code):
    """Clean and extract Python code from Gemini response"""
    try:
        # Ensure code is a string
        if not isinstance(code, str):
            if code is None:
                raise ValueError("Received None from Gemini API")
            code = str(code)

        # Remove markdown code blocks if present
        code = re.sub(r'```python\s*', '', code)
        code = re.sub(r'```\s*', '', code)

        # Ensure it has proper imports and structure
        if 'import matplotlib.pyplot as plt' not in code:
            code = 'import matplotlib.pyplot as plt\n' + code
        if 'import pandas as pd' not in code:
            code = 'import pandas as pd\n' + code

        # Ensure code is not empty
        if not code.strip():
            raise ValueError("Generated code is empty")

        return code.strip()
    except Exception as e:
        raise ValueError(f"Error cleaning matplotlib code: {str(e)}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    """Main page with file upload form (Step 1)"""
    return render_template('index.html')

@app.route('/step2', methods=['POST'])
def step2_table():
    """Show CSV table with head data (Step 2)"""
    try:
        if 'file' not in request.files:
            flash('No file part')
            return redirect(url_for('index'))

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(url_for('index'))

        if file and allowed_file(file.filename):
            # Save uploaded file
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Process the CSV file
            data_info = process_dataframe(file_path)

            # Store data in session for next steps
            session['file_path'] = file_path
            session['data_info'] = data_info

            # Return table view
            return render_template('step2_table.html', data_info=data_info)
        else:
            flash('Please upload a CSV file')
            return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error processing file: {str(e)}')
        return redirect(url_for('index'))

@app.route('/step3', methods=['POST'])
def step3_code():
    """Show Gemini matplotlib code generation (Step 3)"""
    try:
        # Get data from session
        if 'data_info' not in session:
            flash('No data available. Please upload a CSV file first.')
            return redirect(url_for('index'))

        data_info = session['data_info']

        # Get matplotlib code from Gemini
        raw_code = get_matplotlib_code_from_gemini(data_info)
        cleaned_code = clean_matplotlib_code(raw_code)

        # Store code in session
        session['generated_code'] = cleaned_code

        # Return code view
        return render_template('step3_code.html',
                             data_info=data_info,
                             code=cleaned_code)
    except Exception as e:
        flash(f'Error generating code: {str(e)}')
        return redirect(url_for('index'))

@app.route('/step4', methods=['POST'])
def step4_visualization():
    """Run the generated Matplotlib code and show the visualization"""
    try:
        # Validate session
        if 'generated_code' not in session:
            flash('No generated code available. Please run Step 3 first.')
            return redirect(url_for('index'))

        cleaned_code = session['generated_code']

        # Save the generated code to a file
        snippet_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snippet')
        os.makedirs(snippet_dir, exist_ok=True)
        snippet_file = os.path.join(snippet_dir, 'mpl.py')

        with open(snippet_file, 'w') as f:
            f.write(cleaned_code)

        # Execute the code from the file to generate image
        image_filename = execute_matplotlib_code_from_file(snippet_file, session.get('data_info'))

        # Optionally clean up uploaded file
        file_path = session.pop('file_path', None)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        # Clean up the snippet file after execution
        try:
            os.remove(snippet_file)
        except Exception:
            pass

        # Render result
        return render_template(
            'step4_visualization.html',
            image_file=image_filename,
            code=cleaned_code
        )

    except Exception as e:
        flash(f'Error creating visualization: {e}')
        return redirect(url_for('index'))

@app.route('/step5', methods=['POST'])
def step5_preprocessing():
    """Generate preprocessing code snippets (Step 5)"""
    try:
        # Validate session
        if 'data_info' not in session:
            flash('No data available. Please upload a CSV file first.')
            return redirect(url_for('index'))

        data_info = session['data_info']

        # Get preprocessing code from Gemini
        raw_code = get_preprocessing_code_from_gemini(data_info)
        cleaned_code = clean_matplotlib_code(raw_code)  # Reuse existing cleaning function

        # Store code in session
        session['preprocessing_code'] = cleaned_code

        # Return preprocessing code view
        return render_template('step5_preprocessing.html',
                             data_info=data_info,
                             code=cleaned_code)
    except Exception as e:
        flash(f'Error generating preprocessing code: {str(e)}')
        return redirect(url_for('index'))

@app.route('/images/<filename>')
def serve_image(filename):
    """Serve generated images"""
    return send_file(os.path.join(IMAGES_FOLDER, filename))

if __name__ == '__main__':
    app.run(debug=True, port=5001)