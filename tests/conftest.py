import sys
import os

# Make project root importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "simulation"))
sys.path.insert(0, os.path.join(ROOT, "processing"))
sys.path.insert(0, os.path.join(ROOT, "analytics"))
sys.path.insert(0, os.path.join(ROOT, "database"))
sys.path.insert(0, os.path.join(ROOT, "communication"))
