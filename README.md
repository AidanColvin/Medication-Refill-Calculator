# Medication-Refill-Calculator

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Privacy: Stateless](https://img.shields.io/badge/Privacy-100%25_Stateless-success.svg)](#security--privacy)

A highly optimized, fully stateless web application designed to track medication refills with precision. It features an intelligent date-parsing engine, complete quantity calculations, and proactive refill alerts. Built for speed, accuracy, and absolute user privacy.

---

## Table of Contents
1. [Team & Ownership](#-team--ownership)
2. [System Overview](#-system-overview)
3. [Key Features](#-key-features)
4. [Quick Start & Installation](#-quick-start--installation)
5. [Public Deployment](#-public-deployment)
6. [Input Specifications](#-input-specifications)
7. [Date Parsing Engine](#-date-parsing-engine)
8. [Security & Privacy](#-security--privacy)
9. [License & Disclaimers](#-license--disclaimers)

---

## Team & Ownership

**Bean** - Creator, Inventor, Visionary, Co-Founder & CEO  
**Peanut** - Consigliere & Co-Founder  

> **LEGAL NOTICE:** BEAN HOLDS ALL LIABILITY AND RESPONSIBILITY FOR EVERYTHING THAT IS INCLUDED, STORED, AND GENERATED FROM THIS. ALL IP IS GENERATED FROM BEAN.

---

## System Overview

The Medication Refill Calculator eliminates the guesswork from prescription management. By entering a fill date, supply length, and daily dosage, the system instantly computes the exact day a refill is required. 

**Core advantages:**
* **Zero friction:** Only the "Last Filled" date is strictly required. 
* **Stateless execution:** Runs entirely in active memory. No databases, no tracking, no cookies.
* **Error-tolerant:** Built-in regex engines automatically correct common spelling mistakes in date entries.

---

## ✨ Key Features

* **Intelligent Date Parser:** Accepts over 50 date formats, relative dates ("yesterday"), and fuzzy matches ("Novmber 15th").
* **Smart Defaults:** Automatically assumes a 30-day medication supply if left blank.
* **Complete Quantity Tracking:** Calculates exact pills taken, remaining inventory, and days of supply left.
* **Refill Milestone Calculations:** Identifies the exact date a refill should be requested.
* **Instant Web Interface:** Powered by Streamlit for immediate, responsive browser access.

---

## Quick Start & Installation

The application requires **Python 3.8+**. It relies on a single external dependency for the frontend.

### Local Development Setup

```bash
# 1. Clone the repository
git clone [https://github.com/yourusername/medication-refill-calculator.git](https://github.com/yourusername/medication-refill-calculator.git)
cd medication-refill-calculator

# 2. Create a virtual environment (Recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the application
streamlit run app.py
