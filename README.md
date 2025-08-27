# WORK IN PROGRESS...

# QGen - Query Generation Tool

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**QGen** is a powerful tool that helps domain experts, product managers, and AI engineers create synthetic queries for any domain or application. The tool leverages LLMs to generate diverse, realistic queries based on user-defined dimensions, following a structured two-stage process.

**Available Interfaces:**
- 🖥️ **Command Line Interface (CLI)** - Full-featured terminal interface
- 🌐 **Web Interface** - User-friendly browser-based interface (NEW!)

## 🚀 Quick Start

### Installation

Install from source (recommended for development):

```bash
git clone https://github.com/webstruck/query-generator.git
cd query-generator

# Using uv (recommended - faster)
uv pip install -e .

# Or using pip
pip install -e .
```

### Create Your First Project

#### 🌐 Web Interface (Easiest)
```bash
# Launch the web interface
qgen web

# Follow the guided interface in your browser
# 1. Create a new project with a template
# 2. Generate and review tuples
# 3. Generate and review queries  
# 4. Export your dataset
```

#### 🖥️ Command Line Interface
```bash
# Initialize a new project with a domain template
qgen init my-chatbot --template question_answering

# Navigate to your project
cd my-chatbot

# Validate your dimensions
qgen dimensions validate

# Generate tuples (dimension combinations)
qgen generate tuples --count 20

# Generate queries from approved tuples
qgen generate queries --queries-per-tuple 3

# Export your dataset
qgen export --format csv
```

That's it! You now have a dataset of synthetic queries ready for your AI project.

## 🎯 Key Features

- **🔧 Domain Templates**: Pre-built templates for common use cases (customer support, e-commerce, Q&A, etc.)
- **📊 Systematic Generation**: Two-stage process ensures comprehensive coverage
- **🎨 Interactive Review**: Review and approve generated content
- **📤 Multiple Export Formats**: CSV and JSON export with rich metadata
- **🔌 LLM Integration**: Works with OpenAI, Azure OpenAI, and GitHub Models and extendable to other providers
- **🎛️ Fully Configurable**: Customize dimensions, prompts, and generation parameters
- **🌐 Web Interface**: User-friendly browser interface for non-CLI users

## 🌐 Web Interface

QGen now includes a **Streamlit-based web interface** that makes the tool accessible to users who prefer graphical interfaces over command-line tools.

### **Launch Web Interface**
```bash
# Launch from anywhere
qgen web

# Interface opens at http://localhost:8501
```

### **Web Interface Features**
- **📁 Project Management**: Create and load projects with guided forms
- **🎯 Interactive Generation**: Visual progress bars and real-time feedback
- **✅ Enhanced Review**: Click-to-approve interface with inline editing
- **📊 Data Visualization**: Statistics dashboard and data preview
- **📥 One-Click Export**: Direct download buttons for datasets
- **⚙️ Configuration Display**: Visual environment and settings overview

Perfect for:
- **Non-technical users** who need a GUI
- **Rapid prototyping** and experimentation
- **Collaborative review** sessions
- **Demonstration** and training purposes

> **Note**: The web interface uses the same core logic as the CLI, so projects created in either interface work seamlessly in both.

## 📋 Available Domain Templates

| Template | Description | Use Case |
|----------|-------------|----------|
| `question_answering` | Wikipedia-style Q&A RAG systems | Knowledge base chatbots |
| `customer_support` | Customer service interactions | Support ticket classification |
| `e_commerce` | Shopping and product queries | E-commerce search/recommendations |
| `real_estate` | Property and real estate CRM | Real estate agent assistants |
| `mental_health` | Mental health support conversations | Wellness and therapy chatbots |

## 🛠️ Core Concepts

### Dimensions
**Dimensions** are axes of variation that systematically categorize different aspects of user queries. For example:

- **Question Type**: factual, definition, comparison, explanation
- **Complexity**: simple, moderate, complex  
- **Topic Domain**: science, history, geography, culture

