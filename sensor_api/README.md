# PerfectFit API for sensor data

# Requirements
For running the server, ones need to install the dependencies in `requirements.txt`.

For developing it, then install the dependencies in `requirements-dev.txt`.

# Run the server
Example code:
```python
from perfectfitapp.run import create_app
host = '0.0.0.0'
port = 8080
app = create_app(host, port)
app.run(host=host, port=port, debug=True)
```

# Test the server
```python
pytest --cov perfectfitapp --cov-report term
```
