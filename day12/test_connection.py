import os
import snowflake.connector
from dotenv import load_dotenv

# Load the .env file from the lab directory
load_dotenv("lab/.env")

def test_snowflake():
    print("Testing Snowflake connection...")
    try:
        # Create connection using env variables
        conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE")
        )
        
        # Run a simple query to verify
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")
        version = cursor.fetchone()[0]
        
        print("\n✅ SUCCESS!")
        print(f"Connected to Snowflake Version: {version}")
        
    except Exception as e:
        print("\n❌ CONNECTION FAILED!")
        print(f"Error: {str(e)}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    test_snowflake()