### Two-Stage Process
1. **Stage 1: Tuple Generation** - Generate combinations of dimension values
2. **Stage 2: Query Generation** - Create natural language queries for each tuple

This approach ensures systematic coverage while maintaining query naturalness.

## 📖 Usage Guide

### Project Management

```bash
# Initialize new project
qgen init my-project --template customer_support

# Check project status
qgen status

# Edit dimensions.yml to specify dimensions

# Sanitize dimensions
qgen dimensions validate
```

### Generation Workflow

```bash
# Generate tuples (dimension combinations)
qgen generate tuples --count 30 --provider github

# Generate queries from tuples  
qgen generate queries --queries-per-tuple 5

# Export final dataset
qgen export --format json --stage approved
```

### Review Workflow

```bash
# Generate without review (for batch processing)
qgen generate tuples --count 50 --no-review
qgen generate queries --queries-per-tuple 3 --no-review

# Review separately when convenient (interactive with shortcuts)
qgen review tuples      # Review generated tuples with a/r/e/s/q shortcuts
qgen review queries     # Review generated queries with a/r/e/s/q shortcuts

# Export final dataset
qgen export --format csv --stage approved
```

### Working with Dimensions

```bash
# Show examples from all domains
qgen dimensions examples

# Show specific domain examples
qgen dimensions examples --domain e_commerce

# Get guidance on creating dimensions
qgen dimensions guide
```

### Data Organization

QGen maintains an organized project structure:

```
my-project/
├── dimensions.yml          # Your dimension definitions
├── config.yml              # LLM parameters and prompt template definitions
├── data/
│   ├── tuples/            # generated.json, approved.json
│   ├── queries/           # generated.json, approved.json
│   └── exports/           # Final datasets (CSV/JSON)
└── prompts/               # Customizable LLM templates
```

## ⚙️ Configuration

### Environment Setup

Create a `.env` file in your project root:

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Or Azure OpenAI
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
AZURE_OPENAI_API_VERSION=2023-12-01-preview

# Or GitHub Models (free tier available)
GITHUB_TOKEN=your_github_PAT__token_with_models_read_scope
```

### Custom Dimensions

Edit `dimensions.yml` in your project:

```yaml
dimensions:
  - name: "user_intent"
    description: "What the user is trying to accomplish"
    values: ["search", "purchase", "support", "browse"]
  
  - name: "complexity"
    description: "How complex the user's request is"
    values: ["simple", "moderate", "complex"]

example_queries:
  - "Find wireless headphones under $100"
  - "I need help with my recent order"
```

### LLM Parameters

Customize generation in your project's `config.yml`:

```yaml
llm_params:
  temperature: 0.7
  top_p: 1.0
```

## 🔧 Advanced Usage

### Custom Domain Templates

Create your own domain template by adding a YAML file to `src/qgen/examples/dimensions/`:

```yaml
name: "Your Custom Domain"
description: "Description of your domain"

dimensions:
  - name: "your_dimension"
    description: "Your dimension description"
    values: ["value1", "value2", "value3"]

example_queries:
  - "Example query 1"
  - "Example query 2"
```

The template will be automatically available in `qgen init --template your_template`.

### Export Options

```bash
# Export different stages
qgen export --stage generated    # All generated queries
qgen export --stage approved     # Only approved queries (default)

# Different formats
qgen export --format csv         # Spreadsheet-friendly
qgen export --format json        # Structured data with metadata

# Custom output
qgen export --output my-dataset.csv --format csv
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone <repository-url>
cd query-generator
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Using uv (recommended)
uv pip install -e ".[dev]"

# Or using pip
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 **Documentation**: Check this README and built-in `--help` commands
- 🐛 **Issues**: Report bugs on [GitHub Issues](https://github.com/your-org/qgen/issues)
- 💬 **Discussions**: Join our [GitHub Discussions](https://github.com/your-org/qgen/discussions)

## 🙏 Acknowledgments

- Based on learnings from AI Evals For Engineers & PMs course by Hamel Husain and Shreya Shankar.

---

**Happy Query Generation! 🚀**