# MYSports (v1.0)

A customized, high-performance sports feed aggregator designed to consolidate granular team updates into a single, unified user dashboard. 

Built as a backend-focused project to master relational database design, schedule-driven server-side caching, and data transformation pipelines.

## Core Features

- **Dynamic Personalized Feed:** Aggregates real-time data across a user's chosen "favorite" teams onto a single consolidated dashboard.
- **Persistent User Configuration:** Utilizes relational storage to securely map favorite teams to specific user accounts, ensuring the custom feed persists across logins, logouts, and sessions.
- **Live Scores & Standings:** Delivers real-time NFL game scoring updates and tracks division/conference rankings dynamically via dedicated dashboard views.
- **Context-Aware Caching Engine:** Features a schedule-driven TTL management algorithm designed to maximize data freshness during active game windows while rigidly respecting API rate limits.

## Tech Stack

- **Backend Framework:** Python / Flask
- **Caching Layer:** Redis
- **Database Engine:** SQLite
- **Templating Engine:** Jinja2 
- **Frontend Framework:** Bootstrap 5

## Architectural Challenges & Engineering Solutions

### 1. Granular Entity Caching vs. Feed Duplication
* **The Challenge:** Initially, the goal was to cache the entire user feed object to speed up load times. However, because every user's feed is a unique permutation of different favorite teams, caching full feeds would result in massive data duplication, high memory consumption in Redis, and rapid cache invalidation.
* **The Solution:** Shifted to a **Granular Entity Caching** strategy. Instead of caching the combined feed, the application caches individual team data objects. When a user requests their feed, the system instantly assembles the dashboard by pulling the respective team entities directly from memory, optimizing cache efficiency across the entire user base.

### 2. Multi-Source Data Aggregation & Request Orchestration
* **The Challenge:** Constructing a single user feed requires gathering data across multiple decoupled entities. If a user follows multiple teams, the backend must make distinct data lookups for each. Combining these fragmented responses into a seamless frontend contract without performance bottlenecks was a critical hurdle.
* **The Solution:** Engineered an **API Aggregator Engine** that orchestrates lookups. For each team in a user's favorites list, the system checks the Redis cache first (falling back to the external API on a cache miss). It appends each raw payload into a temporary array, iterates through the collection to normalize the structure, filters out non-essential fields, and maps them into a uniform array of dictionaries perfectly tailored for the frontend Jinja layout.

### 3. Finite Resource Optimization & Rate-Limit Management
* **The Challenge:** Operating under a strict free-tier constraint of **100 API calls per day** meant that standard user-driven requests would completely deplete the API budget within minutes during a busy Sunday.
* **The Solution:** Implemented a **Schedule-Driven Cache Eviction Strategy**. By aligning Redis expiration logic directly with real-world NFL broadcast schedules, the system completely insulates the third-party API from user volume:
  - **Active Game Windows:** Cache expires every **10 minutes** during active game slots (Thursday/Sunday/Monday nights and Sunday daytimes) to maintain fresh real-time scores without exceeding the 100-call budget.
  - **Off-Peak Windows:** Cache TTL is automatically extended to **12 hours** during mid-week or deep-night slots when scores and standings are static, completely preserving the API transactions.

### 4. Relational Normalization via Junction Tables
* **The Challenge:** Mapping users to their favorite teams requires handling a strict Many-to-Many (M:M) relationship, as a single user can follow many teams, and a single team can be favorited by many users.
* **The Solution:** Designed a normalized database layout using a custom junction table (`user_favorites`) mapping `user_id` to `team_id`. This serves as the system's clean source of truth for loading persistent preferences upon user authentication.

## Getting Started & Local Installation

Follow these steps to set up a private virtual environment and boot up the MYSports server locally.

### Prerequisites
Ensure you have the following installed on your machine:
- **Python 3.x**
- **pip** (Python's package installer)
- **Redis Server** (Installed locally or running via Docker)

### Setup Instructions

1. **Clone the Repository & Enter Project Directory**
   ```bash
   git clone https://github.com/DinoJazvin/MYSports.git
   cd mysports
   ```

2. **Create and Activate a Virtual Environment (`env`)**
   This insulates the project's dependencies from the rest of your machine:
   ```bash
   python3 -m venv env
   source env/bin/activate
   ```

3. **Install Dependencies**
   Install Flask, Redis, and all required library modules:
   ```bash
   pip install flask redis requests flask_session python-dotenv
   ```

4. **Start Your Redis Server**
   Ensure Redis is running in the background to handle the schedule-driven caching engine:
   ```bash
   redis-server
   ```

5. **Launch the Application**
   Run the local Flask development server:
   ```bash
   flask run
   ```
   Open your browser and navigate to `http://127.0.0.1:5000` to view the app!
