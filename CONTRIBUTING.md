# Contributing to QGen

Thank you for your interest in contributing to QGen! This guide will help you get started.

## 🚀 Quick Start for Contributors

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/your-username/qgen.git
   cd qgen
   ```

2. **Set up development environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or .venv\Scripts\activate on Windows
   
   pip install -e ".[dev]"
   ```

3. **Verify installation**:
   ```bash
   qgen --help
   pytest
   ```

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and test them

3. **Run tests and linting**:
   ```bash
   pytest
   black src/ tests/
   ruff src/ tests/
   ```

4. **Commit and push**:
   ```bash
   git add .
   git commit -m "Add your feature description"
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request** on GitHub

## 🛠️ Development Guidelines

### Code Style
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [Ruff](https://docs.astral.sh/ruff/) for linting
- Follow PEP 8 conventions
- Add type hints where appropriate

### Testing
- Write tests for new features
- Ensure existing tests pass
- Use pytest for testing
- Test both success and failure cases

### Documentation
- Update README.md for user-facing changes
- Add docstrings to new functions/classes
- Update TROUBLESHOOTING.md for common issues

## 📝 Types of Contributions

### 🐛 Bug Fixes
- Fix bugs in existing functionality
- Add tests to prevent regression
- Update documentation if needed

### ✨ New Features
- Add new domain templates
- Implement new export formats
- Enhance CLI interface
- Improve generation algorithms

### 📖 Documentation
- Improve README or guides
- Add examples and tutorials
- Fix typos or unclear instructions

### 🎨 Domain Templates
Adding new domain templates is especially welcome! See the [Domain Template Guide](#domain-template-guide) below.

## 🏗️ Project Structure

```
qgen/
├── src/qgen/
│   ├── cli/           # CLI commands and interface
│   ├── core/          # Core business logic
│   ├── examples/      # Domain templates
│   └── prompts/       # LLM prompt templates
├── tests/             # Test suite
├── docs/              # Documentation
└── pyproject.toml     # Project configuration
```

## 📋 Domain Template Guide

### Creating a New Domain Template

1. **Create YAML file** in `src/qgen/examples/dimensions/your_domain.yml`:
   ```yaml
   name: "Your Domain Name"
   description: "Description of your domain use case"
   
   dimensions:
     - name: "dimension_1"
       description: "Clear description of this dimension"
       values: ["value1", "value2", "value3"]
     - name: "dimension_2"
       description: "Another dimension description"  
       values: ["valueA", "valueB", "valueC"]
   
   example_queries:
     - "Example query that demonstrates the domain"
     - "Another realistic query example"
     - "Third example showing variety"
   ```

2. **Test your template**:
   ```bash
   qgen init test-project --template your_domain
   cd test-project
   qgen dimensions validate
   ```

3. **Validate the template**:
   - 2-5 dimensions is ideal
   - 3-6 values per dimension
   - Values should be mutually exclusive within a dimension
   - Example queries should be realistic and diverse

### Domain Template Best Practices

- **Clear naming**: Use descriptive dimension and value names
- **User-focused**: Think about what end users would actually say
- **Comprehensive**: Cover the major variations in your domain
- **Realistic**: Base examples on real user interactions when possible

### Popular Domain Ideas

We'd love templates for:
- **Legal Q&A**: Legal document queries and advice
- **Healthcare**: Patient questions and medical information
- **Education**: Student questions across subjects
- **Travel**: Trip planning and travel support
- **Finance**: Banking, investing, and financial planning
- **Gaming**: Game support and community questions
- **Food & Recipe**: Cooking questions and meal planning

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_generation.py

# Run with coverage
pytest --cov=qgen tests/
```

### Test Categories
- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test component interactions
- **CLI tests**: Test command-line interface
- **Template tests**: Validate domain templates

### Writing Tests
```python
def test_your_feature():
    # Arrange
    input_data = create_test_data()
    
    # Act
    result = your_function(input_data)
    
    # Assert
    assert result.is_valid()
    assert len(result.items) > 0
```

## 📦 Release Process

### Version Numbering
We use [Semantic Versioning](https://semver.org/):
- **Major** (1.0.0): Breaking changes
- **Minor** (0.1.0): New features, backward compatible
- **Patch** (0.0.1): Bug fixes, backward compatible

### Release Checklist
1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Create release PR
5. Tag release after merge
6. Publish to PyPI (maintainers only)

## 🔒 Security

### Reporting Security Issues
Please report security vulnerabilities privately to the maintainers rather than opening public issues.

### Security Best Practices
- Don't commit API keys or secrets
- Validate all user inputs
- Use secure defaults
- Follow principle of least privilege

## 💬 Communication

### GitHub Issues
Use GitHub issues for:
- Bug reports
- Feature requests
- Questions about usage
- Documentation improvements

### Pull Request Guidelines
- **Clear title**: Describe what the PR does
- **Description**: Explain why the change is needed
- **Testing**: Describe how you tested the change
- **Breaking changes**: Clearly mark any breaking changes

### Code Review Process
- All PRs require review from maintainers
- Address feedback promptly
- Keep PRs focused and reasonably sized
- Update documentation as needed

## 🏆 Recognition

Contributors are recognized in:
- GitHub contributors list
- Release notes for significant contributions
- README acknowledgments

## 📄 License

By contributing to QGen, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to QGen! 🙏