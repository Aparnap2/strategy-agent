from db import init_db

def main():
    """Initialize the database."""
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")

if __name__ == "__main__":
    main()
