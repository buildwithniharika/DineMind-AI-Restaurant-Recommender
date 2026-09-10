# Problem Statement: AI-Powered Restaurant Recommendation System (Zomato Use Case)

You are tasked with building an AI-powered restaurant recommendation service inspired by Zomato. The system should intelligently suggest restaurants based on user preferences by combining structured data with a Large Language Model (LLM).

---

## Objective

Design and implement an application that:

- Takes user preferences (such as location, budget, cuisine, and ratings)
- Uses a real-world dataset of restaurants
- Leverages an LLM to generate personalized, human-like recommendations
- Displays clear and useful results to the user

---

## System Workflow

### 1. Data Ingestion

- Load and preprocess the Zomato dataset from Hugging Face: [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
- Extract relevant fields such as restaurant name, location, cuisine, cost, rating, etc.

### 2. User Input

Collect user preferences:

| Preference | Examples |
|------------|----------|
| **Location** | Delhi, Bangalore |
| **Budget** | Low, medium, high |
| **Cuisine** | Italian, Chinese |
| **Minimum rating** | User-defined threshold |
| **Additional preferences** | Family-friendly, quick service |

### 3. Integration Layer

- Filter and prepare relevant restaurant data based on user input
- Pass structured results into an LLM prompt
- Design a prompt that helps the LLM reason and rank options

### 4. Recommendation Engine

Use the LLM to:

- Rank restaurants
- Provide explanations (why each recommendation fits)
- Optionally summarize choices

### 5. Output Display

Present top recommendations in a user-friendly format:

| Field | Description |
|-------|-------------|
| **Restaurant Name** | Name of the recommended restaurant |
| **Cuisine** | Type of cuisine offered |
| **Rating** | Restaurant rating |
| **Estimated Cost** | Approximate cost for two people |
| **AI-generated explanation** | Personalized reason why this restaurant fits the user's preferences |

---

## Dataset Reference

- **Source:** Hugging Face
- **URL:** https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation
- **Key fields:** Restaurant name, location, cuisine, cost, rating, and related metadata

---

## Summary

This project combines **structured restaurant data** (from the Zomato dataset) with **LLM-powered reasoning** to deliver personalized, explainable restaurant recommendations. The end-to-end flow spans data ingestion, user preference collection, filtering, LLM-based ranking and explanation, and a clear presentation layer for the user.
