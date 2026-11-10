"""Persistent production entry point; saves merged meshes and FBX exports."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from persistent_assembly import main
if __name__ == '__main__':
    main()
