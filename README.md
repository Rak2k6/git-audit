<div align="center">
  <h1>🛡️ Fair Gig Guardian</h1>
  <p><strong>AI-powered platform to analyze gig economy contracts and detect unfair clauses</strong></p>

  <p>
    <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
    <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
    <img alt="React" src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" />
    <img alt="Hackathon Project" src="https://img.shields.io/badge/Hackathon-Project-FF5A5F?style=for-the-badge&logo=devpost&logoColor=white" />
  </p>
</div>

<br />

## 📖 Overview

**Fair Gig Guardian** is an AI-powered platform that analyzes gig economy contracts and detects potentially unfair clauses before freelancers sign them. By acting as a digital legal assistant, it empowers gig workers, freelancers, and independent contractors to understand their rights and negotiate better terms.

---

## 🤔 Problem Statement

Gig economy contracts are often written with complex legal jargon that strongly favors the employer. Freelancers frequently sign agreements without realizing they might be relinquishing their intellectual property, agreeing to unreasonable non-compete clauses, or accepting unfair payment terms. Fair Gig Guardian solves this asymmetry by automating contract review using advanced AI reasoning.

---

## 🏗️ AI Council Architecture

The platform leverages a **Multi-Agent AI Council Architecture**, which breaks down the complex task of legal analysis into dedicated, specialized agents:

1. **Auditor Agent**: Scans the document to extract and categorize potentially risky clauses from the contract.
2. **Debate Agent**: Challenges the findings by generating arguments both for and against the fairness of each highlighted clause.
3. **Judge Agent**: Evaluates the arguments from the Debate Agent, renders a final verdict on each clause, and computes an overall fairness score.

### Architecture Diagram

```text
┌──────────────┐         Upload Contract          ┌─────────────────────┐
│              ├─────────────────────────────────►│                     │
│  Freelancer  │                                  │ Frontend Interface  │
│              │◄─────────────────────────────────┤   (React + Vite)    │
└──────────────┘           View Results           └─────────┬───────────┘
                                                            │
                                                            ▼
                                                  ┌─────────────────────┐
                                                  │                     │
                                                  │ Backend API Gateway │
                                                  │     (FastAPI)       │
                                                  │                     │
                                                  └─────────┬───────────┘
                                                            │
                            ┌───────────────────────────────▼───────────────────────────────┐
                            │                    AI COUNCIL (LLM Core)                      │
                            │                                                               │
                            │   ┌──────────────┐     ┌─────────────┐     ┌─────────────┐    │
                            │   │              │     │             │     │             │    │
                            │   │ 1. Auditor   ├───► │ 2. Debate   ├───► │ 3. Judge    │    │
                            │   │    Agent     │     │    Agent    │     │    Agent    │    │
                            │   │              │     │             │     │             │    │
                            │   └──────────────┘     └─────────────┘     └─────────────┘    │
                            └───────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

- **AI-Based Contract Clause Extraction**: Automatically identifies critical terms hidden in dense legal text.
- **Multi-Agent AI Reasoning**: Employs an intelligent council (Auditor, Debate, Judge) to ensure high-quality and balanced analysis.
- **Fairness Scoring System**: Provides an easy-to-understand aggregate score for the entire contract.
- **Risk Clause Detection**: Accurately flags predatory or unreasonable clauses.
- **Category-Wise Analysis**: Deep dives into specific contract domains:
  - 💰 Payment Terms
  - 🛑 Termination Rights
  - 🚫 Non-Compete Agreements
  - 💡 Intellectual Property (IP) Ownership
  - ⚖️ Dispute Resolution
  - 💵 Compensation Details

---

## 🛠️ Tech Stack

### Backend
- **Python**
- **FastAPI**
- **Pydantic**
- **Uvicorn**
- **LLM Integration**: Gemini (or similar LLM API like Groq)

### Frontend
- **React**
- **Vite**
- **Tailwind CSS**

---

## 💻 API Usage Example

**Endpoint:** `POST /analyze`

**Request Body:**
```json
{
  "contract_text": "The contractor agrees to transfer all intellectual property rights to the company and shall not work for any competitor for a period of 5 years following termination."
}
```

**Response:**
```json
{
  "overall_score": 45,
  "verdict": "Unfair",
  "category_scores": {
    "payment": 80,
    "termination": 50,
    "non_compete": 20,
    "ip": 30,
    "dispute": 60,
    "compensation": 70
  },
  "risky_clauses": [
    {
      "category": "non_compete",
      "risk_level": "High",
      "explanation": "A 5-year non-compete is excessively long and limits your ability to find work.",
      "suggestion": "Negotiate to reduce the non-compete period to 6-12 months."
    }
  ]
}
```

---

## 🚀 Local Setup Instructions

### Prerequisites
- [Node.js](https://nodejs.org/) (v18+)
- [Python](https://www.python.org/) (v3.10+)
- LLM API Key (e.g., Gemini or Groq)

### 1. Backend Setup

Open a terminal and navigate to the backend directory:

```bash
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export GROQ_API_KEY="your_api_key_here"  # Or GEMINI_API_KEY if using Gemini

# Run the FastAPI server
uvicorn main:app --reload --port 8000
```
*The backend API will be running at `http://localhost:8000`.*

### 2. Frontend Setup

Open a new terminal and navigate to the root directory where the Vite project is located:

```bash
# Install frontend dependencies
npm install
# or
bun install

# Start the Vite development server
npm run dev
# or
bun dev
```
*The frontend client will be running at `http://localhost:5173`.*

---

## ☁️ Deployment

- **Backend**: Hosted on **Render**. The FastAPI application is deployed as a managed web service directly from the repository.
- **Frontend**: Hosted on **Vercel**. The Vite application is built and optimized for production to ensure fast delivery globally.

---

## 🏆 Hackathon Project

**Fair Gig Guardian** was proudly developed as a hackathon project! It was born out of a desire to solve real-world problems for freelancers and gig workers by combining cutting-edge GenAI architectures with an accessible, consumer-friendly web interface under a tight deadline.

---

## 🔮 Future Improvements

- **Image Parsing**: Allow users to directly upload photos of their contracts instead of pasting text.
- **Automated Contract Generation**: Use AI to automatically draft a fairer, redlined version of the loaded contract.
- **Multilingual Support**: Expand the AI Council's capabilities to analyze and explain contracts in multiple languages.
- **User Accounts & History Dashboard**: Save analyzed contracts securely so users can track and compare documents over time.

---
