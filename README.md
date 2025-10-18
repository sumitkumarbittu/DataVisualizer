# CSV Data Visualizer

A sophisticated Python Flask web application that provides a **4-step AI-powered data visualization workflow** for CSV files. The application accepts files of **any size**, processes data efficiently, uses Google's Gemini 2.5 Flash AI to generate matplotlib code, saves code to files for execution, and displays beautiful visualizations on the frontend.

## 🚀 Features

- **Unlimited File Size Support**: Upload CSV files of any size (no artificial limits)
- **Intelligent Data Processing**: Efficiently analyzes large files by reading only necessary data
- **4-Step Interactive Workflow**:
  - **Step 1**: Upload CSV file
  - **Step 2**: Review data structure and sample data
  - **Step 3**: View AI-generated matplotlib code
  - **Step 4**: Execute code and view visualization
- **AI-Powered Visualization**: Uses Google's Gemini 2.5 Flash API to generate optimal matplotlib code
- **File-Based Code Execution**: Generated code saved to `snippet/mpl.py` before execution
- **Safe Code Execution**: Isolated environment with security restrictions
- **Beautiful Web Interface**: Responsive design with step-by-step navigation
- **macOS Compatibility**: Optimized for headless matplotlib rendering
- **Comprehensive Error Handling**: Robust error handling throughout the pipeline

## 🛠️ Technical Highlights

- **Smart Memory Management**: Processes large files without memory issues
- **Efficient Row Counting**: Counts total rows without loading entire files
- **Adaptive Sampling**: Reduces sample size for extremely large datasets
- **File-Based Architecture**: Clean separation of code generation and execution
- **Session Management**: Maintains state across the 4-step workflow
- **Responsive Templates**: Mobile-friendly interface with progress indicators

## 📋 Requirements

- Python 3.8+
- Flask
- Flask-Session
- pandas
- google-generativeai
- matplotlib
- Pillow

## 🔧 Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd PreProcessing
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**
```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
export SECRET_KEY="your-flask-secret-key-here"
```

## ⚙️ Configuration

The application uses a `config.py` file for configuration:

- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `SECRET_KEY`: Flask application secret key (required)
- `DEBUG`: Enable/disable debug mode (default: True)
- `MAX_CONTENT_LENGTH`: File upload size limit (set to None for unlimited)
- `ALLOWED_EXTENSIONS`: File types allowed (CSV only)

## 🎯 Usage

1. **Start the application:**
```bash
python app.py
```

2. **Open your browser** and navigate to `http://localhost:5001`

3. **Follow the 4-step workflow:**
   - **Step 1**: Upload any CSV file (unlimited size)
   - **Step 2**: Review data structure, statistics, and sample data
   - **Step 3**: View AI-generated matplotlib code
   - **Step 4**: Execute code from file and view the visualization

## 📁 File Structure

```
PreProcessing/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── requirements.txt           # Python dependencies
├── snippet/                   # Generated code storage
│   └── mpl.py                 # Temporary matplotlib code file
├── templates/                 # HTML templates
│   ├── index.html            # Step 1: Upload form
│   ├── step2_table.html      # Step 2: Data table view
│   ├── step3_code.html       # Step 3: Code display
│   └── step4_visualization.html # Step 4: Results with image
├── static/                   # Static files
│   └── plots/               # Generated chart images
└── uploads/                 # Temporary file uploads
```

## 🌐 API Endpoints

- `GET /`: Main page with file upload form (Step 1)
- `POST /step2`: Process CSV and show data table (Step 2)
- `POST /step3`: Generate and display matplotlib code (Step 3)
- `POST /step4`: Execute code from file and show visualization (Step 4)
- `GET /images/<filename>`: Serve generated images (legacy)
- `GET /static/plots/<filename>`: Serve generated plot images

## 🔒 Security Features

- **File Type Validation**: Only CSV files accepted
- **Secure Filename Handling**: Prevents path traversal attacks
- **Isolated Code Execution**: Restricted execution environment
- **Session Management**: Secure state management across steps
- **File Cleanup**: Automatic cleanup of temporary files

## ⚡ Performance Features

- **Memory Efficient**: Processes large files without loading everything into memory
- **Adaptive Sampling**: Intelligently reduces sample size for very large datasets
- **Fast Processing**: Quick analysis even for large files
- **Optimized Rendering**: macOS-compatible headless matplotlib backend

## 🚨 Error Handling

The application includes comprehensive error handling for:

- **File Upload Issues**: Invalid files, size limits, missing files
- **Data Processing Errors**: Malformed CSV, encoding issues, missing data
- **API Communication**: Network issues, API limits, authentication
- **Code Execution Errors**: Syntax errors, import issues, runtime exceptions
- **File System Issues**: Permission errors, disk space, cleanup failures

## 🔄 Workflow Details

### Step 1: Upload CSV
- Accepts files of any size
- Validates file type (CSV only)
- Stores file temporarily for processing

### Step 2: Data Analysis
- Reads only first 100 rows for analysis (configurable)
- Extracts column names, data types, and statistics
- Shows total rows vs. sample size
- Displays formatted data table

### Step 3: AI Code Generation
- Sends data structure to Gemini 2.5 Flash API
- Receives optimized matplotlib code
- Displays generated code with syntax highlighting
- Stores code in session for next step

### Step 4: Visualization Execution
- **Saves code to `snippet/mpl.py`**
- **Executes code in isolated environment**
- **Generates visualization image**
- **Displays results with original code**
- **Cleans up temporary files**

## 🎨 Example Generated Code

The AI generates matplotlib code like this:

```python
import matplotlib.pyplot as plt
import pandas as pd

# Create sample dataframe
data = {
    'column1': [1, 2, 3, 4, 5],
    'column2': ['A', 'B', 'C', 'D', 'E']
}
df = pd.DataFrame(data)

# Create visualization
plt.figure(figsize=(10, 6))
plt.bar(df['column1'], df['column2'])
plt.title('Sample Visualization')
plt.savefig('plot.png')
```

## 📈 Use Cases

- **Data Analysis**: Quick visualization of CSV datasets
- **Report Generation**: Automated chart creation for reports
- **Exploratory Data Analysis**: Visual data structure examination
- **Educational Tool**: Learning matplotlib through AI-generated examples
- **Business Intelligence**: Rapid prototyping of data visualizations

## 🐛 Troubleshooting

**Common Issues:**
- **413 Request Entity Too Large**: File size limit exceeded (increase MAX_CONTENT_LENGTH)
- **Import Errors**: Ensure all dependencies are installed
- **API Errors**: Check GEMINI_API_KEY is set correctly
- **Matplotlib Errors**: Ensure matplotlib backend is set to 'Agg'

**Debug Mode:**
Enable debug mode in config.py for detailed error messages.

## 📄 License

MIT License
