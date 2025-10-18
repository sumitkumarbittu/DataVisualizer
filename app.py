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
    """Get multiple preprocessing code snippets from Gemini API based on dataframe info"""
    try:
        # Create model instance (API already configured at top of file)
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Analyze data types to determine which preprocessing steps are relevant
        dtypes = data_info['dtypes']
        columns = data_info['columns']

        # Determine which preprocessing steps would be useful based on data types
        preprocessing_steps = []

        # Check for numeric columns (might need scaling, outlier detection)
        numeric_cols = [col for col, dtype in dtypes.items() if dtype in ['int64', 'float64']]
        if numeric_cols:
            preprocessing_steps.extend([
                "numeric_scaling",
                "outlier_detection",
                "missing_value_numeric"
            ])

        # Check for categorical columns (might need encoding)
        categorical_cols = [col for col, dtype in dtypes.items() if dtype == 'object']
        if categorical_cols:
            preprocessing_steps.extend([
                "categorical_encoding",
                "missing_value_categorical"
            ])

        # Check for missing values in sample data
        sample_data = data_info['head_values']
        has_missing = any(None in row.values() or '' in str(v) for row in sample_data for v in row.values())
        if has_missing:
            preprocessing_steps.append("comprehensive_missing_values")

        # Always include some general steps
        preprocessing_steps.extend([
            "data_cleaning",
            "feature_engineering"
        ])

        # Remove duplicates while preserving order
        preprocessing_steps = list(dict.fromkeys(preprocessing_steps))

        # Limit to maximum 6 steps to avoid overwhelming the user
        preprocessing_steps = preprocessing_steps[:6]

        snippets = {}

        for step in preprocessing_steps:
            if step == "missing_value_numeric":
                prompt = f"""
                Generate a Python code snippet for handling missing values in NUMERIC columns.
                Dataset has columns: {columns}
                Numeric columns: {numeric_cols}
                Sample data types: {dtypes}

                Create code that:
                1. Creates sample dataframe with missing values in numeric columns
                2. Shows different strategies: mean/median imputation, forward/backward fill
                3. Compares results before and after
                4. Uses pandas and numpy only
                """

            elif step == "missing_value_categorical":
                prompt = f"""
                Generate a Python code snippet for handling missing values in CATEGORICAL columns.
                Dataset has columns: {columns}
                Categorical columns: {categorical_cols}
                Sample data types: {dtypes}

                Create code that:
                1. Creates sample dataframe with missing values in categorical columns
                2. Shows different strategies: mode imputation, creating 'Unknown' category
                3. Compares results before and after
                4. Uses pandas only
                """

            elif step == "categorical_encoding":
                prompt = f"""
                Generate a Python code snippet for encoding categorical variables.
                Dataset has columns: {columns}
                Categorical columns: {categorical_cols}
                Sample data types: {dtypes}

                Create code that:
                1. Creates sample dataframe with categorical data
                2. Shows different encoding methods: Label Encoding, One-Hot Encoding, Target Encoding
                3. Explains when to use each method
                4. Uses pandas and sklearn
                """

            elif step == "numeric_scaling":
                prompt = f"""
                Generate a Python code snippet for scaling numeric features.
                Dataset has columns: {columns}
                Numeric columns: {numeric_cols}
                Sample data types: {dtypes}

                Create code that:
                1. Creates sample dataframe with numeric data
                2. Shows different scaling methods: StandardScaler, MinMaxScaler, RobustScaler
                3. Explains when to use each method
                4. Uses sklearn preprocessing
                """

            elif step == "outlier_detection":
                prompt = f"""
                Generate a Python code snippet for outlier detection and handling.
                Dataset has columns: {columns}
                Numeric columns: {numeric_cols}
                Sample data types: {dtypes}

                Create code that:
                1. Creates sample dataframe with outliers
                2. Shows different methods: IQR method, Z-score method, Isolation Forest
                3. Compares results before and after outlier removal
                4. Uses pandas, numpy, and scipy
                """

            elif step == "data_cleaning":
                prompt = f"""
                Generate a Python code snippet for general data cleaning operations.
                Dataset has columns: {columns}
                Sample data types: {dtypes}

                Create code that:
                1. Creates sample dataframe with common data quality issues
                2. Shows cleaning steps: removing duplicates, fixing data types, handling whitespace
                3. Validates results after cleaning
                4. Uses pandas only
                """

            elif step == "feature_engineering":
                prompt = f"""
                Generate a Python code snippet for feature engineering techniques.
                Dataset has columns: {columns}
                Sample data types: {dtypes}

                Create code that:
                1. Creates sample dataframe for feature engineering
                2. Shows techniques: creating new features, binning, polynomial features, interactions
                3. Explains the value of each engineered feature
                4. Uses pandas and numpy
                """

            elif step == "comprehensive_missing_values":
                prompt = f"""
                Generate a comprehensive Python code snippet for handling missing values across all data types.
                Dataset has columns: {columns}
                Sample data types: {dtypes}

                Create code that:
                1. Creates sample dataframe with missing values in multiple columns
                2. Shows a complete missing value handling pipeline
                3. Includes visualization of missing value patterns
                4. Uses pandas, numpy, and missingno
                """

            try:
                response = model.generate_content(prompt)

                # Ensure we get a proper response
                if not hasattr(response, 'text') or not response.text:
                    continue

                result = response.text.strip()

                # Ensure result is a string
                if not isinstance(result, str):
                    result = str(result)

                snippets[step] = result

            except Exception as e:
                # If one step fails, continue with others
                continue

        # Ensure we have at least one snippet
        if not snippets:
            raise ValueError("Failed to generate any preprocessing code snippets")

        return snippets

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
    """Generate multiple preprocessing code snippets (Step 5)"""
    try:
        # Validate session
        if 'data_info' not in session:
            flash('No data available. Please upload a CSV file first.')
            return redirect(url_for('index'))

        data_info = session['data_info']

        # Get multiple preprocessing code snippets from Gemini
        raw_snippets = get_preprocessing_code_from_gemini(data_info)

        # Clean each snippet
        cleaned_snippets = {}
        for step_name, raw_code in raw_snippets.items():
            try:
                cleaned_code = clean_matplotlib_code(raw_code)
                cleaned_snippets[step_name] = cleaned_code
            except Exception as e:
                # If cleaning fails for one snippet, skip it
                continue

        # Ensure we have at least one cleaned snippet
        if not cleaned_snippets:
            raise ValueError("Failed to generate any valid preprocessing code snippets")

        # Store snippets in session
        session['preprocessing_snippets'] = cleaned_snippets

        # Return preprocessing code view
        return render_template('step5_preprocessing.html',
                             data_info=data_info,
                             snippets=cleaned_snippets)
    except Exception as e:
        flash(f'Error generating preprocessing code: {str(e)}')
        return redirect(url_for('index'))

@app.route('/images/<filename>')
def serve_image(filename):
    """Serve generated images"""
    return send_file(os.path.join(IMAGES_FOLDER, filename))

if __name__ == '__main__':
    app.run(debug=True, port=5001)