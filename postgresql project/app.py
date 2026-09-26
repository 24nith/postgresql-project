import os
import json
import time
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# Database and deployment state for demonstration & diagnostic testing
db_state = {
    "connected": True,
    "pgvector_extension": True,
    "host": os.getenv("POSTGRES_HOST", "localhost"),
