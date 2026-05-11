# Project Instructions & Working Principles

This document provides a brief overview of the files in the **Legalassist AI** repository and their working principles.

## Core Application Files

- **`app.py`**: The main entry point for the Streamlit web application. It handles the UI for uploading judgments, generating summaries, and navigating between different modules (Drafting, Analytics, Help).
- **`auth.py`**: Manages user authentication, session initialization, and login/logout logic using Streamlit's session state.
- **`database.py`**: Defines the SQLAlchemy database schema (users, cases, documents, deadlines, feedback) and handles database initialization and session management.
- **`config.py`**: Centralized configuration management using environment variables for API keys, database URLs, and application constants.
- **`core.py` (and `core/`)**: Contains core logic and utility functions used across the application, such as text extraction from PDFs, LLM prompt engineering, and language detection.

## Specialized Modules

- **`case_manager.py`**: Contains the logic for creating and managing legal cases, uploading documents to specific cases, and retrieving case history.
- **`analytics_engine.py`**: Powering the Analytics Dashboard. It aggregates case data, calculates regional trends, and provides the logic for the Appeal Success Estimator.
- **`notification_service.py`**: A service for sending notifications (email/SMS) to users regarding deadlines and case updates.
- **`scheduler.py`**: Manages background tasks and scheduled notifications using `apscheduler`.
- **`celery_app.py`**: Configures Celery for handling long-running background tasks like batch processing or complex analytics generation.

## CLI & Batch Tools

- **`cli.py`**: A comprehensive Command Line Interface tool for batch processing multiple legal judgments, supporting OCR, parallel workers, and progress tracking.
- **`deadline_cli.py`**: A CLI tool specifically for managing and viewing upcoming legal deadlines.
- **`pdf_exporter.py`**: Handles the generation of professional PDF reports for judgment summaries and legal drafts.
- **`modify_pdf.py`**: Utilities for manipulating PDF files, such as merging or adding watermarks/overlays.

## UI & Integration

- **`notifications_ui.py`**: Contains specialized UI components for displaying and managing notifications within the Streamlit app.
- **`pages/`**: Directory containing additional Streamlit pages for the multi-page application structure (Login, Case Details, Analytics Dashboard, etc.).
- **`api/`**: Contains the FastAPI implementation for exposing Legalassist AI features via a RESTful API.
- **`sdk/`**: Provides a Python SDK for external applications to integrate with Legalassist AI services.

## Support & Data

- **`legal_aid_directory.json`**: A data file containing state-wise information for legal aid authorities, NGOs, and law clinics in India.
- **`scripts/`**: Utility scripts for data generation (e.g., sample analytics data) and maintenance.
- **`tests/`**: Contains the test suite for verifying the functionality of core components and CLI tools.
