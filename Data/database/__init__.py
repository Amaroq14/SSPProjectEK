"""
SSP Database Package
====================
SQLite database management for the SSP biomechanics study.
"""

from .ssp_database import SSPDatabase, create_database

__all__ = ["SSPDatabase", "create_database"]
