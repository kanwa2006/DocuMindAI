# CorrectionNote is defined alongside Correction in correction.py.
# This re-export keeps any existing import paths working.
from app.models.correction import CorrectionNote as CorrectionNote  # noqa: F401
