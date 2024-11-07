import streamlit as st
from transformers import pipeline
import pandas as pd
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
import torch
from transformers import pipeline
from openai import OpenAI


device = 0 if torch.cuda.is_available() else -1

# Load environment variables from the .env file
load_dotenv()

# Retrieve the environment variables
DB_HOST = st.secrets["MYSQL_HOST"]
DB_USER = st.secrets["MYSQL_USER"]
DB_PASSWORD = st.secrets["MYSQL_PASSWORD"]
DB_NAME = st.secrets["MYSQL_DATABASE"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
# Database connection function
def load_data_from_db():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        if conn.is_connected():
            query = "SELECT * FROM NUS_dashboard_reddit;"  # Modify table name as needed
            df = pd.read_sql(query, conn)
            conn.close()
            return df
    except Error as e:
        st.error(f"Error connecting to the database: {e}")
        return None


def generate_action_plan_gpt3(title, content, selected_comments):

    client = OpenAI(
    api_key = OPENAI_API_KEY
)
    # Combine the selected comments into a single string
    comments = "\n".join(selected_comments) if selected_comments else "No relevant comments selected."
    
    # Create a structured prompt with the selected comments
    prompt = (
        f"Post Title: {title}\n"
        f"Content: {content}\n"
        f"Comments: {comments}\n\n"
        "As a school dean, generate a structured action plan based on the post and comments. "
        "The action plan should address any issues raised and provide clear, actionable steps for NBS. "
        "Please include the following sections:\n\n"
        "1. **Goals**: Outline the main objectives.\n"
        "2. **Action Steps**: List specific actions to address each objective.\n"
        "3. **Timeline**: Suggest a timeline for each action.\n"
        "4. **Resources Needed**: Identify any resources or support required.\n"
        "5. **Expected Outcomes**: Describe the anticipated results from implementing the plan."
    )

    # Use OpenAI API to generate a response
    response =client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
            {"role": "system", "content": "You are a school dean helping to generate structured and actionable plans."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        n=1,
        stop=None,
        temperature=0.7
    )
    
    # Extract and return the generated action plan text
    action_plan = response.choices[0].message
    return action_plan

def main():
    st.title("Action Plan Generation for NBS")

    # Load the data from the database
    df = load_data_from_db()
    
    if df is not None:
        # Search bar to filter posts
        search_term = st.text_input("Search for posts related to NUS/NBS:")
        
        # Filter the DataFrame based on the search term
        if search_term:
            filtered_df = df[df['post'].str.contains(search_term, case=False, na=False)]
        else:
            filtered_df = df

        # Display the filtered posts and allow selection
        post_selection = st.selectbox("Select a post:", filtered_df['post'])

        # Show the selected post details
        if post_selection:
            selected_post = filtered_df[filtered_df['post'] == post_selection].iloc[0]
            st.subheader("Selected Post")
            st.write(selected_post['content'])

            # Display comments associated with the post
            st.subheader("Comments")
            comments = selected_post['comments']
            if comments:
                comment_list = comments.split(" | ")
                selected_comments = []
                
                # Let users select comments to include
                st.write("Select comments to include in the action plan:")
                for idx, comment in enumerate(comment_list, 1):
                    if st.checkbox(f"Comment {idx}: {comment}", key=f"comment_{idx}"):
                        selected_comments.append(comment)

                # Combine selected comments for the action plan generation
                combined_comments = "\n".join(selected_comments) if selected_comments else "No comments selected."
            else:
                st.write("No comments available for this post.")
                combined_comments = "No comments available."

            # Generate action plan button
            if st.button("Generate Action Plan"):
                with st.spinner("Generating action plan..."):
                    action_plan = generate_action_plan_gpt3(
                        selected_post['post'], 
                        selected_post['content'], 
                        selected_comments
                    )
                    if action_plan:
                        st.subheader("Action Plan")
                        st.write(action_plan)
                    else:
                        st.error("Failed to generate an action plan.")
    else:
        st.error("No data available. Ensure the database connection is correct.")

if __name__ == "__main__":
    main()