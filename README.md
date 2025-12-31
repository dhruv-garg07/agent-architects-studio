# Agent Architects Studio

Welcome to Agent Architects Studio, a full-stack platform for building, sharing, and interacting with advanced AI agents. This studio provides the tools and infrastructure for developers and creators to design, test, and deploy sophisticated agents with complex memory and reasoning capabilities.

## ✨ Features

- **Creator Studio:** An intuitive interface to create and configure new AI agents.
- **Agent Marketplace:** Explore and interact with agents built by the community.
- **Advanced Memory:** Built-in RAG (Retrieval-Augmented Generation) pipeline using ChromaDB for persistent, context-aware agent memory.
- **User Authentication:** Secure user profiles and agent management powered by Supabase.
- **Scalable Backend:** A robust Python backend built with Flask, ready for deployment on services like Vercel or Render.
- **Modern Frontend:** A responsive and dynamic user experience built with React, TypeScript, and Vite.

## 🚀 Tech Stack

- **Frontend:** [React](https://react.dev/), [TypeScript](https://www.typescriptlang.org/), [Vite](https://vitejs.dev/), [Tailwind CSS](https://tailwindcss.com/), [shadcn/ui](https://ui.shadcn.com/)
- **Backend:** [Python](https://www.python.org/), [Flask](https://flask.palletsprojects.com/)
- **Database & Auth:** [Supabase](https://supabase.com/) (PostgreSQL)
- **AI & VectorDB:** Retrieval-Augmented Generation (RAG), [ChromaDB](https://www.trychroma.com/)
- **Deployment:** [Vercel](https://vercel.com/), [Render](https://render.com/)

## 🛠️ Getting Started

Follow these instructions to set up your local development environment.

### Prerequisites

- [Node.js](https://nodejs.org/en) (v18 or later)
- [Python](https://www.python.org/downloads/) (v3.11 or later)
- [Supabase CLI](https://supabase.com/docs/guides/cli)
- [Vercel CLI](https://vercel.com/docs/cli) (for local backend emulation)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/agent-architects-studio.git
cd agent-architects-studio
```

### 2. Backend Setup

The backend is a Python Flask application served as a serverless function.

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate # On Windows, use `venv\Scripts\activate`

# Install Python dependencies
pip install -r requirements.txt
```

You will need to set up your environment variables for the backend. Create a `.env` file in the root directory and add the necessary keys for Supabase and any language models you are using.

### 3. Frontend Setup

The frontend is a React application built with Vite.

```bash
# Install JavaScript dependencies
npm install
```

### 4. Database Setup

This project uses Supabase for the database and authentication.

```bash
# Start the local Supabase services
supabase start
```

This will output your local Supabase URL, anon key, and service role key. Use these to populate your `.env` file for the backend and your frontend environment variables.

### 5. Running the Application

To run the full-stack application locally, you need to run the frontend and backend servers concurrently.

```bash
# Run the backend server (simulates Vercel environment)
vercel dev
```

In a separate terminal:

```bash
# Run the frontend development server
npm run dev
```

Open your browser to `http://localhost:5173` to see the application in action.

## 🤝 Contributing

We welcome contributions from the community! Whether you're fixing a bug, adding a feature, or improving documentation, your help is appreciated.

Please follow this workflow:

1.  **Fork the repository.**
2.  **Create a new branch** for your feature or bug fix: `git checkout -b feat/my-new-feature` or `bug/fix-for-something`.
3.  **Make your changes** and commit them with clear, descriptive messages.
4.  **Ensure your code adheres to the project's style.** Run the linter to check: `npm run lint`.
5.  **Push your branch** to your fork: `git push origin feat/my-new-feature`.
6.  **Open a pull request** to the `main` branch of the original repository.

Please be detailed in your pull request description about the changes you've made and why.

## 📂 Project Structure

Here is a high-level overview of the project's directory structure:

```
/
├── api/                # Backend Python/Flask serverless functions
├── src/                # Frontend React/TypeScript source code
│   ├── components/     # Reusable UI components
│   ├── pages/          # Application pages/routes
│   ├── lib/            # Utility functions and libraries
│   └── integrations/   # Supabase client integration
├── Octave_mem/         # Core logic for the RAG and memory systems
├── supabase/           # Supabase local development configuration and migrations
└── ...                 # Configuration files (Vite, TS, Tailwind, etc.)
```

## 📜 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.