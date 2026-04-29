# Implementation Plan: Advanced Automated Intraday Trading System

This document outlines the architecture and execution steps for integrating a probabilistic trading system with Angel One SmartAPI, option chain analytics, and multi-source market logic.

## 1. Core Modules Overview
- `data/option_chain.py`: Analyzes OI, PCR, Support/Resistance, build-ups.
- `data/sentiment_engine.py`: Analyzes news/sentiment for global/macro context.
- `strategies/probabilistic_engine.py`: Aggregates TA, Option Chain, Sentiment, and Global signals into a >70% AI Confidence Score.
- `execution/low_capital_manager.py`: Implements ₹2000-₹5000 constraints.

## 2. Implementation Timeline
### Step 1: Option Chain Engine
Implement `app/data/option_chain.py` mapping LTP, strike PCR, Call/Put OI shifts.

### Step 2: Global Indicators + Sentiment
Implement global checks & NLP impact mappings.

### Step 3: Probabilistic Logic
Tie together technical engines into AI constraints.
