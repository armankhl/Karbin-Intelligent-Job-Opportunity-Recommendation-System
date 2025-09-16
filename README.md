# KarBin: An Intelligent Job Recommendation System

**_سیستم هوشمند پیشنهاد دهنده فرصت‌های شغلی "کاربین"_**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3-000000.svg?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?style=for-the-badge&logo=react)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1.svg?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)

KarBin is a sophisticated, full-stack web application designed as a BSc final project. It serves as a unified platform that scrapes job opportunities from various sources and provides users with highly personalized, semantically relevant job recommendations based on their detailed professional profiles.

---

## Table of Contents
1.  [Project Description](#project-description)
2.  [Key Features](#key-features)
3.  [Technology Stack](#technology-stack)
4.  [System Architecture](#system-architecture)
5.  [Setup and Installation](#-setup-and-installation)
    - [Prerequisites](#prerequisites)
    - [Backend Setup](#backend-setup)
    - [Frontend Setup](#frontend-setup)
6.  [Running the Application](#-running-the-application)
    - [Offline Processes](#offline-processes)
    - [Live Servers](#live-servers)
7.  [The Recommendation Engine: A Dual-Pipeline Strategy](#-the-recommendation-engine-a-dual-pipeline-strategy)
    - [System A: Real-Time Web Recommender (“Corvette”)](#system-a-real-time-web-recommender-corvette)
    - [System B: High-Accuracy Email Recommender (“Freight Train”)](#system-b-high-accuracy-email-recommender-freight-train)
8.  [Evaluation Framework](#-evaluation-framework)
9.  [Future Work](#-future-work)
10. [Project Author & Supervisor](#project-author--supervisor)

---

## Project Description

The modern job market is fragmented across numerous online platforms, making it difficult for job seekers to find all relevant opportunities. KarBin addresses this by aggregating job postings into a single, clean database. Its core innovation lies in its hybrid, multi-stage recommendation engine, which moves beyond simple keyword matching to understand the semantic nuances of a user's profile and career goals, delivering recommendations with high precision and explainability.

## Key Features

-   **🤖 Automated Job Aggregation:** A robust Python scraper (using Selenium) automatically collects and normalizes job postings from sources like Jobinja.
-   **👤 Advanced User Profiling:** A detailed, multi-part profile page allows users to input their work experience, education, skills, and specific job preferences.
-   **🧠 Dual-Pipeline Recommendation Engine:**
    -   A **lightweight, real-time** system for fast, keyword-based relevance sorting on the main jobs page.
    -   A **high-accuracy, offline** system that uses a state-of-the-art Bi-Encoder/Cross-Encoder pipeline for personalized email alerts.
-   **🔍 Interactive Job Hub:** A fully-featured discovery page with keyword search, multi-faceted filtering (province, category), and advanced sorting options.
-   **🔒 Secure Authentication:** A complete user authentication system with JWT, email verification, and rate-limited endpoints to ensure security and prevent abuse.
-   **✉️ Automated Email Alerts:** Proactive email notifications powered by the high-accuracy recommendation engine to keep users engaged.
-   **📊 Research-Grade Evaluation:** A standalone evaluation script to measure and compare the performance of different recommendation models using advanced metrics (Precision@K, Diversity, Novelty, Serendipity).

## Technology Stack

| Category | Technology / Tool | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python, Flask, Flask-JWT-Extended, Flask-Bcrypt, Flask-Limiter | Core API, Authentication, Security |
| **Frontend** | React, React Router, Axios, React Context API | Interactive UI, Navigation, State Management |
| **Database** | PostgreSQL | Primary data store for all jobs, users, and interactions |
| **ML / NLP** | SentenceTransformers, Scikit-learn, FAISS, Pandas | Semantic Embeddings, TF-IDF, Similarity Search, Evaluation |
| **Web Scraping**| Selenium | Automated data collection from job portals |
| **Email Service**| Brevo (Sendinblue) SDK | Transactional emails for verification and recommendations |

## System Architecture

The project follows a modern, decoupled architecture:
-   **React Frontend:** A Single Page Application (SPA) that handles all user-facing views and interactions. It communicates with the backend via a REST API.
-   **Flask Backend:** A Python-based server that exposes RESTful API endpoints for authentication, profile management, job queries, and recommendations.
-   **PostgreSQL Database:** The single source of truth for all persistent data.
-   **Offline ML Services:** A collection of standalone Python scripts that are run periodically (or as needed) to perform heavy computations, such as scraping, generating embeddings, and running evaluations. This separation ensures the live API remains fast and responsive.

## 🚀 Setup and Installation

### Prerequisites
-   Python 3.9+ and `pip`
-   Node.js v16+ and `npm`
-   PostgreSQL Server
-   A `.env` file with your environment variables (database credentials, JWT secret, etc.). Use `.env.example` as a template.

### Backend Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up the database:**
    -   Ensure your PostgreSQL server is running.
    -   Create a database (e.g., `karbin_db`).
    -   Run all the necessary SQL scripts (`.sql` files) to create the tables.
5.  **Run ML Pre-computation:**
    -   (Optional but recommended) Run the web scraper to populate the database: `python run_scraper.py`
    -   Run the data migration/backfill scripts (`backfill_jobs.py`, etc.) if you have existing data.
    -   Generate the FAISS index for semantic search: `python embed_jobs.py`
    -   Generate the TF-IDF vectors for relevance sort: `python precompute_tfidf.py`

### Frontend Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```
2.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```

## ⚙️ Running the Application

You need to run the backend API and the frontend development server in separate terminals.

### Offline Processes
These should be run before starting the live servers for the first time.
-   **Scraper:** `python backend/run_scraper.py`
-   **ML Artifacts:** `python backend/embed_jobs.py` and `python backend/precompute_tfidf.py`
-   **Evaluation:** `python backend/evaluate.py`

### Live Servers

1.  **Start the Backend API Server:**
    ```bash
    # (From the /backend directory with venv activated)
    python api.py
    ```
    The API will be available at `http://127.0.0.1:5000`.

2.  **Start the Frontend Development Server:**
    ```bash
    # (From the /frontend directory)
    npm start
    ```
    The application will open in your browser at `http://localhost:3000`.

## 🧠 The Recommendation Engine: A Dual-Pipeline Strategy

To balance real-time performance with high-accuracy results, KarBin employs a dual-pipeline ("Corvette" and "Freight Train") strategy.

### System A: Real-Time Web Recommender (“Corvette”)
-   **Purpose:** Deliver fast, relevant results on the main `/jobs` page.
-   **Method:** Uses pre-computed **TF-IDF vectors** with cosine similarity. This provides a lightweight, keyword-based relevance score that is extremely fast to compute on the fly for logged-in users.

### System B: High-Accuracy Email Recommender (“Freight Train”)
-   **Purpose:** Deliver the most accurate and personalized recommendations for offline email alerts.
-   **Method:** A state-of-the-art, multi-stage pipeline:
    1.  **Hard Filtering (The Sieve):** Dramatically reduces the candidate pool by applying strict filters for category, province, experience level, and a minimum skill overlap.
    2.  **Bi-Encoder Retrieval:** Uses a fast **SentenceTransformer** model (via a FAISS index) to find the top 50 semantically similar jobs from the filtered pool.
    3.  **Cross-Encoder Re-ranking:** A more powerful but slower **Cross-Encoder** model re-ranks only these 50 candidates, providing a highly accurate final score. This is the core of the system's scientific novelty.

## 📊 Evaluation Framework

The project includes a standalone evaluation script (`evaluate.py`) to measure the performance of the recommendation models. This script runs an A/B test comparing the Bi-Encoder model against the enhanced Bi + Cross-Encoder model across a set of user personas.

The evaluation uses a combination of standard and advanced metrics:
-   **Precision@K & Recall@K:** Classic information retrieval metrics to measure relevance accuracy.
-   **Diversity (ILS):** Measures how varied the recommendations are.
-   **Novelty:** Measures how "surprising" or non-obvious the recommendations are.

## 💡 Future Work

-   **Learning to Re-rank (LTR):** Integrate user click data from the `user_job_interactions` table to train a model (e.g., XGBoost) that learns the optimal weights for the hybrid scoring formula.
-   **Knowledge Graph Embeddings:** Model the ecosystem as a graph to infer latent skills and user interests, further mitigating the cold-start problem.
-   **Fairness and Bias Audit:** Conduct a formal audit of the embeddings and algorithms to identify and mitigate potential demographic biases.

## Project Author & Supervisor
-   **Student:** Arman Khalili
-   **Supervisor:** Dr. Seyed Peyman Adibi
